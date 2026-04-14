from flask import jsonify
from services.stats.service import get_overview_stats
from .. import stats_bp


@stats_bp.route('/overview', methods=['GET'])
def overview():
    """获取概览统计"""
    try:
        data = get_overview_stats()
        return jsonify({"code": 0, "data": data, "message": "获取统计数据成功"})
    except Exception as e:
        return jsonify({"code": 500, "message": f"获取统计数据失败: {str(e)}"}), 500
