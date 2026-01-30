// Mock: 认证相关接口。
import type { MockMethod } from "vite-plugin-mock";

import { mockPermissions, mockRoles, mockUser } from "./data";

export default [
  {
    url: "/auth/login",
    method: "post",
    response: () => ({
      user: mockUser,
      roles: mockRoles,
      permissions: mockPermissions,
      token: "mock-token",
    }),
  },
] as MockMethod[];
