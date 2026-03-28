import type { ActionType } from "@ant-design/pro-components";
import { ProTable } from "@ant-design/pro-components";
import { message } from "antd";
import type { ProFormInstance } from "@ant-design/pro-form";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { apiFetch, getErrorMessage } from "../../../api";
import { getAppConfig } from "../../../config";
import { parseStoredListState, saveListState } from "../storage";
import type { ActiveConfirmState, ListStateSnapshot, QueryParams, TextItem, TextListResponse } from "../types";
import { createParentColumns } from "./table";
import {
  SearchActionBar,
  type DownloadProgressSnapshot,
  downloadFilteredFile,
  downloadPackageFile,
  downloadTemplateFile,
  hasAnyFilter,
  normalizeQueryParams,
  resolveSearchParams,
} from "./filter";

const TABLE_SCROLL_X = 1900;

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
  const [restoreReady, setRestoreReady] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [downloadingPackage, setDownloadingPackage] = useState(false);
  const [packageDownloadStageText, setPackageDownloadStageText] = useState("下载汉化包");
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const buildListState = useCallback((): ListStateSnapshot => {
    return {
      search: parentSearch,
      page: parentPage,
      pageSize: parentPageSize,
    };
  }, [parentPage, parentPageSize, parentSearch]);

  const persistListState = useCallback((snapshot: ListStateSnapshot) => {
    saveListState(snapshot);
  }, []);

  useEffect(() => {
    if (!restoreReady) {
      return;
    }
    persistListState(buildListState());
  }, [buildListState, persistListState, restoreReady]);

  useEffect(() => {
    const state = location.state as { listState?: ListStateSnapshot; refresh?: boolean } | null;
    const stored = state?.listState || parseStoredListState();

    if (stored) {
      setParentSearch(stored.search || {});
      setParentPage(stored.page || 1);
      setParentPageSize(stored.pageSize || 20);

      if (formRef.current) {
        formRef.current.setFieldsValue(stored.search || {});
      }
    }

    if (state?.listState || state?.refresh) {
      navigate(location.pathname, { replace: true, state: {} });
    }

    if (state?.refresh) {
      actionRef.current?.reload();
    }
    setRestoreReady(true);
  }, [location.pathname, location.state, navigate]);

  const navigateWithState = useCallback(
    (path: string) => {
      const snapshot = buildListState();
      persistListState(snapshot);
      navigate(path, { state: { listState: snapshot } });
    },
    [buildListState, navigate, persistListState]
  );

  const handleDownloadTemplate = useCallback(async () => {
    try {
      const result = await downloadTemplateFile();
      if (result === "mock_unsupported") {
        message.warning("Mock 模式不支持模板下载");
        return;
      }
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
      const result = await downloadFilteredFile(currentSearch);
      if (result === "mock_unsupported") {
        message.warning("Mock 模式不支持导出筛选结果");
        return;
      }
      message.success("导出成功");
    } catch (error) {
      message.error(getErrorMessage(error, "导出失败"));
    }
  }, [parentSearch]);

  const handleDownloadPackage = useCallback(async () => {
    if (downloadingPackage) {
      return;
    }
    setDownloadingPackage(true);
    setPackageDownloadStageText("汉化包生成中...");
    const currentSearch = resolveSearchParams(formRef, parentSearch);
    try {
      const result = await downloadPackageFile(currentSearch, {
        onProgress: (progress: DownloadProgressSnapshot) => {
          if (progress.stage === "preparing") {
            setPackageDownloadStageText("汉化包生成中...");
            return;
          }
          if (progress.percent !== null) {
            setPackageDownloadStageText(`汉化包传输中 ${progress.percent}%`);
            return;
          }
          const receivedMb = (progress.loadedBytes / (1024 * 1024)).toFixed(1);
          setPackageDownloadStageText(`汉化包传输中 ${receivedMb}MB`);
        },
      });
      if (result === "mock_unsupported") {
        message.warning("Mock 模式不支持汉化包下载");
        return;
      }
      message.success("汉化包下载成功");
    } catch (error) {
      message.error(getErrorMessage(error, "汉化包下载失败"));
    } finally {
      setDownloadingPackage(false);
      setPackageDownloadStageText("下载汉化包");
    }
  }, [downloadingPackage, parentSearch]);

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

      const query = new URLSearchParams();
      query.set("fileName", selectedFile.name);
      query.set("reason", "模板批量上传");

      const result = await apiFetch<{ updatedCount?: number }>(`/texts/upload?${query.toString()}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        },
        body: selectedFile,
      });

      message.success(`上传成功，更新 ${result.updatedCount || 0} 条`);
      actionRef.current?.reload();
    } catch (error) {
      message.error(getErrorMessage(error, "上传失败"));
    } finally {
      setUploading(false);
    }
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
        sourceMatchMode: parentSearch.sourceMatchMode,
        translatedKeyword: parentSearch.translatedKeyword,
        translatedMatchMode: parentSearch.translatedMatchMode,
        onParentChanged: () => actionRef.current?.reload(),
      }),
    [
      activeConfirm,
      claimingId,
      navigateWithState,
      parentSearch.sourceKeyword,
      parentSearch.sourceMatchMode,
      parentSearch.translatedKeyword,
      parentSearch.translatedMatchMode,
      releasingId,
    ]
  );

  return (
    <>
      <ProTable<TextItem, QueryParams>
        rowKey="id"
        headerTitle="文本列表"
        actionRef={actionRef}
        formRef={formRef}
        size="small"
        cardBordered
        options={false}
        toolBarRender={false}
        search={{
          labelWidth: "auto",
          span: 6,
          optionRender: (_, __, dom) => [
            <SearchActionBar
              key="search-actions"
              dom={dom}
              uploading={uploading}
              downloadingPackage={downloadingPackage}
              packageDownloadText={packageDownloadStageText}
              onDownloadFiltered={() => void handleDownloadFiltered()}
              onDownloadPackage={() => void handleDownloadPackage()}
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
        }}
        onReset={() => {
          setParentSearch({});
          setParentPage(1);
        }}
        pagination={{
          current: parentPage,
          pageSize: parentPageSize,
          showTotal: (total) => `文本共 ${total} 条`,
          showSizeChanger: true,
          onChange: (page, pageSize) => {
            setParentPage(page);
            setParentPageSize(pageSize || parentPageSize);
          },
        }}
        scroll={{ x: TABLE_SCROLL_X }}
        request={async (params) => {
          setQueryLoading(true);
          try {
            const normalized = normalizeQueryParams(params as QueryParams & { uptTime?: [string, string] });
            const query = new URLSearchParams();
            query.set("page", String(params.current || 1));
            query.set("pageSize", String(params.pageSize || parentPageSize));
            if (normalized.fid) query.set("fid", normalized.fid);
            if (normalized.textId) query.set("textId", normalized.textId);
            if (normalized.status !== undefined) query.set("status", String(normalized.status));
            if (normalized.sourceKeyword) query.set("sourceKeyword", normalized.sourceKeyword);
            if (normalized.sourceMatchMode) query.set("sourceMatchMode", normalized.sourceMatchMode);
            if (normalized.translatedKeyword) query.set("translatedKeyword", normalized.translatedKeyword);
            if (normalized.translatedMatchMode) query.set("translatedMatchMode", normalized.translatedMatchMode);
            if (normalized.updatedFrom) query.set("updatedFrom", normalized.updatedFrom);
            if (normalized.updatedTo) query.set("updatedTo", normalized.updatedTo);
            if (normalized.claimer) query.set("claimer", normalized.claimer);
            if (normalized.claimed !== undefined) query.set("claimed", String(normalized.claimed));

            const data = await apiFetch<TextListResponse>(`/texts?${query.toString()}`);

            return {
              data: data.items,
              success: true,
              total: data.total,
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
