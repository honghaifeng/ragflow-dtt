import type * as Tables from "./type"
import { request } from "@/http/axios"

// 查询团队整体数据
export function getTableDataApi(params: Tables.TableRequestData) {
  return request<Tables.TableResponseData>({
    url: "api/v1/teams",
    method: "get",
    params
  })
}

// 获取团队成员列表
export function getTeamMembersApi(teamId: number) {
  return request({
    url: `api/v1/teams/${teamId}/members`,
    method: "get"
  })
}

// 添加团队成员
export function addTeamMemberApi(data: { teamId: number, userId: number, role: string }) {
  return request({
    url: `api/v1/teams/${data.teamId}/members`,
    method: "post",
    data
  })
}

// 移除团队成员
export function removeTeamMemberApi(data: { teamId: number, memberId: number }) {
  return request({
    url: `api/v1/teams/${data.teamId}/members/${data.memberId}`,
    method: "delete"
  })
}

// 创建组织
export function createTeamApi(data: { name: string, description?: string, owner_id?: string, parent_id?: string }) {
  return request({
    url: "api/v1/teams",
    method: "post",
    data
  })
}

// 删除组织
export function deleteTeamApi(teamId: string) {
  return request({
    url: `api/v1/teams/${teamId}`,
    method: "delete"
  })
}

// 获取组织树
export function getOrgTreeApi() {
  return request({
    url: "api/v1/teams/tree",
    method: "get"
  })
}

// 获取组织知识库列表
export function getOrgKnowledgebasesApi(teamId: string) {
  return request({
    url: `api/v1/teams/${teamId}/knowledgebases`,
    method: "get"
  })
}

// 获取组织文件列表
export function getOrgFilesApi(teamId: string) {
  return request({
    url: `api/v1/teams/${teamId}/files`,
    method: "get"
  })
}

// 修改成员角色
export function updateMemberRoleApi(teamId: string, userId: string, role: string) {
  return request({
    url: `api/v1/teams/${teamId}/members/${userId}/role`,
    method: "put",
    data: { role }
  })
}

// 编辑组织
export function updateTeamApi(teamId: string, data: { name?: string; description?: string; owner_id?: string; parent_id?: string | null }) {
  return request({
    url: `api/v1/teams/${teamId}`,
    method: "put",
    data
  })
}

/**
 * @description 获取用户列表
 * @param params 查询参数，例如 { size: number, currentPage: number, username: string }
 */
export function getUsersApi(params?: object) {
  return request({
    url: "api/v1/users",
    method: "get",
    params
  })
}
