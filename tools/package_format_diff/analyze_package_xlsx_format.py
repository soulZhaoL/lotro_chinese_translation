"""比较 online 与 sys 汉化包 xlsx 的格式差异。

说明：
- 仅使用 Python 标准库，避免依赖 openpyxl / PyYAML。
- 配置必须通过 JSON 文件显式提供；缺少配置直接报错。
- 重点分析：
  1. xlsx 结构差异（sheet / 表头 / 分片列）
  2. 同一 fid 聚合后的 translation 是否完全一致
  3. 同一 fid 的分片数量是否一致
  4. 协议分段（||| / textId::::::[...] / textId:::[...]）是否存在格式差异
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Tuple
from xml.etree import ElementTree as ET
from zipfile import ZipFile


MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
NS = {"main": MAIN_NS}
CELL_REF_RE = re.compile(r"([A-Z]+)(\d+)")


class ConfigError(Exception):
    pass


class WorkbookFormatError(Exception):
    pass


@dataclass(frozen=True)
class FileConfig:
    label: str
    path: Path
    sheet: str
    fid_column: str
    translation_column: str
    split_part_column: Optional[str]
    order_mode: str


@dataclass(frozen=True)
class OutputConfig:
    summary_path: Path
    report_path: Path
    mismatch_example_limit: int


@dataclass(frozen=True)
class CompareConfig:
    split_delimiter: str
    text_id_pattern: str


@dataclass(frozen=True)
class GroupRecord:
    fid: str
    chunk_count: int
    merged_translation: str
    row_numbers: Tuple[int, ...]
    split_parts: Tuple[Optional[int], ...]
    chunk_lengths: Tuple[int, ...]


@dataclass(frozen=True)
class FileStats:
    row_count: int
    fid_count: int
    multi_row_fid_count: int
    max_chunk_length: int
    max_chunk_fid: str
    max_chunk_row: int
    max_chunks_per_fid: int
    max_chunks_fid: str
    multi_row_examples: Tuple[Tuple[str, int], ...]


@dataclass(frozen=True)
class SegmentInfo:
    raw: str
    text_id: Optional[str]
    payload: Optional[str]
    is_valid: bool


def _require_key(data: dict, key: str, path: str):
    if key not in data:
        raise ConfigError(f"缺少配置项: {path}{key}")
    return data[key]


def _require_type(value, expected_type, path: str):
    if not isinstance(value, expected_type):
        raise ConfigError(f"配置项类型错误: {path}，期望 {expected_type.__name__}")
    return value


def _find_project_root(start: Path) -> Path:
    for candidate in [start, *start.parents]:
        if (candidate / ".git").exists():
            return candidate
    raise ConfigError("无法定位项目根目录")


def _resolve_path(base_dir: Path, text: str) -> Path:
    path = Path(text)
    if path.is_absolute():
        return path
    return (base_dir / path).resolve()


def _load_config(path: Path) -> Tuple[FileConfig, FileConfig, CompareConfig, OutputConfig]:
    if not path.exists():
        raise FileNotFoundError(f"配置文件不存在: {path}")
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ConfigError("配置文件根节点必须为 JSON object")

    base_dir_text = _require_type(_require_key(data, "base_dir", ""), str, "base_dir")
    base_dir = _find_project_root(path.parent) if base_dir_text == "__PROJECT_ROOT__" else Path(base_dir_text).expanduser().resolve()

    files_cfg = _require_type(_require_key(data, "files", ""), dict, "files")
    compare_cfg = _require_type(_require_key(data, "comparison", ""), dict, "comparison")
    output_cfg = _require_type(_require_key(data, "output", ""), dict, "output")

    online_cfg = _build_file_config(
        "online",
        _require_type(_require_key(files_cfg, "online", "files."), dict, "files.online"),
        base_dir,
        "files.online.",
    )
    sys_cfg = _build_file_config(
        "sys",
        _require_type(_require_key(files_cfg, "sys", "files."), dict, "files.sys"),
        base_dir,
        "files.sys.",
    )

    split_delimiter = _require_type(
        _require_key(compare_cfg, "splitDelimiter", "comparison."),
        str,
        "comparison.splitDelimiter",
    )
    if split_delimiter == "":
        raise ConfigError("comparison.splitDelimiter 不能为空")
    text_id_pattern = _require_type(
        _require_key(compare_cfg, "textIdPattern", "comparison."),
        str,
        "comparison.textIdPattern",
    )
    try:
        re.compile(text_id_pattern)
    except re.error as exc:
        raise ConfigError(f"comparison.textIdPattern 非法: {exc}") from exc

    summary_path = _resolve_path(
        base_dir,
        _require_type(_require_key(output_cfg, "summaryPath", "output."), str, "output.summaryPath"),
    )
    report_path = _resolve_path(
        base_dir,
        _require_type(_require_key(output_cfg, "reportPath", "output."), str, "output.reportPath"),
    )
    mismatch_example_limit = _require_type(
        _require_key(output_cfg, "mismatchExampleLimit", "output."),
        int,
        "output.mismatchExampleLimit",
    )
    if mismatch_example_limit <= 0:
        raise ConfigError("output.mismatchExampleLimit 必须大于 0")

    return (
        online_cfg,
        sys_cfg,
        CompareConfig(split_delimiter=split_delimiter, text_id_pattern=text_id_pattern),
        OutputConfig(
            summary_path=summary_path,
            report_path=report_path,
            mismatch_example_limit=mismatch_example_limit,
        ),
    )


def _build_file_config(label: str, data: dict, base_dir: Path, path_prefix: str) -> FileConfig:
    file_path = _resolve_path(base_dir, _require_type(_require_key(data, "path", path_prefix), str, f"{path_prefix}path"))
    sheet = _require_type(_require_key(data, "sheet", path_prefix), str, f"{path_prefix}sheet")
    fid_column = _require_type(_require_key(data, "fidColumn", path_prefix), str, f"{path_prefix}fidColumn")
    translation_column = _require_type(
        _require_key(data, "translationColumn", path_prefix),
        str,
        f"{path_prefix}translationColumn",
    )
    order_mode = _require_type(_require_key(data, "orderMode", path_prefix), str, f"{path_prefix}orderMode")
    if order_mode not in ("document", "split_part"):
        raise ConfigError(f"{path_prefix}orderMode 仅支持 document/split_part")
    split_part_column = data.get("splitPartColumn")
    if order_mode == "split_part":
        if not isinstance(split_part_column, str) or split_part_column == "":
            raise ConfigError(f"{path_prefix}splitPartColumn 不能为空")
    elif split_part_column is not None and not isinstance(split_part_column, str):
        raise ConfigError(f"{path_prefix}splitPartColumn 必须为字符串或 null")

    return FileConfig(
        label=label,
        path=file_path,
        sheet=sheet,
        fid_column=fid_column,
        translation_column=translation_column,
        split_part_column=split_part_column,
        order_mode=order_mode,
    )


def _normalize_text(value: Optional[str]) -> str:
    if value is None:
        return ""
    return value


def _normalize_fid(value: Optional[str], row_number: int, label: str) -> str:
    text = _normalize_text(value).strip()
    if text == "":
        raise WorkbookFormatError(f"{label} 第 {row_number} 行 fid 为空")
    return text


def _parse_split_part(value: Optional[str], row_number: int, label: str) -> int:
    text = _normalize_text(value).strip()
    if text == "":
        raise WorkbookFormatError(f"{label} 第 {row_number} 行 split_part 为空")
    if not re.fullmatch(r"-?\d+", text):
        raise WorkbookFormatError(f"{label} 第 {row_number} 行 split_part 非整数: {text}")
    number = int(text)
    if number < 0:
        raise WorkbookFormatError(f"{label} 第 {row_number} 行 split_part 不能小于 0")
    return number


def _excel_col_to_index(col: str) -> int:
    value = 0
    for ch in col:
        value = value * 26 + (ord(ch) - 64)
    return value


def _load_shared_strings(zf: ZipFile) -> List[str]:
    if "xl/sharedStrings.xml" not in zf.namelist():
        return []
    root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
    values: List[str] = []
    for si in root.findall("main:si", NS):
        values.append("".join(item.text or "" for item in si.iterfind(".//main:t", NS)))
    return values


def _resolve_sheet_target(zf: ZipFile, sheet_name: str) -> str:
    workbook = ET.fromstring(zf.read("xl/workbook.xml"))
    rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
    rel_map = {node.attrib["Id"]: node.attrib["Target"].lstrip("/") for node in rels.findall(f"{{{PKG_REL_NS}}}Relationship")}
    sheets = workbook.find("main:sheets", NS)
    if sheets is None:
        raise WorkbookFormatError("workbook 缺少 sheets 节点")
    for sheet in sheets:
        if sheet.attrib.get("name") != sheet_name:
            continue
        rel_id = sheet.attrib.get(f"{{{REL_NS}}}id")
        if rel_id is None:
            raise WorkbookFormatError(f"sheet {sheet_name} 缺少关系 id")
        target = rel_map.get(rel_id)
        if target is None:
            raise WorkbookFormatError(f"sheet {sheet_name} 无法解析目标 xml")
        if target.startswith("xl/"):
            return target
        return "xl/" + target.removeprefix("xl/")
    raise WorkbookFormatError(f"未找到 sheet: {sheet_name}")


def _read_cell_value(cell: ET.Element, shared_strings: List[str]) -> str:
    cell_type = cell.attrib.get("t")
    if cell_type == "inlineStr":
        return "".join(item.text or "" for item in cell.iterfind(".//main:t", NS))
    v_node = cell.find("main:v", NS)
    if v_node is None:
        return ""
    raw = v_node.text or ""
    if cell_type == "s":
        return shared_strings[int(raw)]
    return raw


def _iter_sheet_rows(file_path: Path, sheet_name: str) -> Iterator[Tuple[int, Dict[str, str]]]:
    if not file_path.exists():
        raise FileNotFoundError(f"xlsx 文件不存在: {file_path}")
    with ZipFile(file_path) as zf:
        shared_strings = _load_shared_strings(zf)
        sheet_target = _resolve_sheet_target(zf, sheet_name)
        with zf.open(sheet_target) as handle:
            for _, elem in ET.iterparse(handle, events=("end",)):
                if elem.tag != f"{{{MAIN_NS}}}row":
                    continue
                row_number = int(elem.attrib.get("r", "0"))
                values: Dict[str, str] = {}
                for cell in elem.findall("main:c", NS):
                    ref = cell.attrib.get("r")
                    if ref is None:
                        continue
                    matched = CELL_REF_RE.fullmatch(ref)
                    if matched is None:
                        continue
                    values[matched.group(1)] = _read_cell_value(cell, shared_strings)
                yield row_number, values
                elem.clear()


def _read_header(file_cfg: FileConfig) -> Tuple[str, ...]:
    row_iter = _iter_sheet_rows(file_cfg.path, file_cfg.sheet)
    try:
        _, first_row = next(row_iter)
    except StopIteration as exc:
        raise WorkbookFormatError(f"{file_cfg.label} 文件为空: {file_cfg.path}") from exc

    max_col = 0
    for col_name in first_row:
        max_col = max(max_col, _excel_col_to_index(col_name))
    headers: List[str] = []
    for idx in range(1, max_col + 1):
        col_text = _column_name_from_index(idx)
        headers.append(_normalize_text(first_row.get(col_text)))
    return tuple(headers)


def _column_name_from_index(index: int) -> str:
    value = index
    chars: List[str] = []
    while value > 0:
        value, rem = divmod(value - 1, 26)
        chars.append(chr(65 + rem))
    return "".join(reversed(chars))


def _aggregate_groups(file_cfg: FileConfig) -> Tuple[Iterator[GroupRecord], Dict[str, object]]:
    stats_holder: Dict[str, object] = {
        "row_count": 0,
        "fid_count": 0,
        "multi_row_fid_count": 0,
        "max_chunk_length": 0,
        "max_chunk_fid": "",
        "max_chunk_row": 0,
        "max_chunks_per_fid": 0,
        "max_chunks_fid": "",
        "multi_row_examples": [],
    }

    def generator() -> Iterator[GroupRecord]:
        current_fid: Optional[str] = None
        current_rows: List[Tuple[int, Optional[int], str]] = []

        for row_number, row in _iter_sheet_rows(file_cfg.path, file_cfg.sheet):
            if row_number == 1:
                continue
            fid = _normalize_fid(row.get(file_cfg.fid_column), row_number, file_cfg.label)
            translation = _normalize_text(row.get(file_cfg.translation_column))
            split_part_value: Optional[int] = None
            if file_cfg.order_mode == "split_part":
                if file_cfg.split_part_column is None:
                    raise WorkbookFormatError(f"{file_cfg.label} 缺少 splitPart 配置")
                split_part_value = _parse_split_part(row.get(file_cfg.split_part_column), row_number, file_cfg.label)

            stats_holder["row_count"] = int(stats_holder["row_count"]) + 1
            if len(translation) > int(stats_holder["max_chunk_length"]):
                stats_holder["max_chunk_length"] = len(translation)
                stats_holder["max_chunk_fid"] = fid
                stats_holder["max_chunk_row"] = row_number

            if current_fid is None:
                current_fid = fid
            elif fid != current_fid:
                stats_holder["fid_count"] = int(stats_holder["fid_count"]) + 1
                record = _build_group_record(file_cfg, current_fid, current_rows)
                if record.chunk_count > 1:
                    stats_holder["multi_row_fid_count"] = int(stats_holder["multi_row_fid_count"]) + 1
                    multi_row_examples = _require_type(stats_holder["multi_row_examples"], list, "runtime.multi_row_examples")
                    if len(multi_row_examples) < 10:
                        multi_row_examples.append((record.fid, record.chunk_count))
                if record.chunk_count > int(stats_holder["max_chunks_per_fid"]):
                    stats_holder["max_chunks_per_fid"] = record.chunk_count
                    stats_holder["max_chunks_fid"] = record.fid
                yield record
                current_fid = fid
                current_rows = []

            current_rows.append((row_number, split_part_value, translation))

        if current_fid is not None:
            stats_holder["fid_count"] = int(stats_holder["fid_count"]) + 1
            record = _build_group_record(file_cfg, current_fid, current_rows)
            if record.chunk_count > 1:
                stats_holder["multi_row_fid_count"] = int(stats_holder["multi_row_fid_count"]) + 1
                multi_row_examples = _require_type(stats_holder["multi_row_examples"], list, "runtime.multi_row_examples")
                if len(multi_row_examples) < 10:
                    multi_row_examples.append((record.fid, record.chunk_count))
            if record.chunk_count > int(stats_holder["max_chunks_per_fid"]):
                stats_holder["max_chunks_per_fid"] = record.chunk_count
                stats_holder["max_chunks_fid"] = record.fid
            yield record

    return generator(), stats_holder


def _build_group_record(file_cfg: FileConfig, fid: str, rows: List[Tuple[int, Optional[int], str]]) -> GroupRecord:
    ordered_rows = rows
    if file_cfg.order_mode == "split_part":
        split_values = [item[1] for item in rows]
        if any(value is None for value in split_values):
            raise WorkbookFormatError(f"{file_cfg.label} fid={fid} 存在空 split_part")
        seen = set()
        for value in split_values:
            if value in seen:
                raise WorkbookFormatError(f"{file_cfg.label} fid={fid} 出现重复 split_part: {value}")
            seen.add(value)
        ordered_rows = sorted(rows, key=lambda item: (item[1], item[0]))

    return GroupRecord(
        fid=fid,
        chunk_count=len(ordered_rows),
        merged_translation="".join(item[2] for item in ordered_rows),
        row_numbers=tuple(item[0] for item in ordered_rows),
        split_parts=tuple(item[1] for item in ordered_rows),
        chunk_lengths=tuple(len(item[2]) for item in ordered_rows),
    )


def _make_segment_parser(text_id_pattern: str):
    pattern_colon6 = re.compile(rf"^(?P<textId>{text_id_pattern})::::::\[(?P<payload>.*)\]$", re.DOTALL)
    pattern_triple_num = re.compile(rf"^(?P<textId>{text_id_pattern}:::\d+):::\[(?P<payload>.*)\]$", re.DOTALL)
    pattern_triple_range = re.compile(
        rf"^(?P<textId>{text_id_pattern}:::\d+(?:-\d+)+):::\[(?P<payload>.*)\]$",
        re.DOTALL,
    )

    def parse(segment: str) -> SegmentInfo:
        for pattern in (pattern_colon6, pattern_triple_num, pattern_triple_range):
            matched = pattern.fullmatch(segment)
            if matched is not None:
                return SegmentInfo(
                    raw=segment,
                    text_id=matched.group("textId"),
                    payload=matched.group("payload"),
                    is_valid=True,
                )
        return SegmentInfo(raw=segment, text_id=None, payload=None, is_valid=False)

    return parse


def _analyze_translation_diff(
    online_text: str,
    sys_text: str,
    split_delimiter: str,
    parse_segment,
) -> Dict[str, object]:
    online_segments_raw = [] if online_text == "" else online_text.split(split_delimiter)
    sys_segments_raw = [] if sys_text == "" else sys_text.split(split_delimiter)

    online_segments = [parse_segment(item) if item != "" else SegmentInfo(item, None, None, False) for item in online_segments_raw]
    sys_segments = [parse_segment(item) if item != "" else SegmentInfo(item, None, None, False) for item in sys_segments_raw]

    online_valid = [item for item in online_segments if item.is_valid]
    sys_valid = [item for item in sys_segments if item.is_valid]
    online_invalid_indexes = [idx + 1 for idx, item in enumerate(online_segments) if not item.is_valid]
    sys_invalid_indexes = [idx + 1 for idx, item in enumerate(sys_segments) if not item.is_valid]

    online_text_ids = [item.text_id for item in online_valid]
    sys_text_ids = [item.text_id for item in sys_valid]

    tags: List[str] = []
    if online_invalid_indexes or sys_invalid_indexes:
        tags.append("invalid_segment")
    if len(online_segments_raw) != len(sys_segments_raw):
        tags.append("segment_count_diff")
    if online_text_ids != sys_text_ids:
        tags.append("textid_sequence_diff")
    elif online_valid and sys_valid:
        payload_pairs = list(zip(online_valid, sys_valid))
        if any(left.payload != right.payload for left, right in payload_pairs):
            tags.append("same_textid_payload_diff")

    if _trim_trailing_empty_segments(online_segments_raw) == _trim_trailing_empty_segments(sys_segments_raw):
        if online_text != sys_text:
            tags.append("trailing_delimiter_diff")

    if _drop_all_empty_segments(online_segments_raw) == _drop_all_empty_segments(sys_segments_raw):
        if online_text != sys_text:
            tags.append("empty_segment_only_diff")

    if _normalize_whitespace(online_text) == _normalize_whitespace(sys_text) and online_text != sys_text:
        tags.append("whitespace_only_diff")

    first_diff_pos = _first_diff_position(online_text, sys_text)
    return {
        "online_segment_count": len(online_segments_raw),
        "sys_segment_count": len(sys_segments_raw),
        "online_invalid_indexes": online_invalid_indexes,
        "sys_invalid_indexes": sys_invalid_indexes,
        "same_textid_sequence": online_text_ids == sys_text_ids and len(online_valid) == len(sys_valid),
        "first_diff_position": first_diff_pos,
        "first_diff_context": _build_diff_context(online_text, sys_text, first_diff_pos),
        "tags": tags,
    }


def _trim_trailing_empty_segments(items: List[str]) -> List[str]:
    result = list(items)
    while result and result[-1] == "":
        result.pop()
    return result


def _drop_all_empty_segments(items: List[str]) -> List[str]:
    return [item for item in items if item != ""]


def _normalize_whitespace(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n").strip()


def _first_diff_position(left: str, right: str) -> int:
    limit = min(len(left), len(right))
    for index in range(limit):
        if left[index] != right[index]:
            return index
    return limit


def _build_diff_context(left: str, right: str, position: int) -> str:
    start = max(position - 20, 0)
    end = position + 20
    left_snippet = left[start:end].replace("\n", "\\n")
    right_snippet = right[start:end].replace("\n", "\\n")
    return f"online={left_snippet} | sys={right_snippet}"


def run_analysis(
    online_cfg: FileConfig,
    sys_cfg: FileConfig,
    compare_cfg: CompareConfig,
    output_cfg: OutputConfig,
) -> Dict[str, object]:
    online_headers = _read_header(online_cfg)
    sys_headers = _read_header(sys_cfg)
    parse_segment = _make_segment_parser(compare_cfg.text_id_pattern)

    online_map, online_stats = _collect_group_map_any_order(online_cfg)
    sys_map, sys_stats = _collect_group_map_any_order(sys_cfg)

    only_online = 0
    only_sys = 0
    exact_match = 0
    chunk_count_diff = 0
    chunk_count_diff_but_same_translation = 0
    translation_diff = 0
    structural_diff = 0
    tag_counter: Dict[str, int] = {}
    report_rows: List[List[str]] = []
    online_keys = set(online_map)
    sys_keys = set(sys_map)

    for fid in sorted(online_keys - sys_keys):
        only_online += 1
        online_group = online_map[fid]
        report_rows.append(
            [
                "only_online",
                online_group.fid,
                str(online_group.chunk_count),
                "",
                str(len(online_group.merged_translation)),
                "",
                "",
                "",
                "",
                "",
            ]
        )

    for fid in sorted(sys_keys - online_keys):
        only_sys += 1
        sys_group = sys_map[fid]
        report_rows.append(
            [
                "only_sys",
                sys_group.fid,
                "",
                str(sys_group.chunk_count),
                "",
                str(len(sys_group.merged_translation)),
                "",
                "",
                "",
                "",
            ]
        )

    for fid in sorted(online_keys & sys_keys):
        online_group = online_map[fid]
        sys_group = sys_map[fid]
        if online_group.chunk_count != sys_group.chunk_count:
            chunk_count_diff += 1

        if online_group.merged_translation == sys_group.merged_translation:
            exact_match += 1
            if online_group.chunk_count != sys_group.chunk_count:
                chunk_count_diff_but_same_translation += 1
                report_rows.append(
                    [
                        "chunk_count_diff_only",
                        online_group.fid,
                        str(online_group.chunk_count),
                        str(sys_group.chunk_count),
                        str(len(online_group.merged_translation)),
                        str(len(sys_group.merged_translation)),
                        "",
                        "",
                        "",
                        "聚合后 translation 完全一致，仅分片数量不同",
                    ]
                )
            continue

        translation_diff += 1
        diff_info = _analyze_translation_diff(
            online_group.merged_translation,
            sys_group.merged_translation,
            compare_cfg.split_delimiter,
            parse_segment,
        )
        tags = _require_type(diff_info["tags"], list, "runtime.tags")
        if any(tag in {"invalid_segment", "segment_count_diff", "textid_sequence_diff", "trailing_delimiter_diff", "empty_segment_only_diff"} for tag in tags):
            structural_diff += 1
        for tag in tags:
            tag_counter[tag] = tag_counter.get(tag, 0) + 1

        report_rows.append(
            [
                "translation_diff",
                online_group.fid,
                str(online_group.chunk_count),
                str(sys_group.chunk_count),
                str(len(online_group.merged_translation)),
                str(len(sys_group.merged_translation)),
                str(diff_info["online_segment_count"]),
                str(diff_info["sys_segment_count"]),
                "|".join(tags),
                str(diff_info["first_diff_context"]),
            ]
        )

    summary = {
        "online_headers": online_headers,
        "sys_headers": sys_headers,
        "online_stats": online_stats,
        "sys_stats": sys_stats,
        "only_online": only_online,
        "only_sys": only_sys,
        "exact_match": exact_match,
        "chunk_count_diff": chunk_count_diff,
        "chunk_count_diff_but_same_translation": chunk_count_diff_but_same_translation,
        "translation_diff": translation_diff,
        "structural_diff": structural_diff,
        "tag_counter": tag_counter,
        "report_rows": report_rows[: output_cfg.mismatch_example_limit],
        "report_total_rows": len(report_rows),
        "report_path": str(output_cfg.report_path),
    }
    _write_report(output_cfg.report_path, report_rows)
    _write_summary(output_cfg.summary_path, summary)
    return summary


def _build_file_stats(stats_holder: Dict[str, object]) -> FileStats:
    multi_row_examples = _require_type(stats_holder["multi_row_examples"], list, "runtime.multi_row_examples")
    return FileStats(
        row_count=int(stats_holder["row_count"]),
        fid_count=int(stats_holder["fid_count"]),
        multi_row_fid_count=int(stats_holder["multi_row_fid_count"]),
        max_chunk_length=int(stats_holder["max_chunk_length"]),
        max_chunk_fid=_require_type(stats_holder["max_chunk_fid"], str, "runtime.max_chunk_fid"),
        max_chunk_row=int(stats_holder["max_chunk_row"]),
        max_chunks_per_fid=int(stats_holder["max_chunks_per_fid"]),
        max_chunks_fid=_require_type(stats_holder["max_chunks_fid"], str, "runtime.max_chunks_fid"),
        multi_row_examples=tuple(multi_row_examples),
    )


def _collect_group_map_any_order(file_cfg: FileConfig) -> Tuple[Dict[str, GroupRecord], FileStats]:
    fid_order: List[str] = []
    grouped_rows: Dict[str, object] = {}
    row_count = 0
    max_chunk_length = 0
    max_chunk_fid = ""
    max_chunk_row = 0

    for row_number, row in _iter_sheet_rows(file_cfg.path, file_cfg.sheet):
        if row_number == 1:
            continue

        fid = _normalize_fid(row.get(file_cfg.fid_column), row_number, file_cfg.label)
        translation = _normalize_text(row.get(file_cfg.translation_column))
        row_count += 1

        if len(translation) > max_chunk_length:
            max_chunk_length = len(translation)
            max_chunk_fid = fid
            max_chunk_row = row_number

        if fid not in grouped_rows:
            fid_order.append(fid)
            if file_cfg.order_mode == "split_part":
                grouped_rows[fid] = {}
            else:
                grouped_rows[fid] = []

        if file_cfg.order_mode == "split_part":
            if file_cfg.split_part_column is None:
                raise WorkbookFormatError(f"{file_cfg.label} 缺少 splitPart 配置")
            split_part = _parse_split_part(row.get(file_cfg.split_part_column), row_number, file_cfg.label)
            part_map = _require_type(grouped_rows[fid], dict, "runtime.grouped_rows")
            if split_part in part_map:
                existing_row = part_map[split_part][0]
                raise WorkbookFormatError(
                    f"{file_cfg.label} fid={fid} 出现重复 split_part={split_part} "
                    f"(row {existing_row} / row {row_number})"
                )
            part_map[split_part] = (row_number, translation)
        else:
            items = _require_type(grouped_rows[fid], list, "runtime.grouped_rows")
            items.append((row_number, translation))

    grouped: Dict[str, GroupRecord] = {}
    multi_row_fid_count = 0
    max_chunks_per_fid = 0
    max_chunks_fid = ""
    multi_row_examples: List[Tuple[str, int]] = []

    for fid in fid_order:
        if file_cfg.order_mode == "split_part":
            part_map = _require_type(grouped_rows[fid], dict, "runtime.part_map")
            ordered_parts = sorted(part_map)
            row_numbers = tuple(part_map[part][0] for part in ordered_parts)
            split_parts = tuple(ordered_parts)
            chunk_texts = [part_map[part][1] for part in ordered_parts]
        else:
            items = _require_type(grouped_rows[fid], list, "runtime.items")
            row_numbers = tuple(item[0] for item in items)
            split_parts = tuple(None for _ in items)
            chunk_texts = [item[1] for item in items]

        record = GroupRecord(
            fid=fid,
            chunk_count=len(chunk_texts),
            merged_translation="".join(chunk_texts),
            row_numbers=row_numbers,
            split_parts=split_parts,
            chunk_lengths=tuple(len(text) for text in chunk_texts),
        )
        grouped[fid] = record

        if record.chunk_count > 1:
            multi_row_fid_count += 1
            if len(multi_row_examples) < 10:
                multi_row_examples.append((record.fid, record.chunk_count))
        if record.chunk_count > max_chunks_per_fid:
            max_chunks_per_fid = record.chunk_count
            max_chunks_fid = record.fid

    stats = FileStats(
        row_count=row_count,
        fid_count=len(grouped),
        multi_row_fid_count=multi_row_fid_count,
        max_chunk_length=max_chunk_length,
        max_chunk_fid=max_chunk_fid,
        max_chunk_row=max_chunk_row,
        max_chunks_per_fid=max_chunks_per_fid,
        max_chunks_fid=max_chunks_fid,
        multi_row_examples=tuple(multi_row_examples),
    )
    return grouped, stats


def _write_report(path: Path, rows: List[List[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "issue_type",
                "fid",
                "online_chunk_count",
                "sys_chunk_count",
                "online_length",
                "sys_length",
                "online_segment_count",
                "sys_segment_count",
                "tags",
                "note",
            ]
        )
        writer.writerows(rows)


def _write_summary(path: Path, summary: Dict[str, object]) -> None:
    online_stats = _require_type(summary["online_stats"], FileStats, "runtime.online_stats")
    sys_stats = _require_type(summary["sys_stats"], FileStats, "runtime.sys_stats")
    tag_counter = _require_type(summary["tag_counter"], dict, "runtime.tag_counter")
    lines = [
        "# 汉化包格式差异分析",
        "",
        "## 文件结构",
        f"- online 表头: {list(summary['online_headers'])}",
        f"- sys 表头: {list(summary['sys_headers'])}",
        "",
        "## online 统计",
        f"- 数据行数: {online_stats.row_count}",
        f"- fid 数量: {online_stats.fid_count}",
        f"- 多行分片 fid 数量: {online_stats.multi_row_fid_count}",
        f"- 最大单行长度: {online_stats.max_chunk_length} (fid={online_stats.max_chunk_fid}, row={online_stats.max_chunk_row})",
        f"- 最大分片数: {online_stats.max_chunks_per_fid} (fid={online_stats.max_chunks_fid})",
        f"- 多行示例: {list(online_stats.multi_row_examples)}",
        "",
        "## sys 统计",
        f"- 数据行数: {sys_stats.row_count}",
        f"- fid 数量: {sys_stats.fid_count}",
        f"- 多行分片 fid 数量: {sys_stats.multi_row_fid_count}",
        f"- 最大单行长度: {sys_stats.max_chunk_length} (fid={sys_stats.max_chunk_fid}, row={sys_stats.max_chunk_row})",
        f"- 最大分片数: {sys_stats.max_chunks_per_fid} (fid={sys_stats.max_chunks_fid})",
        f"- 多行示例: {list(sys_stats.multi_row_examples)}",
        "",
        "## 比对结果",
        f"- only_online: {summary['only_online']}",
        f"- only_sys: {summary['only_sys']}",
        f"- 聚合后完全一致: {summary['exact_match']}",
        f"- 分片数量不同: {summary['chunk_count_diff']}",
        f"- 仅分片数量不同但聚合后完全一致: {summary['chunk_count_diff_but_same_translation']}",
        f"- 聚合后 translation 不一致: {summary['translation_diff']}",
        f"- 其中结构性差异: {summary['structural_diff']}",
        "",
        "## 结构差异标签统计",
    ]
    if tag_counter:
        for key in sorted(tag_counter):
            lines.append(f"- {key}: {tag_counter[key]}")
    else:
        lines.append("- 无")
    lines.extend(
        [
            "",
            "## 报告文件",
            f"- 详细 CSV: {summary['report_path']}",
            "",
            "## 示例记录数量",
            f"- 已写入报告行数: {summary['report_total_rows']}",
            f"- 摘要内保留样例上限: {len(summary['report_rows'])}",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="比较 online 与 sys 汉化包 xlsx 的格式差异")
    parser.add_argument("--config", required=True, help="JSON 配置文件路径")
    args = parser.parse_args()

    config_path = Path(args.config).expanduser().resolve()
    online_cfg, sys_cfg, compare_cfg, output_cfg = _load_config(config_path)
    summary = run_analysis(online_cfg, sys_cfg, compare_cfg, output_cfg)
    print(json.dumps(
        {
            "only_online": summary["only_online"],
            "only_sys": summary["only_sys"],
            "exact_match": summary["exact_match"],
            "chunk_count_diff": summary["chunk_count_diff"],
            "chunk_count_diff_but_same_translation": summary["chunk_count_diff_but_same_translation"],
            "translation_diff": summary["translation_diff"],
            "structural_diff": summary["structural_diff"],
            "summary_path": str(output_cfg.summary_path),
            "report_path": str(output_cfg.report_path),
        },
        ensure_ascii=False,
        indent=2,
    ))


if __name__ == "__main__":
    main()
