import { request } from "@/http/axios"

export function getOverviewStatsApi() {
  return request({
    url: "api/v1/stats/overview",
    method: "get"
  })
}
