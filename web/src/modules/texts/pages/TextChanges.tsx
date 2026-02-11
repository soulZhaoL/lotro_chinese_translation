// 更新记录页面。
import { Table, message } from "antd";
import { ColumnsType } from "antd/es/table";
import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { apiFetch, getErrorMessage } from "../../../api";
import { formatDateTime } from "../../../utils/datetime";

interface ChangeItem {
  id: number;
  textId: number;
  userId: number;
  beforeText: string;
  afterText: string;
  reason: string | null;
  changedAt: string;
}

interface ChangesResponse {
  items: ChangeItem[];
}

interface TextDetailResponse {
  text: {
    id: number;
  };
}

export default function TextChanges() {
  const params = useParams();
  const fid = params.fid || "";
  const textId = Number(params.textId);
  const [data, setData] = useState<ChangeItem[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const detail = await apiFetch<TextDetailResponse>(
          `/texts/by-textid?fid=${encodeURIComponent(fid)}&textId=${textId}`
        );
        const response = await apiFetch<ChangesResponse>(`/changes?textId=${detail.text.id}`);
        setData(response.items);
      } catch (error) {
        message.error(getErrorMessage(error, "加载失败"));
      } finally {
        setLoading(false);
      }
    };
    if (fid && Number.isFinite(textId)) {
      void load();
    }
  }, [fid, textId]);

  const columns: ColumnsType<ChangeItem> = [
    { title: "时间", dataIndex: "changedAt", render: (val) => formatDateTime(val) },
    { title: "用户", dataIndex: "userId" },
    { title: "原因", dataIndex: "reason" },
  ];

  return (
    <div>
      <Table rowKey="id" size="small" columns={columns} dataSource={data} loading={loading} />
    </div>
  );
}
