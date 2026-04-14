import hashlib
import logging
from datetime import datetime, timedelta

from flask import request
from flask_login import login_required, current_user

from api import settings
from api.db import OrgRole, StatusEnum
from api.db.db_models import InvitationCode, User
from api.db.services.org_service import OrganizationService, OrgMemberService
from api.db.services.user_service import UserService
from api.utils import get_uuid
from api.utils.api_utils import (
    get_json_result,
    validate_request,
    server_error_response,
    get_data_error_result,
)


@manager.route("/my_role", methods=["GET"])  # noqa: F821
@login_required
def my_role():
    """返回当前用户在所有组织中的角色，用于前端判断导航显示"""
    try:
        orgs = OrganizationService.list_by_user(current_user.id)
        has_org_access = any(
            o["role"] in (OrgRole.OWNER, OrgRole.ADMIN) for o in orgs
        )
        return get_json_result(data={
            "has_org_access": has_org_access,
            "orgs": [
                {
                    "org_id": o["id"],
                    "org_name": o["name"],
                    "role": o["role"],
                    "parent_id": o.get("parent_id"),
                }
                for o in orgs
            ],
        })
    except Exception as e:
        return server_error_response(e)


@manager.route("/create", methods=["POST"])  # noqa: F821
@login_required
@validate_request("name")
def create_org():
    req = request.json
    parent_id = req.get("parent_id")
    try:
        # 如果有 parent_id，校验调用者对父组织有管理权限
        if parent_id:
            role = OrgMemberService.get_effective_role(parent_id, current_user.id)
            if role not in (OrgRole.OWNER, OrgRole.ADMIN):
                return get_json_result(
                    data=False, message="需要父组织的管理员权限才能创建子组织",
                    code=settings.RetCode.AUTHENTICATION_ERROR,
                )

        org_id = OrganizationService.create_org(
            name=req["name"],
            owner_id=current_user.id,
            description=req.get("description", ""),
            avatar=req.get("avatar", ""),
            parent_id=parent_id,
        )
        return get_json_result(data={"id": org_id})
    except Exception as e:
        return server_error_response(e)


@manager.route("/list", methods=["GET"])  # noqa: F821
@login_required
def list_orgs():
    """返回用户有权限的组织树"""
    try:
        tree = OrganizationService.get_user_org_tree(current_user.id)
        return get_json_result(data=tree)
    except Exception as e:
        return server_error_response(e)


@manager.route("/flat_list", methods=["GET"])  # noqa: F821
@login_required
def flat_list_orgs():
    """返回用户所属组织的扁平列表（兼容旧接口）"""
    try:
        orgs = OrganizationService.list_by_user(current_user.id)
        for org in orgs:
            org["member_count"] = len(OrgMemberService.list_members(org["id"]))
            org["kb_count"] = OrganizationService.get_kb_count(org["id"])
        return get_json_result(data=orgs)
    except Exception as e:
        return server_error_response(e)


@manager.route("/<org_id>", methods=["GET"])  # noqa: F821
@login_required
def get_org(org_id):
    try:
        org = OrganizationService.get_detail(org_id)
        if not org:
            return get_data_error_result(message="Organization not found.")
        if not OrgMemberService.is_member(org_id, current_user.id):
            return get_json_result(
                data=False, message="No authorization.",
                code=settings.RetCode.AUTHENTICATION_ERROR,
            )
        org["members"] = OrgMemberService.list_members(org_id)
        org["kb_count"] = OrganizationService.get_kb_count(org_id)
        org["children"] = OrganizationService.get_children(org_id)
        org["ancestors"] = OrganizationService.get_ancestors(org_id)
        return get_json_result(data=org)
    except Exception as e:
        return server_error_response(e)


@manager.route("/<org_id>/children", methods=["GET"])  # noqa: F821
@login_required
def get_children(org_id):
    """获取直接子组织"""
    try:
        if not OrgMemberService.is_member(org_id, current_user.id):
            return get_json_result(
                data=False, message="No authorization.",
                code=settings.RetCode.AUTHENTICATION_ERROR,
            )
        children = OrganizationService.get_children(org_id)
        return get_json_result(data=children)
    except Exception as e:
        return server_error_response(e)


@manager.route("/<org_id>/update", methods=["PUT"])  # noqa: F821
@login_required
def update_org(org_id):
    try:
        role = OrgMemberService.get_effective_role(org_id, current_user.id)
        if role not in (OrgRole.OWNER, OrgRole.ADMIN):
            return get_json_result(
                data=False, message="No authorization.",
                code=settings.RetCode.AUTHENTICATION_ERROR,
            )
        req = request.json
        update = {}
        for k in ("name", "description", "avatar"):
            if k in req:
                update[k] = req[k]
        if update:
            OrganizationService.update_org(org_id, **update)
        return get_json_result(data=True)
    except Exception as e:
        return server_error_response(e)


@manager.route("/<org_id>/delete", methods=["DELETE"])  # noqa: F821
@login_required
def delete_org(org_id):
    try:
        role = OrgMemberService.get_effective_role(org_id, current_user.id)
        if role not in (OrgRole.OWNER, OrgRole.ADMIN):
            return get_json_result(
                data=False, message="只有拥有者或管理员可以删除组织",
                code=settings.RetCode.AUTHENTICATION_ERROR,
            )
        OrganizationService.delete_org(org_id)
        return get_json_result(data=True)
    except Exception as e:
        return server_error_response(e)


@manager.route("/<org_id>/members", methods=["GET"])  # noqa: F821
@login_required
def list_members(org_id):
    try:
        if not OrgMemberService.is_member(org_id, current_user.id):
            return get_json_result(
                data=False, message="No authorization.",
                code=settings.RetCode.AUTHENTICATION_ERROR,
            )
        members = OrgMemberService.list_members(org_id)
        return get_json_result(data=members)
    except Exception as e:
        return server_error_response(e)


@manager.route("/<org_id>/member/add", methods=["POST"])  # noqa: F821
@login_required
@validate_request("email")
def add_member(org_id):
    try:
        role = OrgMemberService.get_effective_role(org_id, current_user.id)
        if role not in (OrgRole.OWNER, OrgRole.ADMIN):
            return get_json_result(
                data=False, message="No authorization.",
                code=settings.RetCode.AUTHENTICATION_ERROR,
            )
        req = request.json
        emails = req.get("emails", [req["email"]]) if "emails" in req else [req["email"]]
        member_role = req.get("role", OrgRole.VIEWER)
        if member_role not in (OrgRole.ADMIN, OrgRole.EDITOR, OrgRole.VIEWER):
            return get_data_error_result(message="Invalid role.")

        added = []
        not_found = []
        for email in emails:
            users = UserService.query(email=email)
            if not users:
                not_found.append(email)
                continue
            user = users[0]
            OrgMemberService.add_member(org_id, user.id, member_role, current_user.id)
            added.append({"user_id": user.id, "email": email, "nickname": user.nickname})

        return get_json_result(data={"added": added, "not_found": not_found})
    except Exception as e:
        return server_error_response(e)


@manager.route("/<org_id>/member/<user_id>/remove", methods=["DELETE"])  # noqa: F821
@login_required
def remove_member(org_id, user_id):
    try:
        role = OrgMemberService.get_effective_role(org_id, current_user.id)
        if role not in (OrgRole.OWNER, OrgRole.ADMIN):
            return get_json_result(
                data=False, message="No authorization.",
                code=settings.RetCode.AUTHENTICATION_ERROR,
            )
        target_role = OrgMemberService.get_user_role(org_id, user_id)
        if target_role == OrgRole.OWNER:
            return get_data_error_result(message="Cannot remove the owner.")
        OrgMemberService.remove_member(org_id, user_id)
        return get_json_result(data=True)
    except Exception as e:
        return server_error_response(e)


@manager.route("/<org_id>/member/<user_id>/role", methods=["PUT"])  # noqa: F821
@login_required
@validate_request("role")
def change_role(org_id, user_id):
    try:
        my_role = OrgMemberService.get_effective_role(org_id, current_user.id)
        if my_role not in (OrgRole.OWNER, OrgRole.ADMIN):
            return get_json_result(
                data=False, message="No authorization.",
                code=settings.RetCode.AUTHENTICATION_ERROR,
            )
        new_role = request.json["role"]
        if new_role == OrgRole.OWNER:
            return get_data_error_result(message="Cannot assign owner role.")
        if new_role not in (OrgRole.ADMIN, OrgRole.EDITOR, OrgRole.VIEWER):
            return get_data_error_result(message="Invalid role.")
        OrgMemberService.update_role(org_id, user_id, new_role)
        return get_json_result(data=True)
    except Exception as e:
        return server_error_response(e)


@manager.route("/<org_id>/invite-link", methods=["POST"])  # noqa: F821
@login_required
def create_invite_link(org_id):
    try:
        role = OrgMemberService.get_effective_role(org_id, current_user.id)
        if role not in (OrgRole.OWNER, OrgRole.ADMIN):
            return get_json_result(
                data=False, message="No authorization.",
                code=settings.RetCode.AUTHENTICATION_ERROR,
            )
        req = request.json or {}
        expire_hours = req.get("expire_hours", 72)
        max_uses = req.get("max_uses", 0)

        code = hashlib.md5(f"{org_id}{get_uuid()}".encode()).hexdigest()[:16]
        from api.utils import current_timestamp, datetime_format
        now = current_timestamp()
        now_date = datetime_format(datetime.now())
        expire_time = datetime.now() + timedelta(hours=expire_hours)

        InvitationCode.create(
            id=get_uuid(),
            code=code,
            org_id=org_id,
            user_id=current_user.id,
            expire_time=expire_time,
            max_uses=max_uses,
            used_count=0,
            status=StatusEnum.VALID.value,
            create_time=now,
            create_date=now_date,
            update_time=now,
            update_date=now_date,
        )
        return get_json_result(data={"code": code, "expire_time": str(expire_time)})
    except Exception as e:
        return server_error_response(e)


@manager.route("/join/<invite_code>", methods=["POST"])  # noqa: F821
@login_required
def join_by_invite(invite_code):
    try:
        invites = InvitationCode.select().where(
            InvitationCode.code == invite_code,
            InvitationCode.status == StatusEnum.VALID.value,
        )
        if not invites:
            return get_data_error_result(message="Invalid invite code.")

        invite = invites[0]
        if not invite.org_id:
            return get_data_error_result(message="This invite code is not for an organization.")

        if invite.expire_time and datetime.now() > invite.expire_time:
            return get_data_error_result(message="Invite link has expired.")

        if invite.max_uses > 0 and invite.used_count >= invite.max_uses:
            return get_data_error_result(message="Invite link usage limit reached.")

        org = OrganizationService.get_detail(invite.org_id)
        if not org:
            return get_data_error_result(message="Organization not found.")

        if OrgMemberService.get_user_role(invite.org_id, current_user.id):
            return get_data_error_result(message="You are already a member.")

        OrgMemberService.add_member(
            invite.org_id, current_user.id, OrgRole.VIEWER, invite.user_id,
        )
        InvitationCode.update(
            used_count=InvitationCode.used_count + 1,
        ).where(InvitationCode.id == invite.id).execute()

        return get_json_result(data={"org_id": invite.org_id, "org_name": org["name"]})
    except Exception as e:
        return server_error_response(e)
