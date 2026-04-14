#
#  Copyright 2024 The InfiniFlow Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#
"""
问答评测模块 - 支持标注问答对、自动评分、准确率报表
"""
import json
import time
import math
import uuid
from collections import Counter
from datetime import datetime

from flask import request
from flask_login import current_user, login_required

from api import settings
from api.db import StatusEnum
from api.db.db_models import DB
from api.db.services.dialog_service import chat
from api.db.services.knowledgebase_service import KnowledgebaseService
from api.db.services.dialog_service import DialogService
from api.utils.api_utils import get_json_result


# ======================== 数据库表 ========================

class EvaluationDataset(DB.Model):
    """评测数据集"""
    id = DB.CharField(max_length=32, primary_key=True)
    tenant_id = DB.CharField(max_length=32, null=False, index=True)
    name = DB.CharField(max_length=255, null=False)
    description = DB.TextField(null=True)
    kb_ids = DB.TextField(null=True, help_text="关联知识库IDs, JSON数组")
    dialog_id = DB.CharField(max_length=32, null=True, help_text="关联对话ID")
    create_time = DB.BigIntegerField(null=True)
    update_time = DB.BigIntegerField(null=True)
    status = DB.CharField(max_length=1, default=StatusEnum.VALID.value)

    class Meta:
        db_table = "evaluation_dataset"


class EvaluationQA(DB.Model):
    """评测问答对"""
    id = DB.CharField(max_length=32, primary_key=True)
    dataset_id = DB.CharField(max_length=32, null=False, index=True)
    question = DB.TextField(null=False)
    expected_answer = DB.TextField(null=False, help_text="标注的标准答案")
    actual_answer = DB.TextField(null=True, help_text="系统生成的答案")
    score = DB.FloatField(null=True, help_text="综合评分 0-1")
    score_detail = DB.TextField(null=True, help_text="评分详情JSON")
    reference_chunks = DB.TextField(null=True, help_text="检索到的chunk信息JSON")
    status = DB.CharField(max_length=16, default="pending", help_text="pending/running/done/failed")
    create_time = DB.BigIntegerField(null=True)
    update_time = DB.BigIntegerField(null=True)

    class Meta:
        db_table = "evaluation_qa"


class EvaluationRun(DB.Model):
    """评测运行记录"""
    id = DB.CharField(max_length=32, primary_key=True)
    dataset_id = DB.CharField(max_length=32, null=False, index=True)
    tenant_id = DB.CharField(max_length=32, null=False, index=True)
    total = DB.IntegerField(default=0)
    completed = DB.IntegerField(default=0)
    avg_score = DB.FloatField(null=True)
    accuracy = DB.FloatField(null=True, help_text="准确率(score>0.6的比例)")
    status = DB.CharField(max_length=16, default="running")
    create_time = DB.BigIntegerField(null=True)
    update_time = DB.BigIntegerField(null=True)

    class Meta:
        db_table = "evaluation_run"


def _init_tables():
    """创建评测相关表"""
    DB.create_tables([EvaluationDataset, EvaluationQA, EvaluationRun], safe=True)


try:
    _init_tables()
except Exception:
    pass


# ======================== 评分函数 ========================

def _compute_bleu(reference: str, hypothesis: str, n=4) -> float:
    """计算BLEU-N分数"""
    ref_tokens = list(reference)
    hyp_tokens = list(hypothesis)

    if len(hyp_tokens) == 0:
        return 0.0

    scores = []
    for i in range(1, n + 1):
        ref_ngrams = Counter(
            tuple(ref_tokens[j:j + i]) for j in range(len(ref_tokens) - i + 1)
        )
        hyp_ngrams = Counter(
            tuple(hyp_tokens[j:j + i]) for j in range(len(hyp_tokens) - i + 1)
        )
        matches = sum(min(hyp_ngrams[ng], ref_ngrams.get(ng, 0)) for ng in hyp_ngrams)
        total = max(sum(hyp_ngrams.values()), 1)
        scores.append(matches / total)

    if any(s == 0 for s in scores):
        return 0.0

    log_avg = sum(math.log(s) for s in scores) / len(scores)
    bp = min(1.0, math.exp(1 - len(ref_tokens) / max(len(hyp_tokens), 1)))
    return bp * math.exp(log_avg)


def _compute_rouge_l(reference: str, hypothesis: str) -> float:
    """计算ROUGE-L分数"""
    ref_tokens = list(reference)
    hyp_tokens = list(hypothesis)

    if not ref_tokens or not hyp_tokens:
        return 0.0

    m, n = len(ref_tokens), len(hyp_tokens)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if ref_tokens[i - 1] == hyp_tokens[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])

    lcs = dp[m][n]
    precision = lcs / n if n > 0 else 0
    recall = lcs / m if m > 0 else 0

    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def _compute_keyword_coverage(reference: str, hypothesis: str) -> float:
    """关键词覆盖率"""
    ref_chars = set(reference.replace(" ", ""))
    hyp_chars = set(hypothesis.replace(" ", ""))
    if not ref_chars:
        return 0.0
    return len(ref_chars & hyp_chars) / len(ref_chars)


def evaluate_answer(expected: str, actual: str) -> dict:
    """综合评测一个答案"""
    bleu = _compute_bleu(expected, actual)
    rouge_l = _compute_rouge_l(expected, actual)
    keyword = _compute_keyword_coverage(expected, actual)

    # 综合评分: 加权平均
    score = 0.3 * bleu + 0.4 * rouge_l + 0.3 * keyword

    return {
        "score": round(score, 4),
        "bleu": round(bleu, 4),
        "rouge_l": round(rouge_l, 4),
        "keyword_coverage": round(keyword, 4),
    }


# ======================== API路由 ========================

# --- 评测数据集 CRUD ---

@manager.route("/dataset", methods=["POST"])  # noqa: F821
@login_required
def create_dataset():
    """创建评测数据集"""
    req = request.json
    name = req.get("name", "").strip()
    if not name:
        return get_json_result(data=False, message="名称不能为空", code=settings.RetCode.ARGUMENT_ERROR)

    ds = EvaluationDataset.create(
        id=uuid.uuid4().hex,
        tenant_id=current_user.id,
        name=name,
        description=req.get("description", ""),
        kb_ids=json.dumps(req.get("kb_ids", [])),
        dialog_id=req.get("dialog_id"),
        create_time=int(time.time() * 1000),
        update_time=int(time.time() * 1000),
    )
    return get_json_result(data={"id": ds.id, "name": ds.name})


@manager.route("/dataset", methods=["GET"])  # noqa: F821
@login_required
def list_datasets():
    """列出当前用户的评测数据集"""
    datasets = (
        EvaluationDataset.select()
        .where(
            EvaluationDataset.tenant_id == current_user.id,
            EvaluationDataset.status == StatusEnum.VALID.value,
        )
        .order_by(EvaluationDataset.create_time.desc())
    )
    result = []
    for ds in datasets:
        qa_count = EvaluationQA.select().where(EvaluationQA.dataset_id == ds.id).count()
        result.append({
            "id": ds.id,
            "name": ds.name,
            "description": ds.description,
            "kb_ids": json.loads(ds.kb_ids) if ds.kb_ids else [],
            "dialog_id": ds.dialog_id,
            "qa_count": qa_count,
            "create_time": ds.create_time,
        })
    return get_json_result(data=result)


@manager.route("/dataset/<ds_id>", methods=["DELETE"])  # noqa: F821
@login_required
def delete_dataset(ds_id):
    """删除评测数据集"""
    EvaluationDataset.update(status=StatusEnum.INVALID.value).where(
        EvaluationDataset.id == ds_id,
        EvaluationDataset.tenant_id == current_user.id,
    ).execute()
    return get_json_result(data=True)


# --- 评测问答对 CRUD ---

@manager.route("/dataset/<ds_id>/qa", methods=["POST"])  # noqa: F821
@login_required
def add_qa(ds_id):
    """添加问答对（单条或批量）"""
    req = request.json
    items = req.get("items", [])
    if not items and req.get("question"):
        items = [{"question": req["question"], "expected_answer": req["expected_answer"]}]

    created = []
    for item in items:
        q = item.get("question", "").strip()
        a = item.get("expected_answer", "").strip()
        if not q or not a:
            continue
        qa = EvaluationQA.create(
            id=uuid.uuid4().hex,
            dataset_id=ds_id,
            question=q,
            expected_answer=a,
            create_time=int(time.time() * 1000),
            update_time=int(time.time() * 1000),
        )
        created.append({"id": qa.id, "question": q})

    return get_json_result(data={"count": len(created), "items": created})


@manager.route("/dataset/<ds_id>/qa", methods=["GET"])  # noqa: F821
@login_required
def list_qa(ds_id):
    """列出数据集中的问答对"""
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 20))

    query = EvaluationQA.select().where(EvaluationQA.dataset_id == ds_id)
    total = query.count()
    items = query.order_by(EvaluationQA.create_time.desc()).paginate(page, page_size)

    result = []
    for qa in items:
        result.append({
            "id": qa.id,
            "question": qa.question,
            "expected_answer": qa.expected_answer,
            "actual_answer": qa.actual_answer,
            "score": qa.score,
            "score_detail": json.loads(qa.score_detail) if qa.score_detail else None,
            "status": qa.status,
            "create_time": qa.create_time,
        })
    return get_json_result(data={"total": total, "items": result})


@manager.route("/dataset/<ds_id>/qa/<qa_id>", methods=["PUT"])  # noqa: F821
@login_required
def update_qa(ds_id, qa_id):
    """更新问答对"""
    req = request.json
    updates = {}
    if "question" in req:
        updates["question"] = req["question"]
    if "expected_answer" in req:
        updates["expected_answer"] = req["expected_answer"]
    if updates:
        updates["update_time"] = int(time.time() * 1000)
        EvaluationQA.update(**updates).where(
            EvaluationQA.id == qa_id,
            EvaluationQA.dataset_id == ds_id,
        ).execute()
    return get_json_result(data=True)


@manager.route("/dataset/<ds_id>/qa/<qa_id>", methods=["DELETE"])  # noqa: F821
@login_required
def delete_qa(ds_id, qa_id):
    """删除问答对"""
    EvaluationQA.delete().where(
        EvaluationQA.id == qa_id,
        EvaluationQA.dataset_id == ds_id,
    ).execute()
    return get_json_result(data=True)


# --- 运行评测 ---

@manager.route("/dataset/<ds_id>/run", methods=["POST"])  # noqa: F821
@login_required
def run_evaluation(ds_id):
    """运行评测 - 对数据集中所有pending的QA进行评测"""
    ds = EvaluationDataset.get_or_none(EvaluationDataset.id == ds_id)
    if not ds or ds.tenant_id != current_user.id:
        return get_json_result(data=False, message="数据集不存在", code=settings.RetCode.ARGUMENT_ERROR)

    if not ds.dialog_id:
        return get_json_result(data=False, message="请先关联对话助手", code=settings.RetCode.ARGUMENT_ERROR)

    # 获取Dialog
    dialogs = DialogService.query(id=ds.dialog_id)
    if not dialogs:
        return get_json_result(data=False, message="对话助手不存在", code=settings.RetCode.ARGUMENT_ERROR)
    dialog = dialogs[0]

    # 获取待评测的QA
    qas = list(EvaluationQA.select().where(
        EvaluationQA.dataset_id == ds_id,
        EvaluationQA.status.in_(["pending", "failed"]),
    ))

    if not qas:
        return get_json_result(data=False, message="没有待评测的问答对", code=settings.RetCode.ARGUMENT_ERROR)

    # 创建运行记录
    run = EvaluationRun.create(
        id=uuid.uuid4().hex,
        dataset_id=ds_id,
        tenant_id=current_user.id,
        total=len(qas),
        create_time=int(time.time() * 1000),
        update_time=int(time.time() * 1000),
    )

    # 同步执行评测（后续可改为异步）
    scores = []
    completed = 0
    for qa in qas:
        try:
            EvaluationQA.update(status="running", update_time=int(time.time() * 1000)).where(
                EvaluationQA.id == qa.id
            ).execute()

            # 调用RAG问答
            messages = [{"role": "user", "content": qa.question}]
            actual_answer = ""
            for ans in chat(dialog, messages, stream=False):
                if isinstance(ans, dict) and "answer" in ans:
                    actual_answer = ans["answer"]
                elif isinstance(ans, str):
                    actual_answer += ans

            # 评分
            score_result = evaluate_answer(qa.expected_answer, actual_answer)

            EvaluationQA.update(
                actual_answer=actual_answer,
                score=score_result["score"],
                score_detail=json.dumps(score_result),
                status="done",
                update_time=int(time.time() * 1000),
            ).where(EvaluationQA.id == qa.id).execute()

            scores.append(score_result["score"])
            completed += 1

        except Exception as e:
            EvaluationQA.update(
                status="failed",
                score_detail=json.dumps({"error": str(e)}),
                update_time=int(time.time() * 1000),
            ).where(EvaluationQA.id == qa.id).execute()

    # 更新运行结果
    avg_score = sum(scores) / len(scores) if scores else 0
    accuracy = len([s for s in scores if s > 0.6]) / len(scores) if scores else 0

    EvaluationRun.update(
        completed=completed,
        avg_score=round(avg_score, 4),
        accuracy=round(accuracy, 4),
        status="done",
        update_time=int(time.time() * 1000),
    ).where(EvaluationRun.id == run.id).execute()

    return get_json_result(data={
        "run_id": run.id,
        "total": len(qas),
        "completed": completed,
        "avg_score": round(avg_score, 4),
        "accuracy": round(accuracy, 4),
    })


# --- 评测报表 ---

@manager.route("/dataset/<ds_id>/report", methods=["GET"])  # noqa: F821
@login_required
def get_report(ds_id):
    """获取评测报表"""
    # QA统计
    qas = list(EvaluationQA.select().where(EvaluationQA.dataset_id == ds_id))
    total = len(qas)
    done = [qa for qa in qas if qa.status == "done"]
    failed = [qa for qa in qas if qa.status == "failed"]
    pending = [qa for qa in qas if qa.status == "pending"]

    scores = [qa.score for qa in done if qa.score is not None]
    avg_score = sum(scores) / len(scores) if scores else 0
    accuracy = len([s for s in scores if s > 0.6]) / len(scores) if scores else 0

    # 分数分布
    distribution = {"0-0.2": 0, "0.2-0.4": 0, "0.4-0.6": 0, "0.6-0.8": 0, "0.8-1.0": 0}
    for s in scores:
        if s < 0.2:
            distribution["0-0.2"] += 1
        elif s < 0.4:
            distribution["0.2-0.4"] += 1
        elif s < 0.6:
            distribution["0.4-0.6"] += 1
        elif s < 0.8:
            distribution["0.6-0.8"] += 1
        else:
            distribution["0.8-1.0"] += 1

    # 详细评分维度平均值
    bleu_scores = []
    rouge_scores = []
    keyword_scores = []
    for qa in done:
        if qa.score_detail:
            try:
                detail = json.loads(qa.score_detail)
                bleu_scores.append(detail.get("bleu", 0))
                rouge_scores.append(detail.get("rouge_l", 0))
                keyword_scores.append(detail.get("keyword_coverage", 0))
            except Exception:
                pass

    # 运行历史
    runs = list(
        EvaluationRun.select()
        .where(EvaluationRun.dataset_id == ds_id)
        .order_by(EvaluationRun.create_time.desc())
        .limit(10)
    )

    return get_json_result(data={
        "summary": {
            "total": total,
            "done": len(done),
            "failed": len(failed),
            "pending": len(pending),
            "avg_score": round(avg_score, 4),
            "accuracy": round(accuracy, 4),
        },
        "dimensions": {
            "bleu": round(sum(bleu_scores) / len(bleu_scores), 4) if bleu_scores else 0,
            "rouge_l": round(sum(rouge_scores) / len(rouge_scores), 4) if rouge_scores else 0,
            "keyword_coverage": round(sum(keyword_scores) / len(keyword_scores), 4) if keyword_scores else 0,
        },
        "distribution": distribution,
        "runs": [
            {
                "id": r.id,
                "total": r.total,
                "completed": r.completed,
                "avg_score": r.avg_score,
                "accuracy": r.accuracy,
                "status": r.status,
                "create_time": r.create_time,
            }
            for r in runs
        ],
    })
