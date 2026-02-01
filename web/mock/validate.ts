// Mock: 校验相关接口。
import type { MockMethod } from "vite-plugin-mock";

export default [
  {
    url: "/api/validate",
    method: "post",
    response: ({ body }) => {
      const text = (body?.translated_text || "") as string;
      const errors = [] as string[];
      if (!text.trim()) {
        errors.push("译文不能为空");
      }
      return {
        success: true,
        statusCode: 200,
        code: "0000",
        message: "操作成功",
        data: { valid: errors.length === 0, errors },
      };
    },
  },
] as MockMethod[];
