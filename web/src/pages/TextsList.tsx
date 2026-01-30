// 主文本列表页面。
import { Button, Input, Table, Typography } from "antd";
import { ColumnsType } from "antd/es/table";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { apiFetch } from "../api";

interface TextItem {
  id: number;
  fid: string;
  part: string;
  source_text: string;
  translated_text: string | null;
  status: string;
  edit_count: number;
  updated_at: string;
}

interface TextListResponse {
  items: TextItem[];
  total: number;
  page: number;
  page_size: number;
}

export default function TextsList() {
  const [data, setData] = useState<TextItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [keyword, setKeyword] = useState("");
  const navigate = useNavigate();

  const fetchData = async (query = "") => {
    setLoading(true);
    try {
      const url = new URLSearchParams();
      url.set("page", "1");
      url.set("page_size", "20");
      if (query) {
        url.set("keyword", query);
      }
      const response = await apiFetch<TextListResponse>(`/texts?${url.toString()}`);
      setData(response.items);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void fetchData();
  }, []);

  const columns: ColumnsType<TextItem> = [
    { title: "FID", dataIndex: "fid" },
    { title: "Part", dataIndex: "part" },
    { title: "状态", dataIndex: "status" },
    { title: "更新时间", dataIndex: "updated_at" },
  ];

  return (
    <div>
      <Typography.Title level={4}>主文本列表</Typography.Title>
      <div style={{ display: "flex", gap: 12, marginBottom: 16 }}>
        <Input
          placeholder="关键词搜索"
          value={keyword}
          onChange={(event) => setKeyword(event.target.value)}
        />
        <Button type="primary" onClick={() => fetchData(keyword)}>
          搜索
        </Button>
      </div>
      <Table
        rowKey="id"
        columns={columns}
        dataSource={data}
        loading={loading}
        onRow={(record) => ({
          onClick: () => navigate(`/texts/${record.id}/translate`),
        })}
      />
    </div>
  );
}
