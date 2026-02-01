// Mock: 主文本相关接口。
import type { MockMethod } from "vite-plugin-mock";

import { generateTextDetail, generateTexts } from "./rules";

export default [
  {
    url: "/api/texts",
    method: "get",
    response: ({ query }) => {
      const items = generateTexts(query || {});
      return {
        success: true,
        statusCode: 200,
        code: "0000",
        message: "操作成功",
        data: {
          items,
          total: items.length,
          page: Number(query?.page || 1),
          page_size: Number(query?.page_size || items.length),
        },
      };
    },
  },
  {
    url: /\/api\/texts\/\d+$/,
    method: "get",
    response: ({ url }) => {
      const id = Number(url.split("/").pop());
      const text = generateTextDetail(id);
      return {
        success: true,
        statusCode: 200,
        code: "0000",
        message: "操作成功",
        data: {
          text,
          claims: text.claim_id
            ? [{ id: text.claim_id, user_id: 1, claimed_at: text.claimed_at }]
            : [],
          locks: [],
        },
      };
    },
  },
  {
    url: /\/api\/texts\/\d+\/translate/,
    method: "put",
    response: ({ url, body }) => {
      const id = Number(url.split("/").slice(-2)[0]);
      const isCompleted = Boolean(body?.is_completed);
      return {
        success: true,
        statusCode: 200,
        code: "0000",
        message: "操作成功",
        data: { id, status: isCompleted ? 3 : 2 },
      };
    },
  },
] as MockMethod[];
