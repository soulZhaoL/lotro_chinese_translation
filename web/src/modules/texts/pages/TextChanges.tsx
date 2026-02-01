// 更新记录页面。
import { Table, message } from "antd";
import { ColumnsType } from "antd/es/table";
import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { apiFetch, getErrorMessage } from "../../../api";
import { formatDateTime } from "../../../utils/datetime";

interface ChangeItem {
  id: number;
  text_id: number;
  user_id: number;
  before_text: string;
  after_text: string;
  reason: string | null;
  changed_at: string;
}

interface ChangesResponse {
  items: ChangeItem[];
}

export default function TextChanges() {
  const params = useParams();
  const textId = Number(params.id);
  const [data, setData] = useState<ChangeItem[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const response = await apiFetch<ChangesResponse>(`/changes?text_id=${textId}`);
        setData(response.items);
      } catch (error) {
        message.error(getErrorMessage(error, "加载失败"));
      } finally {
        setLoading(false);
      }
    };
    if (Number.isFinite(textId)) {
      void load();
    }
  }, [textId]);

  const columns: ColumnsType<ChangeItem> = [
    { title: "时间", dataIndex: "changed_at", render: (val) => formatDateTime(val) },
    { title: "用户", dataIndex: "user_id" },
    { title: "原因", dataIndex: "reason" },
  ];

  return (
    <div>
      <Table rowKey="id" size="small" columns={columns} dataSource={data} loading={loading} />
    </div>
  );
}
