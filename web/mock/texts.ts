// Mock: 主文本相关接口。
import type { MockMethod } from "vite-plugin-mock";

import { mockTexts } from "./data";

export default [
  {
    url: "/texts",
    method: "get",
    response: ({ query }) => {
      const keyword = query?.keyword as string | undefined;
      const items = keyword
        ? mockTexts.filter((item) =>
            item.source_text.includes(keyword) ||
            (item.translated_text || "").includes(keyword)
          )
        : mockTexts;
      return {
        items,
        total: items.length,
        page: 1,
        page_size: items.length,
      };
    },
  },
  {
    url: /\/texts\/\d+/,
    method: "get",
    response: ({ url }) => {
      const id = Number(url.split("/").pop());
      const text = mockTexts.find((item) => item.id === id) || mockTexts[0];
      return {
        text,
        claims: [],
        locks: [],
      };
    },
  },
] as MockMethod[];
