import type { ProColumns } from "@ant-design/pro-components";
import { Button, Input, Popconfirm, Popover, Space, Table, Tag, Typography, message } from "antd";
import type { ColumnsType } from "antd/es/table";
import { type Dispatch, type SetStateAction } from "react";

import { apiFetch, getErrorMessage } from "../../../../api";
import { formatDateTime } from "../../../../utils/datetime";

export interface TextItem {
  id: number;
  fid: string;
  textId: number;
  part: number;
  sourceText: string | null;
  translatedText: string | null;
  status: number;
  editCount: number;
  uptTime: string;
  crtTime: string;
  claimId: number | null;
  claimedBy: string | null;
  claimedAt: string | null;
  isClaimed: boolean;
}

export interface TextListResponse {
  items: TextItem[];
  total: number;
  page: number;
  pageSize: number;
}

export interface QueryParams {
  fid?: string;
  status?: number | string;
  sourceKeyword?: string;
  translatedKeyword?: string;
  updatedFrom?: string;
  updatedTo?: string;
  claimer?: string;
  claimed?: string | boolean;
}

export type ChildQuery = {
  page: number;
  pageSize: number;
  textId?: string;
};

export type ChildState = ChildQuery & {
  items: TextItem[];
  total: number;
  loading: boolean;
};

export type ListStateSnapshot = {
  search: QueryParams;
  page: number;
  pageSize: number;
  expandedRowKeys: Array<string | number>;
  childQueries: Record<string, ChildQuery>;
};

export type ActiveConfirmState = { type: "claim" | "release"; id: number } | null;

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

function escapeRegExp(value: string) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function renderHighlightedText(text: string, keyword?: string) {
  const safeKeyword = keyword?.trim();
  if (!safeKeyword) {
    return text;
  }
  const parts = text.split(new RegExp(`(${escapeRegExp(safeKeyword)})`, "ig"));
  if (parts.length <= 1) {
    return text;
  }
  return (
    <>
      {parts.map((part, index) => {
        if (part.toLowerCase() === safeKeyword.toLowerCase()) {
          return (
            <mark
              key={String(index)}
              style={{
                padding: "0 2px",
                borderRadius: 3,
                background: "#ffec3d",
                color: "#000",
                boxShadow: "inset 0 0 0 1px #fadb14",
              }}
            >
              {part}
            </mark>
          );
        }
        return <span key={String(index)}>{part}</span>;
      })}
    </>
  );
}

function renderLongText(value?: string | null, highlightKeyword?: string) {
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
          {renderHighlightedText(tooltipText, highlightKeyword)}
        </div>
      }
    >
      <Typography.Text style={{ whiteSpace: "pre-wrap" }}>
        {renderHighlightedText(displayText, highlightKeyword)}
      </Typography.Text>
    </Popover>
  );
}

type TextRowActionsProps = {
  record: TextItem;
  claimingId: number | null;
  releasingId: number | null;
  activeConfirm: ActiveConfirmState;
  setClaimingId: (value: number | null) => void;
  setReleasingId: (value: number | null) => void;
  setActiveConfirm: (value: ActiveConfirmState) => void;
  navigateWithState: (path: string) => void;
  onChanged: () => void;
  releaseLoading: boolean;
  size?: number;
};

function TextRowActions({
  record,
  claimingId,
  releasingId,
  activeConfirm,
  setClaimingId,
  setReleasingId,
  setActiveConfirm,
  navigateWithState,
  onChanged,
  releaseLoading,
  size = 6,
}: TextRowActionsProps) {
  return (
    <Space size={size} wrap={false}>
      <Popconfirm
        title="确认认领该文本？"
        okText="确认"
        cancelText="取消"
        trigger="click"
        okButtonProps={{ loading: claimingId === record.id }}
        open={activeConfirm?.type === "claim" && activeConfirm.id === record.id}
        onOpenChange={(open) => {
          if (record.isClaimed) {
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
              body: JSON.stringify({ textId: record.id }),
            });
            message.success("认领成功");
            onChanged();
          } catch (error) {
            message.error(getErrorMessage(error, "认领失败"));
          } finally {
            await ensureMinDelay(startedAt, MIN_ACTION_DELAY_MS);
            setClaimingId(null);
            setActiveConfirm(null);
          }
        }}
        disabled={record.isClaimed}
      >
        <Button
          type="link"
          size="small"
          style={{ paddingInline: 0 }}
          disabled={record.isClaimed || claimingId === record.id}
          loading={claimingId === record.id}
        >
          认领
        </Button>
      </Popconfirm>

      <Popconfirm
        title="确认释放该文本？"
        okText="确认"
        cancelText="取消"
        trigger="click"
        okButtonProps={{ loading: releasingId === record.claimId }}
        open={Boolean(record.claimId) && activeConfirm?.type === "release" && activeConfirm.id === record.claimId}
        onOpenChange={(open) => {
          if (!record.claimId) {
            return;
          }
          if (open) {
            setActiveConfirm({ type: "release", id: record.claimId });
          } else if (releasingId !== record.claimId) {
            setActiveConfirm(null);
          }
        }}
        onCancel={() => {
          if (releasingId !== record.claimId) {
            setActiveConfirm(null);
          }
        }}
        onConfirm={async () => {
          if (!record.claimId) {
            return;
          }
          const startedAt = Date.now();
          try {
            setReleasingId(record.claimId);
            await apiFetch(`/claims/${record.claimId}`, { method: "DELETE" });
            message.success("释放成功");
            onChanged();
          } catch (error) {
            message.error(getErrorMessage(error, "释放失败"));
          } finally {
            await ensureMinDelay(startedAt, MIN_ACTION_DELAY_MS);
            setReleasingId(null);
            setActiveConfirm(null);
          }
        }}
        disabled={!record.claimId}
      >
        <Button
          type="link"
          size="small"
          style={{ paddingInline: 0 }}
          disabled={!record.claimId || releasingId === record.claimId}
          loading={releaseLoading && releasingId === record.claimId}
        >
          释放
        </Button>
      </Popconfirm>

      <Button
        type="link"
        size="small"
        style={{ paddingInline: 0 }}
        onClick={() => navigateWithState(`/texts/${record.fid}/${record.textId}/edit`)}
      >
        编辑
      </Button>
      <Button
        type="link"
        size="small"
        style={{ paddingInline: 0 }}
        onClick={() => navigateWithState(`/texts/${record.fid}/${record.textId}/changes`)}
      >
        更新记录
      </Button>
    </Space>
  );
}

type CommonActionDeps = {
  claimingId: number | null;
  releasingId: number | null;
  activeConfirm: ActiveConfirmState;
  setClaimingId: (value: number | null) => void;
  setReleasingId: (value: number | null) => void;
  setActiveConfirm: (value: ActiveConfirmState) => void;
  navigateWithState: (path: string) => void;
};

type ParentColumnsDeps = CommonActionDeps & {
  sourceKeyword?: string;
  translatedKeyword?: string;
  onParentChanged: () => void;
};

type ChildColumnsDeps = CommonActionDeps & {
  sourceKeyword?: string;
  translatedKeyword?: string;
  onChildChanged: (fid: string) => void;
};

export function createParentColumns({
  claimingId,
  releasingId,
  activeConfirm,
  setClaimingId,
  setReleasingId,
  setActiveConfirm,
  navigateWithState,
  sourceKeyword,
  translatedKeyword,
  onParentChanged,
}: ParentColumnsDeps): ProColumns<TextItem>[] {
  return [
    {
      title: "编号",
      dataIndex: "id",
      hideInSearch: true,
      render: (_, record) => (
        <Button type="link" onClick={() => navigateWithState(`/texts/${record.fid}/${record.textId}`)}>
          {record.id}
        </Button>
      ),
    },
    {
      title: "FID",
      dataIndex: "fid",
      hideInSearch: true,
      render: (_, record) => <Typography.Text copyable={{ text: record.fid }}>{record.fid}</Typography.Text>,
    },
    { title: "TextId", dataIndex: "textId", hideInSearch: true },
    { title: "Part", dataIndex: "part", hideInSearch: true },
    {
      title: "原文",
      dataIndex: "sourceText",
      hideInSearch: true,
      width: 280,
      render: (_, record) => renderLongText(record.sourceText, sourceKeyword),
    },
    {
      title: "译文",
      dataIndex: "translatedText",
      hideInSearch: true,
      width: 280,
      render: (_, record) => renderLongText(record.translatedText, translatedKeyword),
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
    { title: "编辑次数", dataIndex: "editCount", hideInSearch: true },
    { title: "认领人", dataIndex: "claimedBy", hideInSearch: true, renderText: (val) => val || "-" },
    {
      title: "更新时间",
      dataIndex: "uptTime",
      hideInSearch: true,
      renderText: (val) => formatDateTime(val),
    },
    {
      title: "操作",
      valueType: "option",
      width: 160,
      render: (_, record) => (
        <TextRowActions
          record={record}
          claimingId={claimingId}
          releasingId={releasingId}
          activeConfirm={activeConfirm}
          setClaimingId={setClaimingId}
          setReleasingId={setReleasingId}
          setActiveConfirm={setActiveConfirm}
          navigateWithState={navigateWithState}
          onChanged={onParentChanged}
          releaseLoading={false}
        />
      ),
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
    { title: "原文关键字", dataIndex: "sourceKeyword", hideInTable: true },
    { title: "汉化关键字", dataIndex: "translatedKeyword", hideInTable: true },
    {
      title: "更新时间范围",
      dataIndex: "uptTime",
      valueType: "dateTimeRange",
      hideInTable: true,
      search: {
        transform: (value) => ({
          updatedFrom: value[0],
          updatedTo: value[1],
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
  ];
}

export function createChildColumns({
  claimingId,
  releasingId,
  activeConfirm,
  setClaimingId,
  setReleasingId,
  setActiveConfirm,
  navigateWithState,
  sourceKeyword,
  translatedKeyword,
  onChildChanged,
}: ChildColumnsDeps): ColumnsType<TextItem> {
  return [
    {
      title: "TextId",
      dataIndex: "textId",
      width: 120,
      render: (_, record) => (
        <Typography.Link
          copyable={{ text: String(record.textId) }}
          onClick={(event) => {
            const target = event.target as HTMLElement;
            if (target.closest("button.ant-typography-copy")) {
              return;
            }
            event.preventDefault();
            navigateWithState(`/texts/${record.fid}/${record.textId}`);
          }}
        >
          {record.textId}
        </Typography.Link>
      ),
    },
    { title: "Part", dataIndex: "part", width: 80 },
    {
      title: "原文",
      dataIndex: "sourceText",
      width: 400,
      render: (_, record) => renderLongText(record.sourceText, sourceKeyword),
    },
    {
      title: "译文",
      dataIndex: "translatedText",
      width: 400,
      render: (_, record) => renderLongText(record.translatedText, translatedKeyword),
    },
    {
      title: "状态",
      dataIndex: "status",
      width: 90,
      render: (_, record) => {
        const meta = statusMeta[record.status];
        return <Tag color={meta?.color || "default"}>{meta?.label || "-"}</Tag>;
      },
    },
    {
      title: "认领人",
      dataIndex: "claimedBy",
      width: 120,
      render: (_, record) => record.claimedBy || "-",
    },
    {
      title: "更新时间",
      dataIndex: "uptTime",
      render: (_, record) => formatDateTime(record.uptTime),
    },
    {
      title: "操作",
      key: "action",
      width: 168,
      render: (_, record) => (
        <TextRowActions
          record={record}
          claimingId={claimingId}
          releasingId={releasingId}
          activeConfirm={activeConfirm}
          setClaimingId={setClaimingId}
          setReleasingId={setReleasingId}
          setActiveConfirm={setActiveConfirm}
          navigateWithState={navigateWithState}
          onChanged={() => onChildChanged(record.fid)}
          releaseLoading
          size={4}
        />
      ),
    },
  ];
}

export function createEmptyChildState(page = 1, pageSize = 10): ChildState {
  return {
    items: [],
    total: 0,
    page,
    pageSize,
    textId: undefined,
    loading: false,
  };
}

type ChildTablePanelProps = {
  parent: TextItem;
  state: ChildState;
  childColumns: ColumnsType<TextItem>;
  fetchChildren: (fid: string, overrides?: Partial<ChildQuery>) => void;
  setChildStates: Dispatch<SetStateAction<Record<string, ChildState>>>;
  handleChildSearch: (fid: string, value: string) => void;
};

export function ChildTablePanel({
  parent,
  state,
  childColumns,
  fetchChildren,
  setChildStates,
  handleChildSearch,
}: ChildTablePanelProps) {
  return (
    <div
      style={{
        padding: 12,
        background: "#fafafa",
        border: "1px solid #f0f0f0",
        borderLeft: "3px solid #1677ff",
        borderRadius: 8,
        boxShadow: "0 1px 2px rgba(0,0,0,0.04)",
        margin: "8px 0",
      }}
    >
      <Space style={{ marginBottom: 8 }}>
        <Input.Search
          placeholder="textId"
          allowClear
          value={state.textId ?? ""}
          onChange={(event) => {
            const value = event.target.value;
            setChildStates((prev) => ({
              ...prev,
              [parent.fid]: {
                ...(prev[parent.fid] || state),
                textId: value,
              },
            }));
          }}
          onSearch={(value) => handleChildSearch(parent.fid, value)}
          style={{ width: 200 }}
        />
        <Button
          onClick={() => {
            setChildStates((prev) => ({
              ...prev,
              [parent.fid]: {
                ...(prev[parent.fid] || state),
                textId: undefined,
              },
            }));
            fetchChildren(parent.fid, { page: 1, textId: undefined });
          }}
        >
          重置
        </Button>
      </Space>
      <Table
        rowKey="id"
        size="small"
        columns={childColumns}
        dataSource={state.items}
        loading={state.loading}
        pagination={{
          current: state.page,
          pageSize: state.pageSize,
          total: state.total,
          showSizeChanger: true,
          onChange: (page, pageSize) => {
            fetchChildren(parent.fid, { page, pageSize });
          },
        }}
      />
    </div>
  );
}
