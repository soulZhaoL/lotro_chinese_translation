import type { ProColumns } from "@ant-design/pro-components";
import { Button, Form, Input, Popconfirm, Popover, Select, Space, Tag, Typography, message } from "antd";

import { apiFetch, getErrorMessage } from "../../../api";
import { formatDateTime } from "../../../utils/datetime";
import { TEXT_STATUS_META, TEXT_STATUS_VALUE_ENUM } from "../constants";
import type { ActiveConfirmState, TextItem, TextMatchMode } from "../types";

const DISPLAY_LIMIT = 200;
const TOOLTIP_LIMIT = 5000;
const MIN_ACTION_DELAY_MS = 300;
const ACTION_COLUMN_WIDTH = 220;
const POPOVER_MAX_WIDTH = "min(620px, calc(100vw - 48px))";
const TEXT_MATCH_MODE_VALUE_ENUM: Record<TextMatchMode, { text: string }> = {
  fuzzy: { text: "模糊" },
  exact: { text: "精确" },
};
const TEXT_MATCH_MODE_OPTIONS = Object.entries(TEXT_MATCH_MODE_VALUE_ENUM).map(([value, meta]) => ({
  value: value as TextMatchMode,
  label: meta.text,
}));

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
      placement="top"
      autoAdjustOverflow
      getPopupContainer={() => document.body}
      content={
        <div style={{ maxHeight: 320, overflowY: "auto", maxWidth: POPOVER_MAX_WIDTH, whiteSpace: "pre-wrap" }}>
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

type KeywordMatchFieldName = "sourceMatchMode" | "translatedMatchMode";

type KeywordMatchInputProps = {
  matchModeField: KeywordMatchFieldName;
  placeholder: string;
  value?: string;
  onChange?: (value: string) => void;
};

function KeywordMatchInput({ matchModeField, placeholder, value, onChange }: KeywordMatchInputProps) {
  const form = Form.useFormInstance();
  const matchMode = Form.useWatch(matchModeField, form) as TextMatchMode | undefined;

  return (
    <Input
      value={value}
      placeholder={placeholder}
      onChange={(event) => onChange?.(event.target.value)}
      addonAfter={
        <>
          <Form.Item name={matchModeField} initialValue="fuzzy" hidden noStyle>
            <Input />
          </Form.Item>
          <Select
            value={matchMode || "fuzzy"}
            options={TEXT_MATCH_MODE_OPTIONS}
            popupMatchSelectWidth={false}
            onChange={(nextValue) => form.setFieldValue(matchModeField, nextValue)}
            style={{ width: 84 }}
          />
        </>
      }
    />
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
              body: JSON.stringify({ id: record.id }),
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
  sourceMatchMode?: TextMatchMode;
  translatedKeyword?: string;
  translatedMatchMode?: TextMatchMode;
  onParentChanged: () => void;
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
  sourceMatchMode,
  translatedKeyword,
  translatedMatchMode,
  onParentChanged,
}: ParentColumnsDeps): ProColumns<TextItem>[] {
  return [
    {
      title: "编号",
      dataIndex: "id",
      hideInSearch: true,
      width: 88,
      fixed: "left",
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
      width: 110,
      fixed: "left",
      render: (_, record) => <Typography.Text copyable={{ text: record.fid }}>{record.fid}</Typography.Text>,
    },
    { title: "TextId", dataIndex: "textId", hideInSearch: true, width: 140 },
    { title: "Part", dataIndex: "part", hideInSearch: true, width: 90 },
    {
      title: "原文",
      dataIndex: "sourceText",
      hideInSearch: true,
      width: 360,
      render: (_, record) => renderLongText(record.sourceText, sourceMatchMode === "fuzzy" ? sourceKeyword : undefined),
    },
    {
      title: "译文",
      dataIndex: "translatedText",
      hideInSearch: true,
      width: 360,
      render: (_, record) =>
        renderLongText(record.translatedText, translatedMatchMode === "fuzzy" ? translatedKeyword : undefined),
    },
    {
      title: "状态",
      dataIndex: "status",
      hideInSearch: true,
      width: 100,
      render: (_, record) => {
        const meta = TEXT_STATUS_META[record.status];
        return <Tag color={meta?.color || "default"}>{meta?.label || "-"}</Tag>;
      },
    },
    { title: "编辑次数", dataIndex: "editCount", hideInSearch: true, width: 100 },
    { title: "认领人", dataIndex: "claimedBy", hideInSearch: true, width: 120, renderText: (val) => val || "-" },
    {
      title: "更新时间",
      dataIndex: "uptTime",
      hideInSearch: true,
      width: 190,
      renderText: (val) => formatDateTime(val),
    },
    {
      title: "操作",
      valueType: "option",
      width: ACTION_COLUMN_WIDTH,
      fixed: "right",
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
    { title: "TextId", dataIndex: "textId", hideInTable: true },
    {
      title: "状态",
      dataIndex: "status",
      hideInTable: true,
      valueEnum: TEXT_STATUS_VALUE_ENUM,
    },
    {
      title: "原文筛选",
      dataIndex: "sourceKeyword",
      hideInTable: true,
      renderFormItem: () => <KeywordMatchInput matchModeField="sourceMatchMode" placeholder="请输入原文" />,
    },
    {
      title: "原文匹配",
      dataIndex: "sourceMatchMode",
      valueType: "select",
      hideInTable: true,
      hideInSearch: true,
      initialValue: "fuzzy",
      valueEnum: TEXT_MATCH_MODE_VALUE_ENUM,
    },
    {
      title: "译文筛选",
      dataIndex: "translatedKeyword",
      hideInTable: true,
      renderFormItem: () => <KeywordMatchInput matchModeField="translatedMatchMode" placeholder="请输入译文" />,
    },
    {
      title: "译文匹配",
      dataIndex: "translatedMatchMode",
      valueType: "select",
      hideInTable: true,
      hideInSearch: true,
      initialValue: "fuzzy",
      valueEnum: TEXT_MATCH_MODE_VALUE_ENUM,
    },
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
