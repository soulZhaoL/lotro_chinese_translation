// 主文本列表页面。
import type { ActionType, ProColumns } from "@ant-design/pro-components";

import { ProTable } from "@ant-design/pro-components";
import { Alert, Button, Input, Popconfirm, Popover, Space, Table, Tag, Typography, message } from "antd";
import type { ProFormInstance } from "@ant-design/pro-form";
import type { ColumnsType } from "antd/es/table";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { apiFetch, getErrorMessage } from "../../../api";
import { formatDateTime } from "../../../utils/datetime";

interface TextItem {
  id: number;
  fid: string;
  textId: number;
  part: number;
  sourceText: string | null;
  translatedText: string | null;
  status: number;
  editCount: number;
  updatedAt: string;
  createdAt: string;
  claimId: number | null;
  claimedBy: string | null;
  claimedAt: string | null;
  isClaimed: boolean;
}

interface TextListResponse {
  items: TextItem[];
  total: number;
  page: number;
  pageSize: number;
}

interface QueryParams {
  fid?: string;
  status?: number;
  sourceKeyword?: string;
  translatedKeyword?: string;
  updatedFrom?: string;
  updatedTo?: string;
  claimer?: string;
  claimed?: string;
}

type ChildQuery = {
  page: number;
  pageSize: number;
  textId?: string;
};

type ChildState = ChildQuery & {
  items: TextItem[];
  total: number;
  loading: boolean;
};

type ListStateSnapshot = {
  search: QueryParams;
  page: number;
  pageSize: number;
  expandedRowKeys: React.Key[];
  childQueries: Record<string, ChildQuery>;
};

const statusMeta: Record<number, { label: string; color: string }> = {
  1: { label: "新增", color: "default" },
  2: { label: "修改", color: "processing" },
  3: { label: "已完成", color: "success" },
};

const DISPLAY_LIMIT = 200;
const TOOLTIP_LIMIT = 5000;
const MIN_ACTION_DELAY_MS = 300;
const STORAGE_KEY = "texts_list_state";

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

function parseStoredState(): ListStateSnapshot | null {
  const raw = sessionStorage.getItem(STORAGE_KEY);
  if (!raw) {
    return null;
  }
  try {
    return JSON.parse(raw) as ListStateSnapshot;
  } catch {
    return null;
  }
}

export default function TextsList() {
  const navigate = useNavigate();
  const location = useLocation();
  const actionRef = useRef<ActionType>();
  const formRef = useRef<ProFormInstance<QueryParams> | undefined>(undefined);
  const [queryLoading, setQueryLoading] = useState(false);
  const [claimingId, setClaimingId] = useState<number | null>(null);
  const [releasingId, setReleasingId] = useState<number | null>(null);
  const [activeConfirm, setActiveConfirm] = useState<{ type: "claim" | "release"; id: number } | null>(null);
  const [parentSearch, setParentSearch] = useState<QueryParams>({});
  const [parentPage, setParentPage] = useState(1);
  const [parentPageSize, setParentPageSize] = useState(20);
  const [expandedRowKeys, setExpandedRowKeys] = useState<React.Key[]>([]);
  const [childStates, setChildStates] = useState<Record<string, ChildState>>({});
  const [pageFids, setPageFids] = useState<string[]>([]);
  const childStatesRef = useRef<Record<string, ChildState>>({});
  const parentSearchRef = useRef<QueryParams>({});

  useEffect(() => {
    childStatesRef.current = childStates;
  }, [childStates]);

  useEffect(() => {
    parentSearchRef.current = parentSearch;
  }, [parentSearch]);

  const buildListState = useCallback((): ListStateSnapshot => {
    const childQueries: Record<string, ChildQuery> = {};
    Object.entries(childStates).forEach(([fid, state]) => {
      childQueries[fid] = {
        page: state.page,
        pageSize: state.pageSize,
        textId: state.textId,
      };
    });
    return {
      search: parentSearch,
      page: parentPage,
      pageSize: parentPageSize,
      expandedRowKeys,
      childQueries,
    };
  }, [childStates, expandedRowKeys, parentPage, parentPageSize, parentSearch]);

  const persistListState = useCallback(
    (snapshot: ListStateSnapshot) => {
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(snapshot));
    },
    []
  );

  useEffect(() => {
    persistListState(buildListState());
  }, [buildListState, persistListState]);

  const fetchChildren = useCallback(async (fid: string, overrides?: Partial<ChildQuery>) => {
    const current = childStatesRef.current[fid] || {
      items: [],
      total: 0,
      page: 1,
      pageSize: 10,
      textId: undefined,
      loading: false,
    };
    const hasOverrideTextId = Boolean(overrides && Object.prototype.hasOwnProperty.call(overrides, "textId"));
    const nextQuery: ChildQuery = {
      page: overrides?.page ?? current.page,
      pageSize: overrides?.pageSize ?? current.pageSize,
      textId: hasOverrideTextId ? overrides?.textId : current.textId,
    };

    setChildStates((prev) => ({
      ...prev,
      [fid]: {
        ...(prev[fid] || current),
        ...nextQuery,
        loading: true,
      },
    }));

    try {
      const query = new URLSearchParams();
      query.set("fid", fid);
      query.set("page", String(nextQuery.page));
      query.set("pageSize", String(nextQuery.pageSize));
      if (nextQuery.textId) {
        query.set("textId", nextQuery.textId);
      }
      const sourceKeyword = parentSearchRef.current.sourceKeyword;
      if (sourceKeyword) {
        query.set("sourceKeyword", sourceKeyword);
      }
      const translatedKeyword = parentSearchRef.current.translatedKeyword;
      if (translatedKeyword) {
        query.set("translatedKeyword", translatedKeyword);
      }
      const response = await apiFetch<TextListResponse>(`/texts/children?${query.toString()}`);
      setChildStates((prev) => ({
        ...prev,
        [fid]: {
          ...(prev[fid] || current),
          ...nextQuery,
          items: response.items,
          total: response.total,
          loading: false,
        },
      }));
    } catch (error) {
      message.error(getErrorMessage(error, "加载子列表失败"));
      setChildStates((prev) => ({
        ...prev,
        [fid]: {
          ...(prev[fid] || current),
          ...nextQuery,
          items: [],
          total: 0,
          loading: false,
        },
      }));
    }
  }, []);

  useEffect(() => {
    const state = location.state as { listState?: ListStateSnapshot; refresh?: boolean } | null;
    const stored = state?.listState || parseStoredState();
    if (stored) {
      const restoredExpandedKeys = stored.expandedRowKeys || [];
      const normalizedExpandedKeys = restoredExpandedKeys.length ? [restoredExpandedKeys[0]] : [];
      setParentSearch(stored.search || {});
      setParentPage(stored.page || 1);
      setParentPageSize(stored.pageSize || 20);
      setExpandedRowKeys(normalizedExpandedKeys);
      const nextChildStates: Record<string, ChildState> = {};
      Object.entries(stored.childQueries || {}).forEach(([fid, query]) => {
        if (!normalizedExpandedKeys.includes(fid)) {
          return;
        }
        nextChildStates[fid] = {
          items: [],
          total: 0,
          loading: false,
          page: query.page,
          pageSize: query.pageSize,
          textId: query.textId,
        };
      });
      setChildStates(nextChildStates);
      if (formRef.current) {
        formRef.current.setFieldsValue(stored.search || {});
      }
      normalizedExpandedKeys.forEach((key) => {
        const fid = String(key);
        fetchChildren(fid, stored.childQueries?.[fid]);
      });
    }
    if (state?.listState || state?.refresh) {
      navigate(location.pathname, { replace: true, state: {} });
    }
    if (state?.refresh) {
      actionRef.current?.reload();
    }
  }, [fetchChildren, location.pathname, location.state, navigate]);

  const navigateWithState = useCallback(
    (path: string) => {
      const snapshot = buildListState();
      persistListState(snapshot);
      navigate(path, { state: { listState: snapshot } });
    },
    [buildListState, navigate, persistListState]
  );

  const handleChildSearch = useCallback(
    (fid: string, value: string) => {
      const trimmed = value.trim();
      if (trimmed && !/^\d+$/.test(trimmed)) {
        message.warning("textId 仅支持数字");
        return;
      }
      fetchChildren(fid, { page: 1, textId: trimmed || undefined });
    },
    [fetchChildren]
  );

  const keywordActive = Boolean(parentSearch.sourceKeyword || parentSearch.translatedKeyword);

  const expandFirstOnPage = useCallback(() => {
    const first = pageFids[0];
    if (!first) {
      return;
    }
    setExpandedRowKeys([first]);
    fetchChildren(first);
  }, [fetchChildren, pageFids]);

  const collapseAll = useCallback(() => {
    setExpandedRowKeys([]);
  }, []);

  const columns: ProColumns<TextItem>[] = useMemo(
    () => [
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
        render: (_, record) => renderLongText(record.sourceText, parentSearch.sourceKeyword),
      },
      {
        title: "译文",
        dataIndex: "translatedText",
        hideInSearch: true,
        width: 280,
        render: (_, record) => renderLongText(record.translatedText, parentSearch.translatedKeyword),
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
        dataIndex: "updatedAt",
        hideInSearch: true,
        renderText: (val) => formatDateTime(val),
      },
      {
        title: "操作",
        valueType: "option",
        width: 160,
        render: (_, record) => (
          <Space size={6} wrap={false}>
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
                  actionRef.current?.reload();
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
                  actionRef.current?.reload();
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
                // loading={releasingId === record.claimId}
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
        dataIndex: "updatedAt",
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
    ],
    [
      activeConfirm,
      claimingId,
      releasingId,
      navigateWithState,
      parentSearch.sourceKeyword,
      parentSearch.translatedKeyword,
    ]
  );

  const childColumns: ColumnsType<TextItem> = useMemo(
    () => [
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
        render: (_, record) => renderLongText(record.sourceText, parentSearch.sourceKeyword),
      },
      {
        title: "译文",
        dataIndex: "translatedText",
        width: 400,
        render: (_, record) => renderLongText(record.translatedText, parentSearch.translatedKeyword),
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
        renderText: (val: TextItem["claimedBy"]) => val || "-",
      },
      {
        title: "更新时间",
        dataIndex: "updatedAt",
        renderText: (val: TextItem["updatedAt"]) => formatDateTime(val),
      },
      {
        title: "操作",
        key: "action",
        width: 168,
        render: (_, record) => (
          <Space size={4} wrap={false}>
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
                  fetchChildren(record.fid);
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
                  fetchChildren(record.fid);
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
                loading={releasingId === record.claimId}
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
        ),
      },
    ],
    [
      activeConfirm,
      claimingId,
      releasingId,
      navigateWithState,
      fetchChildren,
      parentSearch.sourceKeyword,
      parentSearch.translatedKeyword,
    ]
  );

  const renderChildTable = (parent: TextItem) => {
    const state = childStates[parent.fid] || {
      items: [],
      total: 0,
      page: 1,
      pageSize: 10,
      textId: undefined,
      loading: false,
    };
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
  };

  return (
    <>
      {keywordActive ? (
        <Alert
          type="info"
          showIcon
          style={{ marginBottom: 8 }}
          message="关键字筛选会同时匹配子列表内容；如需定位命中项，可展开查看。"
          action={
            <Space size={8}>
              <Button size="small" onClick={expandFirstOnPage} disabled={!pageFids.length}>
                展开首条
              </Button>
              <Button size="small" onClick={collapseAll} disabled={!expandedRowKeys.length}>
                全部收起
              </Button>
            </Space>
          }
        />
      ) : null}
      <ProTable<TextItem, QueryParams>
        rowKey="fid"
        headerTitle="主文本列表"
        actionRef={actionRef}
        formRef={formRef}
        size="small"
        cardBordered
        options={false}
        search={{ labelWidth: "auto" }}
        toolBarRender={false}
        loading={queryLoading}
        params={parentSearch}
        onSubmit={(params) => {
          setParentSearch(params as QueryParams);
          setParentPage(1);
          setExpandedRowKeys([]);
          setChildStates({});
        }}
        onReset={() => {
          setParentSearch({});
          setParentPage(1);
          setExpandedRowKeys([]);
          setChildStates({});
        }}
        pagination={{
          current: parentPage,
          pageSize: parentPageSize,
          showSizeChanger: true,
          onChange: (page, pageSize) => {
            setParentPage(page);
            setParentPageSize(pageSize || parentPageSize);
          },
        }}
        request={async (params) => {
          setQueryLoading(true);
          try {
            const query = new URLSearchParams();
            query.set("page", String(params.current || 1));
            query.set("pageSize", String(params.pageSize || parentPageSize));
            if (params.fid) query.set("fid", params.fid);
            if (params.status) query.set("status", String(params.status));
            if (params.sourceKeyword) query.set("sourceKeyword", params.sourceKeyword);
            if (params.translatedKeyword) query.set("translatedKeyword", params.translatedKeyword);
            if (params.updatedFrom) query.set("updatedFrom", params.updatedFrom);
            if (params.updatedTo) query.set("updatedTo", params.updatedTo);
            if (params.claimer) query.set("claimer", params.claimer);
            if (params.claimed) query.set("claimed", params.claimed);

            const response = await apiFetch<TextListResponse>(`/texts/parents?${query.toString()}`);
            setPageFids(Array.from(new Set(response.items.map((item) => item.fid))));
            return {
              data: response.items,
              success: true,
              total: response.total,
            };
          } catch (error) {
            message.error(getErrorMessage(error, "加载列表失败"));
            setPageFids([]);
            return {
              data: [],
              success: false,
              total: 0,
            };
          } finally {
            setQueryLoading(false);
          }
        }}
        expandable={{
          expandedRowKeys,
          onExpand: (expanded, record) => {
            const fid = record.fid;
            setExpandedRowKeys(expanded ? [fid] : []);
            if (expanded) {
              fetchChildren(fid);
            }
          },
          expandedRowRender: (record) => renderChildTable(record),
        }}
        columns={columns}
      />
    </>
  );
}
