// 词典管理页面。
import { Button, Form, Input, Modal, Select, Table, Typography, message } from "antd";
import { ColumnsType } from "antd/es/table";
import { useEffect, useState } from "react";

import { apiFetch, getErrorMessage } from "../../../api";
import { formatDateTime } from "../../../utils/datetime";

interface DictionaryItem {
  id: number;
  termKey: string;
  termValue: string;
  category: string | null;
  isActive: boolean;
  uptTime: string;
}

interface DictionaryResponse {
  items: DictionaryItem[];
  total: number;
  page: number;
  pageSize: number;
}

const CATEGORY_LABELS: Record<string, string> = {
  skill: "技能",
  race: "种族",
  place: "地点",
  item: "物品",
  quest: "任务",
};

const CATEGORY_OPTIONS = Object.entries(CATEGORY_LABELS).map(([value, label]) => ({
  value,
  label,
}));

export default function Dictionary() {
  const [filterForm] = Form.useForm();
  const [createForm] = Form.useForm();
  const [data, setData] = useState<DictionaryItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [createVisible, setCreateVisible] = useState(false);
  const [filtering, setFiltering] = useState(false);
  const [creating, setCreating] = useState(false);

  const fetchData = async (filters?: { termKey?: string; termValue?: string; category?: string }) => {
    setLoading(true);
    try {
      const query = new URLSearchParams();
      query.set("page", "1");
      query.set("pageSize", "50");
      if (filters?.termKey) query.set("termKey", filters.termKey);
      if (filters?.termValue) query.set("termValue", filters.termValue);
      if (filters?.category) {
        query.set("category", filters.category);
      }
      const response = await apiFetch<DictionaryResponse>(`/dictionary?${query.toString()}`);
      setData(response.items);
    } catch (error) {
      message.error(getErrorMessage(error, "加载失败"));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void fetchData();
  }, []);

  const handleCreate = async () => {
    try {
      if (creating) {
        return;
      }
      setCreating(true);
      const values = await createForm.validateFields();
      await apiFetch("/dictionary", {
        method: "POST",
        body: JSON.stringify(values),
      });
      message.success("新增成功");
      createForm.resetFields();
      const filters = filterForm.getFieldsValue();
      await fetchData(filters);
      setCreateVisible(false);
    } catch (error) {
      message.error(getErrorMessage(error, "新增失败"));
    } finally {
      setCreating(false);
    }
  };

  const handleFilter = async () => {
    if (filtering) {
      return;
    }
    setFiltering(true);
    try {
      const values = await filterForm.validateFields();
      await fetchData(values);
    } finally {
      setFiltering(false);
    }
  };

  const handleReset = async () => {
    if (filtering) {
      return;
    }
    setFiltering(true);
    try {
      filterForm.resetFields();
      await fetchData();
    } finally {
      setFiltering(false);
    }
  };

  const columns: ColumnsType<DictionaryItem> = [
    { title: "原文 key", dataIndex: "termKey" },
    { title: "译文 value", dataIndex: "termValue" },
    {
      title: "分类",
      dataIndex: "category",
      render: (value) => (value ? CATEGORY_LABELS[value] || value : "-"),
    },
    { title: "更新时间", dataIndex: "uptTime", render: (val) => formatDateTime(val) },
  ];

  return (
    <div>
      <Typography.Title level={4}>词典管理</Typography.Title>
      <Form form={filterForm} layout="inline" style={{ marginBottom: 16 }}>
        <Form.Item name="termKey" label="原文">
          <Input placeholder="原文关键字" />
        </Form.Item>
        <Form.Item name="termValue" label="译文">
          <Input placeholder="译文关键字" />
        </Form.Item>
        <Form.Item name="category" label="分类">
          <Select
            allowClear
            options={CATEGORY_OPTIONS}
            placeholder="请选择分类"
            style={{ width: 160 }}
          />
        </Form.Item>
        <Button type="primary" onClick={handleFilter} loading={filtering}>
          查询
        </Button>
        <Button onClick={handleReset} loading={filtering}>
          重置
        </Button>
        <Button type="primary" onClick={() => setCreateVisible(true)}>
          新增
        </Button>
      </Form>
      <Table rowKey="id" size="small" columns={columns} dataSource={data} loading={loading} />
      <Modal
        title="新增词条"
        open={createVisible}
        onCancel={() => setCreateVisible(false)}
        onOk={handleCreate}
        okText="保存"
        cancelText="取消"
        confirmLoading={creating}
        destroyOnClose
      >
        <Form form={createForm} layout="vertical" preserve={false}>
          <Form.Item name="termKey" label="原文" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="termValue" label="译文" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="category" label="分类">
            <Select allowClear options={CATEGORY_OPTIONS} placeholder="请选择分类" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
