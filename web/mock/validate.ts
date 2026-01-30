// Mock: 校验相关接口。
import type { MockMethod } from "vite-plugin-mock";

export default [
  {
    url: "/validate",
    method: "post",
    response: () => ({
      valid: true,
      errors: [],
    }),
  },
] as MockMethod[];
