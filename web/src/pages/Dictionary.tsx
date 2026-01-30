// 词典管理页面。
import { Button, Form, Input, Table, Typography } from "antd";
import { ColumnsType } from "antd/es/table";
import { useEffect, useState } from "react";

import { apiFetch } from "../api";

interface DictionaryItem {
  id: number;
  term_key: string;
  term_value: string;
  category: string | null;
  is_active: boolean;
  updated_at: string;
}

interface DictionaryResponse {
  items: DictionaryItem[];
  total: number;
  page: number;
  page_size: number;
}

export default function Dictionary() {
  const [form] = Form.useForm();
  const [data, setData] = useState<DictionaryItem[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchData = async () => {
    setLoading(true);
    try {
      const response = await apiFetch<DictionaryResponse>("/dictionary?page=1&page_size=50");
      setData(response.items);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void fetchData();
  }, []);

  const handleCreate = async () => {
    const values = await form.validateFields();
    await apiFetch("/dictionary", {
      method: "POST",
      body: JSON.stringify(values),
    });
    form.resetFields();
    await fetchData();
  };

  const columns: ColumnsType<DictionaryItem> = [
    { title: "原文 key", dataIndex: "term_key" },
    { title: "译文 value", dataIndex: "term_value" },
    { title: "分类", dataIndex: "category" },
    { title: "更新时间", dataIndex: "updated_at" },
  ];

  return (
    <div>
      <Typography.Title level={4}>词典管理</Typography.Title>
      <Form form={form} layout="inline" style={{ marginBottom: 16 }}>
        <Form.Item name="term_key" label="原文" rules={[{ required: true }]}>
          <Input />
        </Form.Item>
        <Form.Item name="term_value" label="译文" rules={[{ required: true }]}>
          <Input />
        </Form.Item>
        <Form.Item name="category" label="分类">
          <Input />
        </Form.Item>
        <Button type="primary" onClick={handleCreate}>
          新增
        </Button>
      </Form>
      <Table rowKey="id" columns={columns} dataSource={data} loading={loading} />
    </div>
  );
}
