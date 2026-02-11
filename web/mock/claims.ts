// Mock: 认领相关接口。
import type { MockMethod } from "vite-plugin-mock";

export default [
  {
    url: "/api/claims",
    method: "post",
    response: () => ({
      success: true,
      statusCode: 200,
      code: "0000",
      message: "操作成功",
      data: { claimId: Math.floor(Math.random() * 10000) + 1 },
    }),
  },
  {
    url: /\/api\/claims\/\d+/,
    method: "delete",
    response: ({ url }) => ({
      success: true,
      statusCode: 200,
      code: "0000",
      message: "操作成功",
      data: { id: Number(url.split("/").pop()) },
    }),
  },
] as MockMethod[];
