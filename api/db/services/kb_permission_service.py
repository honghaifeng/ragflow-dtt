from datetime import datetime

from api.db import StatusEnum, KbPermissionLevel, OrgRole
from api.db.db_models import DB, KbPermission, OrgMember, Knowledgebase
from api.db.services.common_service import CommonService
from api.utils import get_uuid, current_timestamp, datetime_format


class KbPermissionService(CommonService):
    model = KbPermission

    @classmethod
    @DB.connection_context()
    def grant(cls, kb_id, target_type, target_id, permission, granted_by):
        """Grant permission. Upsert if already exists."""
        existing = cls.model.select().where(
            cls.model.kb_id == kb_id,
            cls.model.target_type == target_type,
            cls.model.target_id == target_id,
        ).first()
        now = current_timestamp()
        now_date = datetime_format(datetime.now())
        if existing:
            cls.model.update(
                permission=permission,
                granted_by=granted_by,
                update_time=now,
                update_date=now_date,
            ).where(cls.model.id == existing.id).execute()
            return existing.id
        perm_id = get_uuid()
        cls.model.create(
            id=perm_id,
            kb_id=kb_id,
            target_type=target_type,
            target_id=target_id,
            permission=permission,
            granted_by=granted_by,
            create_time=now,
            create_date=now_date,
            update_time=now,
            update_date=now_date,
        )
        return perm_id

    @classmethod
    @DB.connection_context()
    def revoke(cls, kb_id, target_type, target_id):
        return cls.model.delete().where(
            cls.model.kb_id == kb_id,
            cls.model.target_type == target_type,
            cls.model.target_id == target_id,
        ).execute()

    @classmethod
    @DB.connection_context()
    def list_permissions(cls, kb_id):
        return list(
            cls.model.select()
            .where(cls.model.kb_id == kb_id)
            .order_by(cls.model.create_time.asc())
            .dicts()
        )

    @classmethod
    @DB.connection_context()
    def check_user_permission(cls, kb_id, user_id):
        """Check user's effective permission on a KB.
        Returns permission level string or None.
        Priority: manage > edit > view.
        Checks: direct user grant, org membership grants, public grants.
        """
        kb = Knowledgebase.select().where(
            Knowledgebase.id == kb_id,
            Knowledgebase.status == StatusEnum.VALID.value,
        ).first()
        if not kb:
            return None

        # Owner always has manage access
        if kb.created_by == user_id:
            return KbPermissionLevel.MANAGE

        # Check KB permission type
        perm_type = kb.permission

        if perm_type == "private":
            return None

        if perm_type == "org" and kb.org_id:
            # Any org member can view; role-based for higher
            member = OrgMember.select().where(
                OrgMember.org_id == kb.org_id,
                OrgMember.user_id == user_id,
                OrgMember.status == StatusEnum.VALID.value,
            ).first()
            if member:
                role = member.role
                if role in (OrgRole.OWNER, OrgRole.ADMIN):
                    return KbPermissionLevel.MANAGE
                elif role == OrgRole.EDITOR:
                    return KbPermissionLevel.EDIT
                else:
                    return KbPermissionLevel.VIEW
            return None

        if perm_type == "custom":
            # Check direct user permission
            best = None
            rank = {KbPermissionLevel.VIEW: 1, KbPermissionLevel.EDIT: 2, KbPermissionLevel.MANAGE: 3}

            direct = cls.model.select().where(
                cls.model.kb_id == kb_id,
                cls.model.target_type == "user",
                cls.model.target_id == user_id,
            ).first()
            if direct:
                best = direct.permission

            # Check org permissions
            org_perms = (
                cls.model.select(cls.model.permission)
                .join(OrgMember, on=(
                    (cls.model.target_id == OrgMember.org_id) &
                    (cls.model.target_type == "org")
                ))
                .where(
                    cls.model.kb_id == kb_id,
                    OrgMember.user_id == user_id,
                    OrgMember.status == StatusEnum.VALID.value,
                )
                .dicts()
            )
            for op in org_perms:
                p = op["permission"]
                if best is None or rank.get(p, 0) > rank.get(best, 0):
                    best = p

            # Check public
            public = cls.model.select().where(
                cls.model.kb_id == kb_id,
                cls.model.target_type == "public",
            ).first()
            if public:
                p = public.permission
                if best is None or rank.get(p, 0) > rank.get(best, 0):
                    best = p

            return best

        # Fallback: legacy me/team — treat "team" like org for backward compat
        return None

    @classmethod
    @DB.connection_context()
    def user_can_access(cls, kb_id, user_id):
        """Boolean check: can user at least view this KB?"""
        return cls.check_user_permission(kb_id, user_id) is not None

    @classmethod
    @DB.connection_context()
    def user_can_edit(cls, kb_id, user_id):
        perm = cls.check_user_permission(kb_id, user_id)
        return perm in (KbPermissionLevel.EDIT, KbPermissionLevel.MANAGE)

    @classmethod
    @DB.connection_context()
    def user_can_manage(cls, kb_id, user_id):
        perm = cls.check_user_permission(kb_id, user_id)
        return perm == KbPermissionLevel.MANAGE
