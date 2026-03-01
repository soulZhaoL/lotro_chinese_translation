import type { ActionType } from "@ant-design/pro-components";
import { ProTable } from "@ant-design/pro-components";
import { Alert, Button, Space, message } from "antd";
import type { ProFormInstance } from "@ant-design/pro-form";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { getErrorMessage, getToken } from "../../../../api";
import { getAppConfig } from "../../../../config";
import {
  ChildTablePanel,
  createChildColumns,
  createEmptyChildState,
  createParentColumns,
  type ActiveConfirmState,
  type ChildQuery,
  type ChildState,
  type ListStateSnapshot,
  type QueryParams,
  type TextItem,
  type TextListResponse,
} from "./table";
import {
  SearchActionBar,
  downloadFilteredFile,
  downloadTemplateFile,
  hasAnyFilter,
  normalizeQueryParams,
  resolveSearchParams,
} from "./filter";

const STORAGE_KEY = "texts_list_state";

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
  const [activeConfirm, setActiveConfirm] = useState<ActiveConfirmState>(null);
  const [parentSearch, setParentSearch] = useState<QueryParams>({});
  const [parentPage, setParentPage] = useState(1);
  const [parentPageSize, setParentPageSize] = useState(20);
  const [expandedRowKeys, setExpandedRowKeys] = useState<Array<string | number>>([]);
  const [childStates, setChildStates] = useState<Record<string, ChildState>>({});
  const [pageFids, setPageFids] = useState<string[]>([]);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
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

  const persistListState = useCallback((snapshot: ListStateSnapshot) => {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(snapshot));
  }, []);

  useEffect(() => {
    persistListState(buildListState());
  }, [buildListState, persistListState]);

  const fetchChildren = useCallback(async (fid: string, overrides?: Partial<ChildQuery>) => {
    const current = childStatesRef.current[fid] || createEmptyChildState(1, 10);
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
      if (parentSearchRef.current.sourceKeyword) {
        query.set("sourceKeyword", parentSearchRef.current.sourceKeyword);
      }
      if (parentSearchRef.current.translatedKeyword) {
        query.set("translatedKeyword", parentSearchRef.current.translatedKeyword);
      }

      const config = getAppConfig();
      const apiBase = config.useMock ? "/api" : config.apiBaseUrl;
      if (!apiBase) {
        throw new Error("缺少 apiBaseUrl");
      }
      const token = getToken();
      const headers = new Headers();
      if (token) {
        headers.set("Authorization", `Bearer ${token}`);
      }

      const response = await fetch(`${apiBase}/texts/children?${query.toString()}`, {
        method: "GET",
        headers,
      });
      const payload = (await response.json()) as {
        code?: string;
        message?: string;
        data?: TextListResponse;
      };
      if (!response.ok || payload.code !== "0000" || !payload.data) {
        throw new Error(payload.message || "加载子列表失败");
      }
      const data = payload.data;

      setChildStates((prev) => ({
        ...prev,
        [fid]: {
          ...(prev[fid] || current),
          ...nextQuery,
          items: data.items,
          total: data.total,
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
        nextChildStates[fid] = createEmptyChildState(query.page, query.pageSize);
        nextChildStates[fid].textId = query.textId;
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

  const handleDownloadTemplate = useCallback(async () => {
    try {
      await downloadTemplateFile();
      message.success("模板下载成功");
    } catch (error) {
      message.error(getErrorMessage(error, "模板下载失败"));
    }
  }, []);

  const handleDownloadFiltered = useCallback(async () => {
    const currentSearch = resolveSearchParams(formRef, parentSearch);
    if (!hasAnyFilter(currentSearch)) {
      message.warning("请先设置筛选条件后再导出");
      return;
    }
    try {
      await downloadFilteredFile(currentSearch);
      message.success("导出成功");
    } catch (error) {
      message.error(getErrorMessage(error, "导出失败"));
    }
  }, [parentSearch]);

  const handleUploadFile = useCallback(async (event: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = event.target.files?.[0];
    event.target.value = "";
    if (!selectedFile) {
      return;
    }
    if (!selectedFile.name.toLowerCase().endsWith(".xlsx")) {
      message.error("仅支持上传 .xlsx 文件");
      return;
    }

    try {
      setUploading(true);
      const config = getAppConfig();
      if (config.useMock) {
        message.warning("Mock 模式不支持模板上传");
        return;
      }
      const apiBase = config.apiBaseUrl;
      if (!apiBase) {
        throw new Error("缺少 apiBaseUrl");
      }
      const token = getToken();
      if (!token) {
        throw new Error("未登录或登录已失效");
      }

      const query = new URLSearchParams();
      query.set("fileName", selectedFile.name);
      query.set("reason", "模板批量上传");

      const response = await fetch(`${apiBase}/texts/upload?${query.toString()}`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        },
        body: selectedFile,
      });
      const payload = (await response.json()) as {
        success?: boolean;
        code?: string;
        message?: string;
        data?: { updatedCount?: number };
      };

      if (!response.ok || !payload.success || payload.code !== "0000") {
        throw new Error(payload.message || "上传失败");
      }

      message.success(`上传成功，更新 ${payload.data?.updatedCount || 0} 条`);
      setExpandedRowKeys([]);
      setChildStates({});
      actionRef.current?.reload();
    } catch (error) {
      message.error(getErrorMessage(error, "上传失败"));
    } finally {
      setUploading(false);
    }
  }, []);

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

  const parentColumns = useMemo(
    () =>
      createParentColumns({
        claimingId,
        releasingId,
        activeConfirm,
        setClaimingId,
        setReleasingId,
        setActiveConfirm,
        navigateWithState,
        sourceKeyword: parentSearch.sourceKeyword,
        translatedKeyword: parentSearch.translatedKeyword,
        onParentChanged: () => actionRef.current?.reload(),
      }),
    [activeConfirm, claimingId, navigateWithState, parentSearch.sourceKeyword, parentSearch.translatedKeyword, releasingId]
  );

  const childColumns = useMemo(
    () =>
      createChildColumns({
        claimingId,
        releasingId,
        activeConfirm,
        setClaimingId,
        setReleasingId,
        setActiveConfirm,
        navigateWithState,
        sourceKeyword: parentSearch.sourceKeyword,
        translatedKeyword: parentSearch.translatedKeyword,
        onChildChanged: (fid) => fetchChildren(fid),
      }),
    [
      activeConfirm,
      claimingId,
      fetchChildren,
      navigateWithState,
      parentSearch.sourceKeyword,
      parentSearch.translatedKeyword,
      releasingId,
    ]
  );

  const keywordActive = Boolean(parentSearch.sourceKeyword || parentSearch.translatedKeyword);

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
        toolBarRender={false}
        search={{
          labelWidth: "auto",
          optionRender: (_, __, dom) => [
            <SearchActionBar
              key="search-actions"
              dom={dom}
              uploading={uploading}
              onDownloadFiltered={() => void handleDownloadFiltered()}
              onDownloadTemplate={() => void handleDownloadTemplate()}
              onUpload={() => fileInputRef.current?.click()}
            />,
          ],
        }}
        loading={queryLoading}
        params={parentSearch}
        onSubmit={(params) => {
          const normalized = normalizeQueryParams(params as QueryParams & { uptTime?: [string, string] });
          setParentSearch(normalized);
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
            const normalized = normalizeQueryParams(params as QueryParams & { uptTime?: [string, string] });
            const query = new URLSearchParams();
            query.set("page", String(params.current || 1));
            query.set("pageSize", String(params.pageSize || parentPageSize));
            if (normalized.fid) query.set("fid", normalized.fid);
            if (normalized.status !== undefined) query.set("status", String(normalized.status));
            if (normalized.sourceKeyword) query.set("sourceKeyword", normalized.sourceKeyword);
            if (normalized.translatedKeyword) query.set("translatedKeyword", normalized.translatedKeyword);
            if (normalized.updatedFrom) query.set("updatedFrom", normalized.updatedFrom);
            if (normalized.updatedTo) query.set("updatedTo", normalized.updatedTo);
            if (normalized.claimer) query.set("claimer", normalized.claimer);
            if (normalized.claimed !== undefined) query.set("claimed", String(normalized.claimed));

            const config = getAppConfig();
            const apiBase = config.useMock ? "/api" : config.apiBaseUrl;
            if (!apiBase) {
              throw new Error("缺少 apiBaseUrl");
            }
            const token = getToken();
            const headers = new Headers();
            if (token) {
              headers.set("Authorization", `Bearer ${token}`);
            }

            const response = await fetch(`${apiBase}/texts/parents?${query.toString()}`, {
              method: "GET",
              headers,
            });
            const payload = (await response.json()) as {
              code?: string;
              message?: string;
              data?: TextListResponse;
            };
            if (!response.ok || payload.code !== "0000" || !payload.data) {
              throw new Error(payload.message || "加载列表失败");
            }
            const data = payload.data;

            setPageFids(Array.from(new Set(data.items.map((item) => item.fid))));
            return {
              data: data.items,
              success: true,
              total: data.total,
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
          expandedRowRender: (record) => {
            const state = childStates[record.fid] || createEmptyChildState(1, 10);
            return (
              <ChildTablePanel
                parent={record}
                state={state}
                childColumns={childColumns}
                fetchChildren={fetchChildren}
                setChildStates={setChildStates}
                handleChildSearch={handleChildSearch}
              />
            );
          },
        }}
        columns={parentColumns}
      />

      <input
        ref={fileInputRef}
        type="file"
        accept=".xlsx"
        style={{ display: "none" }}
        onChange={(event) => void handleUploadFile(event)}
      />
    </>
  );
}
