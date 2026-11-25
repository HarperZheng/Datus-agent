"""Export the semantic modeling design manual (xlsx) to agent-readable markdown.

The xlsx is the single source of truth; the markdown files under
docs/modeling-input/ are derived artifacts for semantic_modeling to consume
via read_file. Never hand-edit the generated md — rerun this script instead.

Usage: uv run python nontax_product/scripts/export_design_manual.py
"""

import datetime
import re
from pathlib import Path

import openpyxl

BASE = Path(__file__).resolve().parents[1]
XLSX = BASE / "docs" / "非税问数-设计-语义层建模设计手册-国库独立-fujian.xlsx"
OUT = BASE / "docs" / "modeling-input"

# sheet 名 → (输出文件名, 转换方式)
SHEET_PLAN = [
    ("导读", "00-导读与建模规则.md", "prose"),
    ("白名单字段清单-收缴清分", "01-数据集一收缴清分-字段白名单.md", "table"),
    ("白名单字段清单-专户代收收入", "02-数据集二专户代收收入-字段白名单.md", "table"),
    ("白名单字段清单-国库收入", "03-数据集三国库收入-字段白名单.md", "table"),
    ("跨集同名与对齐字段", "04-跨集同名与对齐关系.md", "table"),
    ("预设指标", "05-预设指标清单.md", "table"),
    ("黑名单字段", "06-黑名单字段.md", "table"),
]

SECTION_RE = re.compile(r"^[一二三四五六七八九十]+、")


def expand_merged(ws):
    """合并单元格只有左上角有值——解除合并并把值填充到全部成员格，避免转换出空洞。"""
    for rng in list(ws.merged_cells.ranges):
        v = ws.cell(row=rng.min_row, column=rng.min_col).value
        ws.unmerge_cells(str(rng))
        for r in range(rng.min_row, rng.max_row + 1):
            for c in range(rng.min_col, rng.max_col + 1):
                ws.cell(row=r, column=c).value = v


def cell_str(v):
    if v is None:
        return ""
    return str(v).replace("\r\n", "\n").strip()


def tc(v):
    """表格单元格转义：竖线转义、换行转 <br>。"""
    return cell_str(v).replace("|", "\\|").replace("\n", "<br>")


def export_prose(ws):
    """导读：两列（标签|内容）逐行转段落；单列行转标题/段落。"""
    lines = []
    for i, row in enumerate(ws.iter_rows(values_only=True), start=1):
        a = cell_str(row[0]) if len(row) > 0 else ""
        b = cell_str(row[1]) if len(row) > 1 else ""
        rest = [cell_str(v) for v in row[2:] if cell_str(v)]
        if not a and not b and not rest:
            continue
        if i == 1:
            lines.append(f"# {a or b}")
        elif a and b and a == b:
            # 合并单元格展开后 A=B：按单列行处理
            lines.append(f"### {a}" if SECTION_RE.match(a) else a)
        elif a and b:
            lines.append(f"**{a}**：{b}")
        elif b:
            lines.append(f"### {b}" if SECTION_RE.match(b) else b)
        elif a:
            if SECTION_RE.match(a):
                lines.append(f"### {a}")
            elif i == 1 or "手册" in a:
                lines.append(f"# {a}")
            else:
                lines.append(a)
        if rest:
            lines.extend(rest)
    return lines


def export_table(ws):
    """表格类 sheet：首行作表头，其余行进表格；孤立单列行转为表后注记。"""
    rows = [row for row in ws.iter_rows(values_only=True)]
    rows = [r for r in rows if any(cell_str(v) for v in r)]
    if not rows:
        return []
    header = [cell_str(v) or "—" for v in rows[0]]
    ncol = len(rows[0])
    lines = ["| " + " | ".join(tc(h) for h in header) + " |", "|" + "|".join(["---"] * ncol) + "|"]
    notes = []
    n_data = 0
    for r in rows[1:]:
        cells = [cell_str(v) for v in r]
        if sum(1 for c in cells if c) == 1:
            notes.append(cells[[i for i, c in enumerate(cells) if c][0]])
            continue
        lines.append("| " + " | ".join(tc(v) for v in cells) + " |")
        n_data += 1
    for n in notes:
        lines.append("")
        lines.append(f"> {n}")
    lines.append(f"<!-- 数据行数: {n_data} -->")
    return lines


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    wb = openpyxl.load_workbook(XLSX, data_only=True)
    stamp = datetime.date.today().isoformat()
    report = []
    for sheet, out_name, mode in SHEET_PLAN:
        ws = wb[sheet]
        expand_merged(ws)
        body = export_prose(ws) if mode == "prose" else export_table(ws)
        n_rows = len(
            [
                x
                for x in body
                if x
                and not x.startswith("<!")
                and not x.startswith("#")
                and not x.startswith("|---")
                and not x.startswith("> ")
            ]
        )
        header = (
            f"<!-- 由 {XLSX.name} 的 sheet「{sheet}」经 export_design_manual.py 生成，"
            f"勿手改；xlsx 变更后重跑脚本再生成。源行数: {n_rows}，生成日期: {stamp} -->"
        )
        (OUT / out_name).write_text(header + "\n\n" + "\n\n".join(body) + "\n", encoding="utf-8")
        report.append((out_name, n_rows))
    print("生成完成：")
    for name, n in report:
        print(f"  {name}: 源行数 {n}")


if __name__ == "__main__":
    main()
