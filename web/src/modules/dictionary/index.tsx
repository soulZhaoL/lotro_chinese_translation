import type { ActionType, ProColumns } from "@ant-design/pro-components";
import { ProTable } from "@ant-design/pro-components";
import type { ProFormInstance } from "@ant-design/pro-form";
import { Button, Form, Input, Modal, Popover, Select, Space, Typography, message } from "antd";
import type { ChangeEvent } from "react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { apiFetch, getErrorMessage } from "../../api";
import { getAppConfig } from "../../config";
import { formatDateTime } from "../../utils/datetime";
import { CATEGORY_LABELS, CATEGORY_OPTIONS } from "./constants";
import {
  SearchActionBar,
  type DownloadProgressSnapshot,
  downloadFilteredFile,
  downloadTemplateFile,
  formatDownloadProgressText,
  normalizeQueryParams,
  resolveSearchParams,
} from "./io";
import type {
  DictionaryFilters,
  DictionaryItem,
  DictionaryMutationPayload,
  DictionaryResponse,
} from "./types";

const TABLE_SCROLL_X = 1320;
const DISPLAY_LIMIT = 80;
const TOOLTIP_LIMIT = 5000;
const POPOVER_MAX_WIDTH = "min(620px, calc(100vw - 48px))";

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
      placement="top"
      autoAdjustOverflow
      getPopupContainer={() => document.body}
      content={<div style={{ maxHeight: 320, overflowY: "auto", maxWidth: POPOVER_MAX_WIDTH, whiteSpace: "pre-wrap" }}>{tooltipText}</div>}
    >
      <Typography.Text style={{ whiteSpace: "pre-wrap" }}>{displayText}</Typography.Text>
    </Popover>
  );
}

export default function Dictionary() {
  const actionRef = useRef<ActionType>();
  const formRef = useRef<ProFormInstance<DictionaryFilters> | undefined>(undefined);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [modalForm] = Form.useForm<DictionaryMutationPayload>();
  const [queryLoading, setQueryLoading] = useState(false);
  const [currentSearch, setCurrentSearch] = useState<DictionaryFilters>({});
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingItem, setEditingItem] = useState<DictionaryItem | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [downloadingFiltered, setDownloadingFiltered] = useState(false);
  const [filteredDownloadStageText, setFilteredDownloadStageText] = useState("导出");

  const syncModalForm = useCallback(() => {
    if (editingItem) {
      modalForm.setFieldsValue({
        termKey: editingItem.termKey,
        termValue: editingItem.termValue,
        category: editingItem.category || undefined,
        remark: editingItem.remark || undefined,
      });
      return;
    }
    modalForm.resetFields();
  }, [editingItem, modalForm]);

  useEffect(() => {
    if (!modalOpen) {
      return;
    }
    syncModalForm();
  }, [modalOpen, syncModalForm]);

  const openCreateModal = useCallback(() => {
    setEditingItem(null);
    setModalOpen(true);
  }, []);

  const openEditModal = useCallback(
    (record: DictionaryItem) => {
      setEditingItem(record);
      setModalOpen(true);
    },
    []
  );

  const closeModal = useCallback(() => {
    setModalOpen(false);
    setEditingItem(null);
    modalForm.resetFields();
  }, [modalForm]);

  const handleSubmit = useCallback(async () => {
    if (submitting) {
      return;
    }
    try {
      setSubmitting(true);
      const values = await modalForm.validateFields();
      if (editingItem) {
        await apiFetch(`/dictionary/${editingItem.id}`, {
          method: "PUT",
          body: JSON.stringify({
            termValue: values.termValue,
            category: values.category,
            remark: values.remark,
          }),
        });
        message.success("修改成功");
      } else {
        await apiFetch("/dictionary", {
          method: "POST",
          body: JSON.stringify(values),
        });
        message.success("新增成功");
      }
      closeModal();
      actionRef.current?.reload();
    } catch (error) {
      message.error(getErrorMessage(error, editingItem ? "修改失败" : "新增失败"));
    } finally {
      setSubmitting(false);
    }
  }, [closeModal, editingItem, modalForm, submitting]);

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
    if (downloadingFiltered) {
      return;
    }
    const search = resolveSearchParams(formRef, currentSearch);
    try {
      setDownloadingFiltered(true);
      setFilteredDownloadStageText("导出生成中...");
      const result = await downloadFilteredFile(search, {
        onProgress: (progress: DownloadProgressSnapshot) => {
          setFilteredDownloadStageText(formatDownloadProgressText("导出", progress));
        },
      });
      if (result === "mock_unsupported") {
        message.warning("Mock 模式不支持导出");
        return;
      }
      message.success("导出成功");
    } catch (error) {
      message.error(getErrorMessage(error, "导出失败"));
    } finally {
      setDownloadingFiltered(false);
      setFilteredDownloadStageText("导出");
    }
  }, [currentSearch, downloadingFiltered]);

  const handleUploadFile = useCallback(async (event: ChangeEvent<HTMLInputElement>) => {
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
        message.warning("Mock 模式不支持词典导入");
        return;
      }

      const query = new URLSearchParams();
      query.set("fileName", selectedFile.name);
      const result = await apiFetch<{ createdCount?: number; updatedCount?: number }>(
        `/dictionary/upload?${query.toString()}`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
          },
          body: selectedFile,
        }
      );

      message.success(`导入成功，新增 ${result.createdCount || 0} 条，覆盖 ${result.updatedCount || 0} 条`);
      actionRef.current?.reload();
    } catch (error) {
      message.error(getErrorMessage(error, "导入失败"));
    } finally {
      setUploading(false);
    }
  }, []);

  const columns = useMemo<ProColumns<DictionaryItem>[]>(
    () => [
      {
        title: "词条Key",
        dataIndex: "termKey",
        width: 220,
        ellipsis: true,
        formItemProps: {
          rules: [{ max: 128, message: "最多 128 个字符" }],
        },
      },
      {
        title: "词条Value",
        dataIndex: "termValue",
        width: 220,
        render: (_, record) => renderLongText(record.termValue),
        formItemProps: {
          rules: [{ max: 128, message: "最多 128 个字符" }],
        },
      },
      {
        title: "分类",
        dataIndex: "category",
        width: 140,
        valueType: "select",
        valueEnum: Object.fromEntries(
          CATEGORY_OPTIONS.map((option) => [option.value, { text: option.label }])
        ),
        render: (_, record) => (record.category ? CATEGORY_LABELS[record.category] || record.category : "-"),
      },
      {
        title: "备注",
        dataIndex: "remark",
        width: 260,
        hideInSearch: true,
        render: (_, record) => renderLongText(record.remark),
      },
      {
        title: "修改人",
        dataIndex: "lastModifiedByName",
        width: 140,
        hideInSearch: true,
        render: (_, record) => record.lastModifiedByName || "-",
      },
      {
        title: "更新时间",
        dataIndex: "uptTime",
        width: 180,
        hideInSearch: true,
        render: (_, record) => formatDateTime(record.uptTime),
      },
      {
        title: "操作",
        key: "actions",
        width: 100,
        hideInSearch: true,
        fixed: "right",
        render: (_, record) => (
          <Space size={8}>
            <Button type="link" size="small" style={{ paddingInline: 0 }} onClick={() => openEditModal(record)}>
              修改
            </Button>
          </Space>
        ),
      },
    ],
    [openEditModal]
  );

  return (
    <>
      <ProTable<DictionaryItem, DictionaryFilters>
        rowKey="id"
        headerTitle="词典管理"
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
              downloadingFiltered={downloadingFiltered}
              filteredDownloadText={filteredDownloadStageText}
              uploading={uploading}
              creating={submitting && !editingItem}
              onDownloadFiltered={() => void handleDownloadFiltered()}
              onDownloadTemplate={() => void handleDownloadTemplate()}
              onUpload={() => fileInputRef.current?.click()}
              onCreate={openCreateModal}
            />,
          ],
        }}
        loading={queryLoading}
        params={currentSearch}
        onSubmit={(params) => {
          setCurrentSearch(normalizeQueryParams(params));
          setPage(1);
        }}
        onReset={() => {
          setCurrentSearch({});
          setPage(1);
        }}
        pagination={{
          current: page,
          pageSize,
          showTotal: (total) => `词典共 ${total} 条`,
          showSizeChanger: true,
          onChange: (nextPage, nextPageSize) => {
            setPage(nextPage);
            setPageSize(nextPageSize || pageSize);
          },
        }}
        scroll={{ x: TABLE_SCROLL_X }}
        request={async (params) => {
          setQueryLoading(true);
          try {
            const normalized = normalizeQueryParams(params);
            const query = new URLSearchParams();
            query.set("page", String(params.current || 1));
            query.set("pageSize", String(params.pageSize || pageSize));
            if (normalized.termKey) {
              query.set("termKey", normalized.termKey);
            }
            if (normalized.termValue) {
              query.set("termValue", normalized.termValue);
            }
            if (normalized.category) {
              query.set("category", normalized.category);
            }

            const data = await apiFetch<DictionaryResponse>(`/dictionary?${query.toString()}`);
            return {
              data: data.items,
              success: true,
              total: data.total,
            };
          } catch (error) {
            message.error(getErrorMessage(error, "加载词典失败"));
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

      <input
        ref={fileInputRef}
        type="file"
        accept=".xlsx"
        style={{ display: "none" }}
        onChange={(event) => void handleUploadFile(event)}
      />

      <Modal
        title={editingItem ? "修改词条" : "新增词条"}
        open={modalOpen}
        onCancel={closeModal}
        onOk={() => void handleSubmit()}
        afterOpenChange={(open) => {
          if (open) {
            syncModalForm();
          }
        }}
        okText="保存"
        cancelText="取消"
        confirmLoading={submitting}
        forceRender
        destroyOnClose
      >
        <Form
          form={modalForm}
          layout="vertical"
          preserve={false}
          initialValues={{
            termKey: "",
            termValue: "",
            category: undefined,
            remark: "",
          }}
        >
          <Form.Item
            name="termKey"
            label="词条Key"
            rules={[{ required: true, message: "请输入词条Key" }]}
          >
            <Input disabled={Boolean(editingItem)} maxLength={128} />
          </Form.Item>
          <Form.Item
            name="termValue"
            label="词条Value"
            rules={[{ required: true, message: "请输入词条Value" }]}
          >
            <Input maxLength={128} />
          </Form.Item>
          <Form.Item name="category" label="分类">
            <Select allowClear options={CATEGORY_OPTIONS} placeholder="请选择分类" />
          </Form.Item>
          <Form.Item name="remark" label="备注">
            <Input.TextArea rows={4} maxLength={255} placeholder="可填写补充说明" />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}
