// Mock: 更新记录相关接口。
import type { MockMethod } from "vite-plugin-mock";

import { generateChanges } from "./rules";

export default [
  {
    url: /\/api\/changes/,
    method: "get",
    response: ({ query }) => {
      const textId = query?.text_id ? Number(query.text_id) : undefined;
      return {
        success: true,
        statusCode: 200,
        code: "0000",
        message: "操作成功",
        data: { items: generateChanges(textId) },
      };
    },
  },
] as MockMethod[];
