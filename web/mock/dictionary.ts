// Mock: 词典相关接口。
import type { MockMethod } from "vite-plugin-mock";

import { generateDictionary } from "./rules";

export default [
  {
    url: "/api/dictionary",
    method: "get",
    response: ({ query }) => {
      const items = generateDictionary(query || {});
      return {
        success: true,
        statusCode: 200,
        code: "0000",
        message: "操作成功",
        data: {
          items,
          total: items.length,
          page: Number(query?.page || 1),
          pageSize: Number(query?.pageSize || items.length),
        },
      };
    },
  },
  {
    url: "/api/dictionary",
    method: "post",
    response: () => ({
      success: true,
      statusCode: 200,
      code: "0000",
      message: "操作成功",
      data: { id: Math.floor(Math.random() * 10000) + 1 },
    }),
  },
  {
    url: /\/api\/dictionary\/\d+/,
    method: "put",
    response: ({ url }) => ({
      success: true,
      statusCode: 200,
      code: "0000",
      message: "操作成功",
      data: { id: Number(url.split("/").pop()) },
    }),
  },
  {
    url: /\/api\/dictionary\/\d+\/correct/,
    method: "post",
    response: ({ url }) => ({
      success: true,
      statusCode: 200,
      code: "0000",
      message: "操作成功",
      data: {
        dictionaryId: Number(url.split("/").slice(-2)[0]),
        matchedTextCount: 12,
        updatedTextCount: 8,
        status: 3,
        statusLabel: "已完成",
        appliedCorrectionVersion: 2,
        startedAt: new Date().toISOString(),
        finishedAt: new Date().toISOString(),
        error: null,
      },
    }),
  },
] as MockMethod[];
