from datetime import datetime

from api.db import OrgRole, StatusEnum
from api.db.db_models import DB, Organization, OrgMember, User, Knowledgebase
from api.db.services.common_service import CommonService
from api.utils import get_uuid, current_timestamp, datetime_format


# 角色优先级，数值越大权限越高
_ROLE_PRIORITY = {
    OrgRole.VIEWER: 1,
    OrgRole.EDITOR: 2,
    OrgRole.ADMIN: 3,
    OrgRole.OWNER: 4,
}


class OrganizationService(CommonService):
    model = Organization

    @classmethod
    @DB.connection_context()
    def create_org(cls, name, owner_id, description="", avatar="", parent_id=None):
        org_id = get_uuid()
        now = current_timestamp()
        now_date = datetime_format(datetime.now())
        Organization.create(
            id=org_id,
            name=name,
            description=description,
            avatar=avatar,
            owner_id=owner_id,
            parent_id=parent_id,
            status=StatusEnum.VALID.value,
            create_time=now,
            create_date=now_date,
            update_time=now,
            update_date=now_date,
        )
        OrgMember.create(
            id=get_uuid(),
            org_id=org_id,
            user_id=owner_id,
            role=OrgRole.OWNER,
            invited_by=owner_id,
            status=StatusEnum.VALID.value,
            create_time=now,
            create_date=now_date,
            update_time=now,
            update_date=now_date,
        )
        return org_id

    @classmethod
    @DB.connection_context()
    def list_by_user(cls, user_id):
        """返回用户所属的所有组织（含角色和 parent_id）"""
        fields = [
            cls.model.id,
            cls.model.name,
            cls.model.description,
            cls.model.avatar,
            cls.model.owner_id,
            cls.model.parent_id,
            cls.model.create_date,
            cls.model.update_date,
            OrgMember.role,
        ]
        return list(
            cls.model.select(*fields)
            .join(OrgMember, on=(cls.model.id == OrgMember.org_id))
            .where(
                OrgMember.user_id == user_id,
                OrgMember.status == StatusEnum.VALID.value,
                cls.model.status == StatusEnum.VALID.value,
            )
            .dicts()
        )

    @classmethod
    @DB.connection_context()
    def get_detail(cls, org_id):
        orgs = cls.model.select().where(
            cls.model.id == org_id,
            cls.model.status == StatusEnum.VALID.value,
        ).dicts()
        return list(orgs)[0] if orgs else None

    @classmethod
    @DB.connection_context()
    def update_org(cls, org_id, **kwargs):
        kwargs["update_time"] = current_timestamp()
        kwargs["update_date"] = datetime_format(datetime.now())
        return cls.model.update(kwargs).where(cls.model.id == org_id).execute()

    @classmethod
    @DB.connection_context()
    def delete_org(cls, org_id):
        """级联软删除组织及所有子组织"""
        now = current_timestamp()
        now_date = datetime_format(datetime.now())
        all_ids = cls.get_subtree_ids(org_id)
        all_ids.append(org_id)
        cls.model.update(
            status=StatusEnum.INVALID.value,
            update_time=now,
            update_date=now_date,
        ).where(cls.model.id.in_(all_ids)).execute()
        OrgMember.update(
            status=StatusEnum.INVALID.value,
            update_time=now,
            update_date=now_date,
        ).where(OrgMember.org_id.in_(all_ids)).execute()

    @classmethod
    @DB.connection_context()
    def get_kb_count(cls, org_id):
        return Knowledgebase.select().where(
            Knowledgebase.org_id == org_id,
            Knowledgebase.status == StatusEnum.VALID.value,
        ).count()

    # ======================== 树操作 ========================

    @classmethod
    @DB.connection_context()
    def get_children(cls, org_id):
        """获取直接子组织列表"""
        return list(
            cls.model.select()
            .where(
                cls.model.parent_id == org_id,
                cls.model.status == StatusEnum.VALID.value,
            )
            .dicts()
        )

    @classmethod
    @DB.connection_context()
    def get_subtree_ids(cls, org_id):
        """递归获取所有后代组织 ID（不含自身）"""
        result = []
        children = list(
            cls.model.select(cls.model.id)
            .where(
                cls.model.parent_id == org_id,
                cls.model.status == StatusEnum.VALID.value,
            )
            .dicts()
        )
        for child in children:
            result.append(child["id"])
            result.extend(cls.get_subtree_ids(child["id"]))
        return result

    @classmethod
    @DB.connection_context()
    def get_ancestors(cls, org_id):
        """从当前组织向上遍历所有祖先，返回 [parent, grandparent, ...]"""
        ancestors = []
        current = cls.get_detail(org_id)
        while current and current.get("parent_id"):
            parent = cls.get_detail(current["parent_id"])
            if not parent:
                break
            ancestors.append(parent)
            current = parent
        return ancestors

    @classmethod
    @DB.connection_context()
    def get_root(cls, org_id):
        """获取当前组织所属的根组织"""
        current = cls.get_detail(org_id)
        while current and current.get("parent_id"):
            parent = cls.get_detail(current["parent_id"])
            if not parent:
                break
            current = parent
        return current

    @classmethod
    @DB.connection_context()
    def get_all_valid(cls):
        """获取所有有效组织（管理后台用）"""
        return list(
            cls.model.select()
            .where(cls.model.status == StatusEnum.VALID.value)
            .order_by(cls.model.create_time.asc())
            .dicts()
        )

    @classmethod
    def build_tree(cls, orgs, parent_id=None):
        """将扁平列表构建为树形结构"""
        tree = []
        for org in orgs:
            pid = org.get("parent_id") or None
            if pid == parent_id:
                node = dict(org)
                node["children"] = cls.build_tree(orgs, org["id"])
                tree.append(node)
        return tree

    @classmethod
    @DB.connection_context()
    def get_user_org_tree(cls, user_id):
        """获取用户有权限的组织树"""
        user_orgs = cls.list_by_user(user_id)
        if not user_orgs:
            return []

        # 收集用户直接所属的组织 ID
        direct_org_ids = {org["id"] for org in user_orgs}
        role_map = {org["id"]: org["role"] for org in user_orgs}

        # 收集所有需要展示的组织（直接所属 + 祖先 + 后代）
        all_org_ids = set(direct_org_ids)

        # 添加祖先链（保证树结构完整）
        for org in user_orgs:
            ancestors = cls.get_ancestors(org["id"])
            for a in ancestors:
                all_org_ids.add(a["id"])

        # 对于 admin/owner，添加子组织树
        for org in user_orgs:
            if org["role"] in (OrgRole.OWNER, OrgRole.ADMIN):
                subtree = cls.get_subtree_ids(org["id"])
                all_org_ids.update(subtree)

        # 查询所有需要的组织
        all_orgs = list(
            cls.model.select()
            .where(
                cls.model.id.in_(list(all_org_ids)),
                cls.model.status == StatusEnum.VALID.value,
            )
            .dicts()
        )

        # 给每个组织标注用户的有效角色
        for org in all_orgs:
            org["role"] = cls._get_effective_role_from_map(org["id"], role_map, all_orgs)

        return cls.build_tree(all_orgs)

    @classmethod
    def _get_effective_role_from_map(cls, org_id, role_map, all_orgs):
        """根据角色映射和组织树，计算用户对某组织的有效角色"""
        # 直接角色
        if org_id in role_map:
            return role_map[org_id]

        # 从祖先继承
        org_dict = {o["id"]: o for o in all_orgs}
        current = org_dict.get(org_id)
        while current and current.get("parent_id"):
            parent_id = current["parent_id"]
            if parent_id in role_map:
                parent_role = role_map[parent_id]
                # owner 对子组织降级为 admin
                if parent_role == OrgRole.OWNER:
                    return OrgRole.ADMIN
                return parent_role
            current = org_dict.get(parent_id)
        return None


class OrgMemberService(CommonService):
    model = OrgMember

    @classmethod
    @DB.connection_context()
    def list_members(cls, org_id):
        fields = [
            cls.model.id,
            cls.model.user_id,
            cls.model.role,
            cls.model.create_date,
            User.nickname,
            User.email,
            User.avatar,
        ]
        return list(
            cls.model.select(*fields)
            .join(User, on=(cls.model.user_id == User.id))
            .where(
                cls.model.org_id == org_id,
                cls.model.status == StatusEnum.VALID.value,
            )
            .order_by(cls.model.create_time.asc())
            .dicts()
        )

    @classmethod
    @DB.connection_context()
    def add_member(cls, org_id, user_id, role, invited_by):
        existing = cls.model.select().where(
            cls.model.org_id == org_id,
            cls.model.user_id == user_id,
        ).first()
        now = current_timestamp()
        now_date = datetime_format(datetime.now())
        if existing:
            cls.model.update(
                role=role,
                status=StatusEnum.VALID.value,
                update_time=now,
                update_date=now_date,
            ).where(cls.model.id == existing.id).execute()
            return existing.id
        member_id = get_uuid()
        cls.model.create(
            id=member_id,
            org_id=org_id,
            user_id=user_id,
            role=role,
            invited_by=invited_by,
            status=StatusEnum.VALID.value,
            create_time=now,
            create_date=now_date,
            update_time=now,
            update_date=now_date,
        )
        return member_id

    @classmethod
    @DB.connection_context()
    def remove_member(cls, org_id, user_id):
        return cls.model.update(
            status=StatusEnum.INVALID.value,
            update_time=current_timestamp(),
            update_date=datetime_format(datetime.now()),
        ).where(
            cls.model.org_id == org_id,
            cls.model.user_id == user_id,
        ).execute()

    @classmethod
    @DB.connection_context()
    def update_role(cls, org_id, user_id, role):
        return cls.model.update(
            role=role,
            update_time=current_timestamp(),
            update_date=datetime_format(datetime.now()),
        ).where(
            cls.model.org_id == org_id,
            cls.model.user_id == user_id,
        ).execute()

    @classmethod
    @DB.connection_context()
    def get_member(cls, org_id, user_id):
        members = cls.model.select().where(
            cls.model.org_id == org_id,
            cls.model.user_id == user_id,
            cls.model.status == StatusEnum.VALID.value,
        ).dicts()
        return list(members)[0] if members else None

    @classmethod
    @DB.connection_context()
    def get_user_role(cls, org_id, user_id):
        """获取用户在某组织的直接角色"""
        member = cls.get_member(org_id, user_id)
        return member["role"] if member else None

    @classmethod
    @DB.connection_context()
    def get_effective_role(cls, org_id, user_id):
        """获取用户在某组织的有效角色（含继承）"""
        # 直接角色
        direct = cls.get_user_role(org_id, user_id)
        if direct:
            return direct

        # 向上查祖先
        org = OrganizationService.get_detail(org_id)
        while org and org.get("parent_id"):
            parent_role = cls.get_user_role(org["parent_id"], user_id)
            if parent_role:
                # owner 对子组织降级为 admin
                if parent_role == OrgRole.OWNER:
                    return OrgRole.ADMIN
                return parent_role
            org = OrganizationService.get_detail(org["parent_id"])
        return None

    @classmethod
    @DB.connection_context()
    def is_member(cls, org_id, user_id):
        """检查用户是否是组织成员（含继承）"""
        return cls.get_effective_role(org_id, user_id) is not None
