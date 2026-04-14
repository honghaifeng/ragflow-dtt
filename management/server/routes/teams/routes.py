from flask import jsonify, request
from services.teams.service import (
    get_teams_with_pagination, get_team_by_id, delete_team,
    get_team_members, add_team_member, remove_team_member,
    create_team, update_team, get_org_tree, update_member_role,
    get_org_knowledgebases, get_org_files,
)
from services.auth import get_current_user_from_token, is_admin
from .. import teams_bp


@teams_bp.route('', methods=['GET'])
def get_teams():
    """获取组织列表（分页）"""
    try:
        current_user = get_current_user_from_token()

        current_page = int(request.args.get('currentPage', 1))
        page_size = int(request.args.get('size', 10))
        team_name = request.args.get('name', '')
        sort_by = request.args.get("sort_by", "create_time")
        sort_order = request.args.get("sort_order", "desc")

        tenant_id = None
        if current_user and not is_admin(current_user):
            tenant_id = current_user.get("tenant_id")

        teams, total = get_teams_with_pagination(current_page, page_size, team_name, sort_by, sort_order, tenant_id)

        return jsonify({
            "code": 0,
            "data": {"list": teams, "total": total},
            "message": "获取组织列表成功"
        })
    except Exception as e:
        return jsonify({"code": 500, "message": f"获取组织列表失败: {str(e)}"}), 500


@teams_bp.route('/tree', methods=['GET'])
def get_tree():
    """获取完整组织树"""
    try:
        tree = get_org_tree()
        return jsonify({"code": 0, "data": tree, "message": "获取组织树成功"})
    except Exception as e:
        return jsonify({"code": 500, "message": f"获取组织树失败: {str(e)}"}), 500


@teams_bp.route('', methods=['POST'])
def create_team_route():
    """创建组织"""
    try:
        data = request.json
        name = data.get('name')
        description = data.get('description', '')
        owner_id = data.get('owner_id')
        parent_id = data.get('parent_id')

        if not name:
            return jsonify({"code": 400, "message": "组织名称不能为空"}), 400
        if not owner_id:
            current_user = get_current_user_from_token()
            if current_user:
                owner_id = current_user.get('id') or current_user.get('user_id')
            if not owner_id:
                return jsonify({"code": 400, "message": "请指定组织负责人"}), 400

        org_id = create_team(name, owner_id, description, parent_id)
        if org_id:
            return jsonify({"code": 0, "data": {"id": org_id}, "message": "创建组织成功"})
        else:
            return jsonify({"code": 500, "message": "创建组织失败"}), 500
    except Exception as e:
        return jsonify({"code": 500, "message": f"创建组织失败: {str(e)}"}), 500


@teams_bp.route('/<string:team_id>', methods=['GET'])
def get_team(team_id):
    """获取单个组织详情"""
    try:
        team = get_team_by_id(team_id)
        if team:
            return jsonify({"code": 0, "data": team, "message": "获取组织详情成功"})
        else:
            return jsonify({"code": 404, "message": f"组织不存在"}), 404
    except Exception as e:
        return jsonify({"code": 500, "message": f"获取组织详情失败: {str(e)}"}), 500


@teams_bp.route('/<string:team_id>', methods=['PUT'])
def update_team_route(team_id):
    """编辑组织"""
    try:
        data = request.json
        success = update_team(
            team_id,
            name=data.get('name'),
            description=data.get('description'),
            owner_id=data.get('owner_id'),
            parent_id=data.get('parent_id'),
        )
        if success:
            return jsonify({"code": 0, "message": "组织更新成功"})
        else:
            return jsonify({"code": 400, "message": "更新失败（组织不存在或上级组织设置无效）"}), 400
    except Exception as e:
        return jsonify({"code": 500, "message": f"更新组织失败: {str(e)}"}), 500


@teams_bp.route('/<string:team_id>', methods=['DELETE'])
def delete_team_route(team_id):
    """删除组织（级联删除子组织）"""
    try:
        success = delete_team(team_id)
        if success:
            return jsonify({"code": 0, "message": "组织删除成功"})
        else:
            return jsonify({"code": 404, "message": "组织不存在或删除失败"}), 404
    except Exception as e:
        return jsonify({"code": 500, "message": f"删除组织失败: {str(e)}"}), 500


@teams_bp.route('/<string:team_id>/members', methods=['GET'])
def get_team_members_route(team_id):
    """获取组织成员"""
    try:
        members = get_team_members(team_id)
        return jsonify({"code": 0, "data": members, "message": "获取组织成员成功"})
    except Exception as e:
        return jsonify({"code": 500, "message": f"获取组织成员失败: {str(e)}"}), 500


@teams_bp.route('/<string:team_id>/members', methods=['POST'])
def add_team_member_route(team_id):
    """添加组织成员"""
    try:
        data = request.json
        user_id = data.get('userId')
        role = data.get('role', 'viewer')
        success = add_team_member(team_id, user_id, role)
        if success:
            return jsonify({"code": 0, "message": "添加成员成功"})
        else:
            return jsonify({"code": 400, "message": "添加成员失败"}), 400
    except Exception as e:
        return jsonify({"code": 500, "message": f"添加成员失败: {str(e)}"}), 500


@teams_bp.route('/<string:team_id>/members/<string:user_id>', methods=['DELETE'])
def remove_team_member_route(team_id, user_id):
    """移除组织成员"""
    try:
        success = remove_team_member(team_id, user_id)
        if success:
            return jsonify({"code": 0, "message": "移除成员成功"})
        else:
            return jsonify({"code": 400, "message": "移除成员失败（不能移除拥有者）"}), 400
    except Exception as e:
        return jsonify({"code": 500, "message": f"移除成员失败: {str(e)}"}), 500


@teams_bp.route('/<string:team_id>/members/<string:user_id>/role', methods=['PUT'])
def update_member_role_route(team_id, user_id):
    """修改成员角色"""
    try:
        data = request.json
        role = data.get('role')
        if role not in ('admin', 'editor', 'viewer'):
            return jsonify({"code": 400, "message": "无效的角色"}), 400
        success = update_member_role(team_id, user_id, role)
        if success:
            return jsonify({"code": 0, "message": "角色修改成功"})
        else:
            return jsonify({"code": 400, "message": "角色修改失败（不能修改拥有者角色）"}), 400
    except Exception as e:
        return jsonify({"code": 500, "message": f"角色修改失败: {str(e)}"}), 500


@teams_bp.route('/<string:team_id>/knowledgebases', methods=['GET'])
def get_org_knowledgebases_route(team_id):
    """获取组织的知识库列表"""
    try:
        kbs = get_org_knowledgebases(team_id)
        return jsonify({"code": 0, "data": kbs, "message": "获取知识库列表成功"})
    except Exception as e:
        return jsonify({"code": 500, "message": f"获取知识库列表失败: {str(e)}"}), 500


@teams_bp.route('/<string:team_id>/files', methods=['GET'])
def get_org_files_route(team_id):
    """获取组织的文件列表"""
    try:
        files = get_org_files(team_id)
        return jsonify({"code": 0, "data": files, "message": "获取文件列表成功"})
    except Exception as e:
        return jsonify({"code": 500, "message": f"获取文件列表失败: {str(e)}"}), 500
