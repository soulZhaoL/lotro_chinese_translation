// Mock: 认证相关接口。
import type { MockMethod } from "vite-plugin-mock";

export default [
  {
    url: "/api/auth/login",
    method: "post",
    response: ({ body }) => {
      const username = body?.username || "tester";
      return {
        success: true,
        statusCode: 200,
        code: "0000",
        message: "操作成功",
        data: {
          user: { id: 1, username, isGuest: false },
          roles: ["translator"],
          permissions: ["text.read", "text.write", "dictionary.read", "dictionary.write"],
          token: "mock-token",
        },
      };
    },
  },
] as MockMethod[];
