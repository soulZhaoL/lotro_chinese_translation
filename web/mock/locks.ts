// Mock: 锁定相关接口。
import type { MockMethod } from "vite-plugin-mock";

export default [
  {
    url: "/api/locks",
    method: "post",
    response: () => ({
      success: true,
      statusCode: 200,
      code: "0000",
      message: "操作成功",
      data: {
        lockId: 1,
        expiresAt: "2026-01-30T12:00:00Z",
      },
    }),
  },
  {
    url: /\/api\/locks\/\d+/,
    method: "delete",
    response: () => ({
      success: true,
      statusCode: 200,
      code: "0000",
      message: "操作成功",
      data: {
        releasedAt: "2026-01-30T11:30:00Z",
      },
    }),
  },
] as MockMethod[];
