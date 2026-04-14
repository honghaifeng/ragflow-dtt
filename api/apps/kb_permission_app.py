import logging
from flask import request
from flask_login import login_required, current_user

from api import settings
from api.db import KbPermissionLevel
from api.db.services.kb_permission_service import KbPermissionService
from api.db.services.knowledgebase_service import KnowledgebaseService
from api.utils.api_utils import (
    get_json_result,
    validate_request,
    server_error_response,
    get_data_error_result,
)


page_name = "kb_permission"


@manager.route("/<kb_id>/list", methods=["GET"])  # noqa: F821
@login_required
def list_permissions(kb_id):
    try:
        if not KbPermissionService.user_can_manage(kb_id, current_user.id):
            return get_json_result(
                data=False, message="No authorization.",
                code=settings.RetCode.AUTHENTICATION_ERROR,
            )
        perms = KbPermissionService.list_permissions(kb_id)
        return get_json_result(data=perms)
    except Exception as e:
        return server_error_response(e)


@manager.route("/<kb_id>/grant", methods=["POST"])  # noqa: F821
@login_required
@validate_request("target_type", "permission")
def grant_permission(kb_id):
    try:
        if not KbPermissionService.user_can_manage(kb_id, current_user.id):
            return get_json_result(
                data=False, message="No authorization.",
                code=settings.RetCode.AUTHENTICATION_ERROR,
            )
        req = request.json
        target_type = req["target_type"]
        target_id = req.get("target_id", "")
        permission = req["permission"]
        if target_type not in ("user", "org", "public"):
            return get_data_error_result(message="Invalid target_type.")
        if permission not in (KbPermissionLevel.VIEW, KbPermissionLevel.EDIT, KbPermissionLevel.MANAGE):
            return get_data_error_result(message="Invalid permission level.")
        perm_id = KbPermissionService.grant(
            kb_id, target_type, target_id, permission, current_user.id,
        )
        return get_json_result(data={"id": perm_id})
    except Exception as e:
        return server_error_response(e)


@manager.route("/<kb_id>/revoke", methods=["DELETE"])  # noqa: F821
@login_required
@validate_request("target_type", "target_id")
def revoke_permission(kb_id):
    try:
        if not KbPermissionService.user_can_manage(kb_id, current_user.id):
            return get_json_result(
                data=False, message="No authorization.",
                code=settings.RetCode.AUTHENTICATION_ERROR,
            )
        req = request.json
        KbPermissionService.revoke(kb_id, req["target_type"], req["target_id"])
        return get_json_result(data=True)
    except Exception as e:
        return server_error_response(e)


@manager.route("/<kb_id>/check", methods=["GET"])  # noqa: F821
@login_required
def check_permission(kb_id):
    try:
        perm = KbPermissionService.check_user_permission(kb_id, current_user.id)
        return get_json_result(data={"permission": perm})
    except Exception as e:
        return server_error_response(e)
