// 主文本列表页面。
import type { ActionType, ProColumns } from "@ant-design/pro-components";

import { ProTable } from "@ant-design/pro-components";
import { Button, Popconfirm, Popover, Tag, Typography, message } from "antd";
import { useEffect, useMemo, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { apiFetch, getErrorMessage } from "../../../api";
import { formatDateTime } from "../../../utils/datetime";

interface TextItem {
  id: number;
  fid: string;
  part: string;
  source_text: string | null;
  translated_text: string | null;
  status: number;
  edit_count: number;
  updated_at: string;
  claim_id: number | null;
  claimed_by: string | null;
  claimed_at: string | null;
  is_claimed: boolean;
}

interface TextListResponse {
  items: TextItem[];
  total: number;
  page: number;
  page_size: number;
}

interface QueryParams {
  fid?: string;
  status?: number;
  source_keyword?: string;
  translated_keyword?: string;
  updated_from?: string;
  updated_to?: string;
  claimer?: string;
  claimed?: string;
}

const statusMeta: Record<number, { label: string; color: string }> = {
  1: { label: "新增", color: "default" },
  2: { label: "修改", color: "processing" },
  3: { label: "已完成", color: "success" },
};

const DISPLAY_LIMIT = 200;
const TOOLTIP_LIMIT = 5000;
const MIN_ACTION_DELAY_MS = 300;

async function ensureMinDelay(startAt: number, minMs: number) {
  const elapsed = Date.now() - startAt;
  if (elapsed < minMs) {
    await new Promise((resolve) => setTimeout(resolve, minMs - elapsed));
  }
}

function truncateText(text: string, limit: number): string {
  if (text.length <= limit) {
    return text;
  }
  return `${text.slice(0, limit)}...`;
}

function renderLongText(value?: string | null) {
  const text = value || "";
  if (!text) {
    return "-";
  }
  const displayText = truncateText(text, DISPLAY_LIMIT);
  const tooltipText = truncateText(text, TOOLTIP_LIMIT);
  return (
    <Popover
      placement="rightTop"
      content={
        <div style={{ maxHeight: 320, overflowY: "auto", maxWidth: 620, whiteSpace: "pre-wrap" }}>
          {tooltipText}
        </div>
      }
    >
      <Typography.Text style={{ whiteSpace: "pre-wrap" }}>{displayText}</Typography.Text>
    </Popover>
  );
}

export default function TextsList() {
  const navigate = useNavigate();
  const location = useLocation();
  const actionRef = useRef<ActionType>();
  const [queryLoading, setQueryLoading] = useState(false);
  const [claimingId, setClaimingId] = useState<number | null>(null);
  const [releasingId, setReleasingId] = useState<number | null>(null);
  const [activeConfirm, setActiveConfirm] = useState<{ type: "claim" | "release"; id: number } | null>(null);

  useEffect(() => {
    const state = location.state as { refresh?: boolean } | null;
    if (state?.refresh) {
      actionRef.current?.reload();
      navigate(location.pathname, { replace: true, state: {} });
    }
  }, [location, navigate]);

  const columns: ProColumns<TextItem>[] = useMemo(
    () => [
      {
        title: "编号",
        dataIndex: "id",
        hideInSearch: true,
        render: (_, record) => (
          <Button type="link" onClick={() => navigate(`/texts/${record.id}`)}>
            {record.id}
          </Button>
        ),
      },
      { title: "FID", dataIndex: "fid", hideInSearch: true },
      { title: "Part", dataIndex: "part", hideInSearch: true },
      {
        title: "原文",
        dataIndex: "source_text",
        hideInSearch: true,
        width: 280,
        render: (_, record) => renderLongText(record.source_text),
      },
      {
        title: "译文",
        dataIndex: "translated_text",
        hideInSearch: true,
        width: 280,
        render: (_, record) => renderLongText(record.translated_text),
      },
      {
        title: "状态",
        dataIndex: "status",
        hideInSearch: true,
        render: (_, record) => {
          const meta = statusMeta[record.status];
          return <Tag color={meta?.color || "default"}>{meta?.label || "-"}</Tag>;
        },
      },
      { title: "编辑次数", dataIndex: "edit_count", hideInSearch: true },
      { title: "认领人", dataIndex: "claimed_by", hideInSearch: true, renderText: (val) => val || "-" },
      {
        title: "更新时间",
        dataIndex: "updated_at",
        hideInSearch: true,
        renderText: (val) => formatDateTime(val),
      },
      {
        title: "操作",
        valueType: "option",
        width: 160,
        render: (_, record) => [
          <Popconfirm
            key="claim"
            title="确认认领该文本？"
            okText="确认"
            cancelText="取消"
            trigger="click"
            okButtonProps={{ loading: claimingId === record.id }}
            open={activeConfirm?.type === "claim" && activeConfirm.id === record.id}
            onOpenChange={(open) => {
              if (record.is_claimed) {
                return;
              }
              if (open) {
                setActiveConfirm({ type: "claim", id: record.id });
              } else if (claimingId !== record.id) {
                setActiveConfirm(null);
              }
            }}
            onCancel={() => {
              if (claimingId !== record.id) {
                setActiveConfirm(null);
              }
            }}
            onConfirm={async () => {
              const startedAt = Date.now();
              try {
                setClaimingId(record.id);
                await apiFetch("/claims", {
                  method: "POST",
                  body: JSON.stringify({ text_id: record.id }),
                });
                message.success("认领成功");
                actionRef.current?.reload();
              } catch (error) {
                message.error(getErrorMessage(error, "认领失败"));
              } finally {
                await ensureMinDelay(startedAt, MIN_ACTION_DELAY_MS);
                setClaimingId(null);
                setActiveConfirm(null);
              }
            }}
            disabled={record.is_claimed}
          >
            <Button
              type="link"
              disabled={record.is_claimed || claimingId === record.id}
              loading={claimingId === record.id}
            >
              认领
            </Button>
          </Popconfirm>,
          <Popconfirm
            key="release"
            title="确认释放该文本？"
            okText="确认"
            cancelText="取消"
            trigger="click"
            okButtonProps={{ loading: releasingId === record.claim_id }}
            open={Boolean(record.claim_id) && activeConfirm?.type === "release" && activeConfirm.id === record.claim_id}
            onOpenChange={(open) => {
              if (!record.claim_id) {
                return;
              }
              if (open) {
                setActiveConfirm({ type: "release", id: record.claim_id });
              } else if (releasingId !== record.claim_id) {
                setActiveConfirm(null);
              }
            }}
            onCancel={() => {
              if (releasingId !== record.claim_id) {
                setActiveConfirm(null);
              }
            }}
            onConfirm={async () => {
              if (!record.claim_id) {
                return;
              }
              const startedAt = Date.now();
              try {
                setReleasingId(record.claim_id);
                await apiFetch(`/claims/${record.claim_id}`, { method: "DELETE" });
                message.success("释放成功");
                actionRef.current?.reload();
              } catch (error) {
                message.error(getErrorMessage(error, "释放失败"));
              } finally {
                await ensureMinDelay(startedAt, MIN_ACTION_DELAY_MS);
                setReleasingId(null);
                setActiveConfirm(null);
              }
            }}
            disabled={!record.claim_id}
          >
            <Button
              type="link"
              disabled={!record.claim_id || releasingId === record.claim_id}
              loading={releasingId === record.claim_id}
            >
              释放
            </Button>
          </Popconfirm>,
          <Button key="edit" type="link" onClick={() => navigate(`/texts/${record.id}/edit`)}>
            编辑
          </Button>,
          <Button key="changes" type="link" onClick={() => navigate(`/texts/${record.id}/changes`)}>
            更新记录
          </Button>,
        ],
      },
      { title: "FID", dataIndex: "fid", hideInTable: true },
      {
        title: "状态",
        dataIndex: "status",
        hideInTable: true,
        valueEnum: {
          1: { text: "新增" },
          2: { text: "修改" },
          3: { text: "已完成" },
        },
      },
      { title: "原文关键字", dataIndex: "source_keyword", hideInTable: true },
      { title: "汉化关键字", dataIndex: "translated_keyword", hideInTable: true },
      {
        title: "更新时间范围",
        dataIndex: "updated_at",
        valueType: "dateTimeRange",
        hideInTable: true,
        search: {
          transform: (value) => ({
            updated_from: value[0],
            updated_to: value[1],
          }),
        },
      },
      { title: "认领人", dataIndex: "claimer", hideInTable: true },
      {
        title: "是否认领",
        dataIndex: "claimed",
        valueType: "select",
        valueEnum: {
          true: { text: "已认领" },
          false: { text: "未认领" },
        },
        hideInTable: true,
      },
    ],
    [navigate, claimingId, releasingId, activeConfirm]
  );

  return (
    <ProTable<TextItem, QueryParams>
      rowKey="id"
      headerTitle="主文本列表"
      actionRef={actionRef}
      size="small"
      cardBordered
      options={false}
      search={{ labelWidth: "auto" }}
      toolBarRender={false}
      loading={queryLoading}
      request={async (params) => {
        setQueryLoading(true);
        try {
          const query = new URLSearchParams();
          query.set("page", String(params.current || 1));
          query.set("page_size", String(params.pageSize || 20));
          if (params.fid) query.set("fid", params.fid);
          if (params.status) query.set("status", String(params.status));
          if (params.source_keyword) query.set("source_keyword", params.source_keyword);
          if (params.translated_keyword) query.set("translated_keyword", params.translated_keyword);
          if (params.updated_from) query.set("updated_from", params.updated_from);
          if (params.updated_to) query.set("updated_to", params.updated_to);
          if (params.claimer) query.set("claimer", params.claimer);
          if (params.claimed) query.set("claimed", params.claimed);

          const response = await apiFetch<TextListResponse>(`/texts?${query.toString()}`);
          return {
            data: response.items,
            success: true,
            total: response.total,
          };
        } catch (error) {
          message.error(getErrorMessage(error, "加载列表失败"));
          return {
            data: [],
            success: false,
            total: 0,
          };
        } finally {
          setQueryLoading(false);
        }
      }}
      columns={columns}
    />
  );
}
