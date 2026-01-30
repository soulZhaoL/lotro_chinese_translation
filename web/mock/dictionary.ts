// Mock: 词典相关接口。
import type { MockMethod } from "vite-plugin-mock";

import { mockDictionary } from "./data";

export default [
  {
    url: "/dictionary",
    method: "get",
    response: ({ query }) => {
      const keyword = query?.keyword as string | undefined;
      const items = keyword
        ? mockDictionary.filter((item) =>
            item.term_key.includes(keyword) || item.term_value.includes(keyword)
          )
        : mockDictionary;
      return {
        items,
        total: items.length,
        page: 1,
        page_size: items.length,
      };
    },
  },
  {
    url: "/dictionary",
    method: "post",
    response: () => ({
      id: 999,
    }),
  },
  {
    url: /\/dictionary\/\d+/,
    method: "put",
    response: ({ url }) => ({
      id: Number(url.split("/").pop()),
    }),
  },
] as MockMethod[];
