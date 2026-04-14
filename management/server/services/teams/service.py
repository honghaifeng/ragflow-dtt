"""
Organization service - supports hierarchical (tree) organizations.
"""
import mysql.connector
from datetime import datetime
from utils import generate_uuid
from database import DB_CONFIG


def get_teams_with_pagination(current_page, page_size, name='', sort_by="create_time", sort_order="desc", tenant_id=None):
    """查询组织列表（支持分页、筛选）"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)

        where_clauses = []
        params = []

        if name:
            where_clauses.append("o.name LIKE %s")
            params.append(f"%{name}%")

        if tenant_id:
            where_clauses.append("o.owner_id = %s")
            params.append(tenant_id)

        where_sql = "WHERE o.status = '1'" + (" AND " + " AND ".join(where_clauses) if where_clauses else "")

        valid_sort_fields = ["name", "create_time", "create_date"]
        if sort_by not in valid_sort_fields:
            sort_by = "create_time"
        sort_clause = f"ORDER BY o.{sort_by} {sort_order.upper()}"

        count_sql = f"SELECT COUNT(*) as total FROM organization o {where_sql}"
        cursor.execute(count_sql, params)
        total = cursor.fetchone()['total']

        offset = (current_page - 1) * page_size

        query = f"""
        SELECT
            o.id,
            o.name,
            o.description,
            o.owner_id,
            o.parent_id,
            o.create_date,
            o.update_date,
            (SELECT u.nickname FROM user u WHERE u.id = o.owner_id) as owner_name,
            (SELECT p.name FROM organization p WHERE p.id = o.parent_id) as parent_name,
            (SELECT COUNT(*) FROM org_member om WHERE om.org_id = o.id AND om.status = '1') as member_count
        FROM organization o
        {where_sql}
        {sort_clause}
        LIMIT %s OFFSET %s
        """
        cursor.execute(query, params + [page_size, offset])
        results = cursor.fetchall()

        cursor.close()
        conn.close()

        formatted = []
        for row in results:
            formatted.append({
                "id": row["id"],
                "name": row["name"],
                "ownerName": row["owner_name"] or "未指定",
                "memberCount": row["member_count"],
                "description": row["description"] or "",
                "parentId": row["parent_id"],
                "parentName": row["parent_name"] or "",
                "createTime": row["create_date"].strftime("%Y-%m-%d %H:%M:%S") if row["create_date"] else "",
                "updateTime": row["update_date"].strftime("%Y-%m-%d %H:%M:%S") if row["update_date"] else "",
            })
        return formatted, total

    except mysql.connector.Error as err:
        print(f"DB error: {err}")
        return [], 0


def get_org_tree():
    """获取完整组织树"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        query = """
        SELECT
            o.id,
            o.name,
            o.description,
            o.owner_id,
            o.parent_id,
            o.create_date,
            (SELECT u.nickname FROM user u WHERE u.id = o.owner_id) as owner_name,
            (SELECT COUNT(*) FROM knowledgebase kb WHERE kb.org_id = o.id AND kb.status = '1') as kb_count,
            (SELECT COUNT(*) FROM document d JOIN knowledgebase kb2 ON d.kb_id = kb2.id WHERE kb2.org_id = o.id AND kb2.status = '1' AND d.status = '1') as file_count
        FROM organization o
        WHERE o.status = '1'
        ORDER BY o.create_time ASC
        """
        cursor.execute(query)
        results = cursor.fetchall()

        # 查询所有 org_member，构建 org_id -> user_id 集合
        cursor.execute("SELECT org_id, user_id FROM org_member WHERE status = '1'")
        member_rows = cursor.fetchall()
        cursor.close()
        conn.close()

        org_members_map = {}
        for mr in member_rows:
            org_members_map.setdefault(mr["org_id"], set()).add(mr["user_id"])

        all_orgs = []
        for row in results:
            oid = row["id"]
            all_orgs.append({
                "id": oid,
                "name": row["name"],
                "ownerId": row["owner_id"],
                "ownerName": row["owner_name"] or "未指定",
                "memberCount": len(org_members_map.get(oid, set())),
                "kbCount": row["kb_count"],
                "fileCount": row["file_count"],
                "description": row["description"] or "",
                "parentId": row["parent_id"],
                "createTime": row["create_date"].strftime("%Y-%m-%d %H:%M:%S") if row["create_date"] else "",
            })

        def build_tree(orgs, parent_id=None):
            tree = []
            for org in orgs:
                if (org["parentId"] or None) == parent_id:
                    node = dict(org)
                    node["children"] = build_tree(orgs, org["id"])
                    tree.append(node)
            return tree

        def aggregate_counts(nodes):
            """自底向上汇总：kbCount/fileCount 直接累加，memberCount 用 user_id 集合去重"""
            for node in nodes:
                node["_member_set"] = set(org_members_map.get(node["id"], set()))
                if node["children"]:
                    aggregate_counts(node["children"])
                    for child in node["children"]:
                        node["_member_set"] |= child["_member_set"]
                        node["kbCount"] += child["kbCount"]
                        node["fileCount"] += child["fileCount"]
                node["memberCount"] = len(node["_member_set"])

        def cleanup_sets(nodes):
            for node in nodes:
                node.pop("_member_set", None)
                if node["children"]:
                    cleanup_sets(node["children"])

        tree = build_tree(all_orgs)
        aggregate_counts(tree)
        cleanup_sets(tree)
        return tree

    except mysql.connector.Error as err:
        print(f"DB error: {err}")
        return []


def get_team_by_id(team_id):
    """获取单个组织详情"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        query = """
        SELECT o.id, o.name, o.description, o.owner_id, o.parent_id, o.create_date, o.update_date,
            (SELECT p.name FROM organization p WHERE p.id = o.parent_id) as parent_name
        FROM organization o WHERE o.id = %s AND o.status = '1'
        """
        cursor.execute(query, (team_id,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        if row:
            return {
                "id": row["id"],
                "name": row["name"],
                "description": row["description"],
                "parentId": row["parent_id"],
                "parentName": row["parent_name"] or "",
                "createTime": row["create_date"].strftime("%Y-%m-%d %H:%M:%S") if row["create_date"] else "",
                "updateTime": row["update_date"].strftime("%Y-%m-%d %H:%M:%S") if row["update_date"] else "",
            }
        return None
    except mysql.connector.Error as err:
        print(f"DB error: {err}")
        return None


def _get_subtree_ids(cursor, org_id):
    """递归获取所有子组织 ID"""
    cursor.execute("SELECT id FROM organization WHERE parent_id = %s AND status = '1'", (org_id,))
    children = cursor.fetchall()
    result = []
    for child in children:
        cid = child["id"] if isinstance(child, dict) else child[0]
        result.append(cid)
        result.extend(_get_subtree_ids(cursor, cid))
    return result


def delete_team(team_id):
    """级联软删除组织及所有子组织"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)

        all_ids = [team_id]
        all_ids.extend(_get_subtree_ids(cursor, team_id))

        placeholders = ",".join(["%s"] * len(all_ids))
        cursor.execute(f"UPDATE organization SET status = '0' WHERE id IN ({placeholders})", all_ids)
        cursor.execute(f"UPDATE org_member SET status = '0' WHERE org_id IN ({placeholders})", all_ids)

        conn.commit()
        affected = cursor.rowcount
        cursor.close()
        conn.close()
        return affected > 0
    except mysql.connector.Error as err:
        print(f"DB error: {err}")
        return False


def get_team_members(team_id):
    """获取组织及所有子孙组织的成员"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)

        all_ids = [team_id]
        all_ids.extend(_get_subtree_ids(cursor, team_id))

        placeholders = ",".join(["%s"] * len(all_ids))
        query = f"""
        SELECT om.user_id, COALESCE(u.nickname, om.user_id) as nickname, COALESCE(u.email, '') as email,
            om.role, om.create_date, om.org_id,
            (SELECT o.name FROM organization o WHERE o.id = om.org_id) as org_name
        FROM org_member om
        LEFT JOIN user u ON om.user_id = u.id
        WHERE om.org_id IN ({placeholders}) AND om.status = '1'
        ORDER BY om.create_date ASC
        """
        cursor.execute(query, all_ids)
        results = cursor.fetchall()
        cursor.close()
        conn.close()

        # 按 user_id 去重，合并多个组织名
        user_map = {}
        for m in results:
            uid = m["user_id"]
            org_name = m["org_name"] or ""
            is_desc = m["org_id"] != team_id
            if uid not in user_map:
                user_map[uid] = {
                    "userId": uid,
                    "username": m["nickname"],
                    "email": m["email"],
                    "role": m["role"],
                    "orgNames": [org_name],
                    "isDescendant": is_desc,
                    "joinTime": m["create_date"].strftime("%Y-%m-%d %H:%M:%S") if m["create_date"] else "",
                }
            else:
                if org_name and org_name not in user_map[uid]["orgNames"]:
                    user_map[uid]["orgNames"].append(org_name)
                # 如果在当前组织也有记录，标记为非子孙
                if not is_desc:
                    user_map[uid]["isDescendant"] = False
        formatted = list(user_map.values())
        return formatted
    except mysql.connector.Error as err:
        print(f"DB error: {err}")
        return []


def add_team_member(team_id, user_id, role="viewer"):
    """添加组织成员"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM org_member WHERE org_id = %s AND user_id = %s", (team_id, user_id))
        existing = cursor.fetchone()

        now = datetime.now()
        ts = int(now.timestamp() * 1000)
        date_str = now.strftime("%Y-%m-%d %H:%M:%S")

        if existing:
            cursor.execute(
                "UPDATE org_member SET role = %s, status = '1', update_time = %s, update_date = %s WHERE org_id = %s AND user_id = %s",
                (role, ts, date_str, team_id, user_id),
            )
        else:
            cursor.execute(
                "INSERT INTO org_member (id, create_time, create_date, update_time, update_date, org_id, user_id, role, invited_by, status) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (generate_uuid(), ts, date_str, ts, date_str, team_id, user_id, role, "system", "1"),
            )
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except mysql.connector.Error as err:
        print(f"DB error: {err}")
        return False


def remove_team_member(team_id, user_id):
    """移除组织成员"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()

        cursor.execute("SELECT role FROM org_member WHERE org_id = %s AND user_id = %s", (team_id, user_id))
        row = cursor.fetchone()
        if row and row[0] == 'owner':
            cursor.close()
            conn.close()
            return False

        now = datetime.now()
        ts = int(now.timestamp() * 1000)
        date_str = now.strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute(
            "UPDATE org_member SET status = '0', update_time = %s, update_date = %s WHERE org_id = %s AND user_id = %s",
            (ts, date_str, team_id, user_id),
        )
        affected = cursor.rowcount
        conn.commit()
        cursor.close()
        conn.close()
        return affected > 0
    except mysql.connector.Error as err:
        print(f"DB error: {err}")
        return False


def update_member_role(team_id, user_id, role):
    """修改成员角色"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()

        cursor.execute("SELECT role FROM org_member WHERE org_id = %s AND user_id = %s AND status = '1'", (team_id, user_id))
        row = cursor.fetchone()
        if not row:
            cursor.close()
            conn.close()
            return False
        if row[0] == 'owner':
            cursor.close()
            conn.close()
            return False

        now = datetime.now()
        ts = int(now.timestamp() * 1000)
        date_str = now.strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute(
            "UPDATE org_member SET role = %s, update_time = %s, update_date = %s WHERE org_id = %s AND user_id = %s",
            (role, ts, date_str, team_id, user_id),
        )
        affected = cursor.rowcount
        conn.commit()
        cursor.close()
        conn.close()
        return affected > 0
    except mysql.connector.Error as err:
        print(f"DB error: {err}")
        return False


def get_org_knowledgebases(org_id):
    """获取组织及所有子孙组织的知识库列表"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)

        all_ids = [org_id]
        all_ids.extend(_get_subtree_ids(cursor, org_id))

        placeholders = ",".join(["%s"] * len(all_ids))
        query = f"""
        SELECT kb.id, kb.name, kb.description, kb.create_date,
            kb.doc_num, kb.token_num, kb.chunk_num, kb.org_id,
            (SELECT u.nickname FROM user u WHERE u.id = kb.created_by) as creator_name,
            (SELECT o.name FROM organization o WHERE o.id = kb.org_id) as org_name
        FROM knowledgebase kb
        WHERE kb.org_id IN ({placeholders}) AND kb.status = '1'
        ORDER BY kb.create_time DESC
        """
        cursor.execute(query, all_ids)
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        formatted = []
        for row in results:
            formatted.append({
                "id": row["id"],
                "name": row["name"],
                "description": row["description"] or "",
                "docNum": row["doc_num"] or 0,
                "tokenNum": row["token_num"] or 0,
                "chunkNum": row["chunk_num"] or 0,
                "creatorName": row["creator_name"] or "",
                "orgId": row["org_id"],
                "orgName": row["org_name"] or "",
                "isDescendant": row["org_id"] != org_id,
                "createTime": row["create_date"].strftime("%Y-%m-%d %H:%M:%S") if row["create_date"] else "",
            })
        return formatted
    except mysql.connector.Error as err:
        print(f"DB error: {err}")
        return []


def get_org_files(org_id):
    """获取组织及所有子孙组织下所有知识库的文件列表"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)

        all_ids = [org_id]
        all_ids.extend(_get_subtree_ids(cursor, org_id))

        placeholders = ",".join(["%s"] * len(all_ids))
        query = f"""
        SELECT d.id, d.name, d.size, d.type, d.run, d.progress, d.create_date,
            kb.name as kb_name, kb.org_id,
            (SELECT o.name FROM organization o WHERE o.id = kb.org_id) as org_name
        FROM document d
        JOIN knowledgebase kb ON d.kb_id = kb.id
        WHERE kb.org_id IN ({placeholders}) AND kb.status = '1' AND d.status = '1'
        ORDER BY d.create_time DESC
        """
        cursor.execute(query, all_ids)
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        formatted = []
        for row in results:
            formatted.append({
                "id": row["id"],
                "name": row["name"],
                "size": row["size"] or 0,
                "type": row["type"] or "",
                "run": row["run"] or "0",
                "progress": float(row["progress"]) if row["progress"] else 0,
                "kbName": row["kb_name"] or "",
                "orgId": row["org_id"],
                "orgName": row["org_name"] or "",
                "isDescendant": row["org_id"] != org_id,
                "createTime": row["create_date"].strftime("%Y-%m-%d %H:%M:%S") if row["create_date"] else "",
            })
        return formatted
    except mysql.connector.Error as err:
        print(f"DB error: {err}")
        return []


def create_team(name, owner_id, description="", parent_id=None):
    """创建组织（支持 parent_id）"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # 校验 owner_id 存在
        cursor.execute("SELECT id FROM user WHERE id = %s", (owner_id,))
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            return None

        org_id = generate_uuid()
        now = datetime.now()
        ts = int(now.timestamp() * 1000)
        date_str = now.strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute(
            "INSERT INTO organization (id, create_time, create_date, update_time, update_date, name, description, owner_id, parent_id, status) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (org_id, ts, date_str, ts, date_str, name, description, owner_id, parent_id, "1"),
        )
        cursor.execute(
            "INSERT INTO org_member (id, create_time, create_date, update_time, update_date, org_id, user_id, role, invited_by, status) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (generate_uuid(), ts, date_str, ts, date_str, org_id, owner_id, "owner", owner_id, "1"),
        )
        conn.commit()
        cursor.close()
        conn.close()
        return org_id
    except mysql.connector.Error as err:
        print(f"DB error: {err}")
        return None


def update_team(team_id, name=None, description=None, owner_id=None, parent_id=None):
    """编辑组织"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)

        # 防止循环：parent_id 不能是自身或自身的子孙
        if parent_id:
            if parent_id == team_id:
                cursor.close()
                conn.close()
                return False
            subtree = _get_subtree_ids(cursor, team_id)
            if parent_id in subtree:
                cursor.close()
                conn.close()
                return False

        sets = []
        params = []
        if name is not None:
            sets.append("name = %s")
            params.append(name)
        if description is not None:
            sets.append("description = %s")
            params.append(description)
        if owner_id is not None:
            sets.append("owner_id = %s")
            params.append(owner_id)
        if parent_id is not None:
            sets.append("parent_id = %s")
            params.append(parent_id)

        if not sets:
            cursor.close()
            conn.close()
            return True

        now = datetime.now()
        ts = int(now.timestamp() * 1000)
        date_str = now.strftime("%Y-%m-%d %H:%M:%S")
        sets.append("update_time = %s")
        params.append(ts)
        sets.append("update_date = %s")
        params.append(date_str)
        params.append(team_id)

        cursor.execute(f"UPDATE organization SET {', '.join(sets)} WHERE id = %s AND status = '1'", params)
        affected = cursor.rowcount
        conn.commit()
        cursor.close()
        conn.close()
        return affected > 0
    except mysql.connector.Error as err:
        print(f"DB error: {err}")
        return False
