// Mock: 锁定相关接口。
import type { MockMethod } from "vite-plugin-mock";

export default [
  {
    url: "/locks",
    method: "post",
    response: () => ({
      lock_id: 1,
      expires_at: "2026-01-30T12:00:00Z",
    }),
  },
  {
    url: /\/locks\/\d+/,
    method: "delete",
    response: () => ({
      released_at: "2026-01-30T11:30:00Z",
    }),
  },
] as MockMethod[];
