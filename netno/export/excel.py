from __future__ import annotations

from pathlib import Path

import pandas as pd
from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

HEADER_FILL = PatternFill("solid", start_color="1F3864")
LONG_COLS = {"text", "quote", "note", "example", "value", "description"}


def _style(ws, df: pd.DataFrame) -> None:
    for c in ws[1]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = HEADER_FILL
        c.alignment = Alignment(vertical="center", wrap_text=True)
    ws.freeze_panes = "A2"
    if len(df):
        ws.auto_filter.ref = ws.dimensions
    for i, col in enumerate(df.columns, start=1):
        long = str(col).lower() in LONG_COLS
        lens = [len(str(v)) for v in df[col].head(200) if pd.notna(v)]
        sample = max(lens) if lens else 10
        width = 90 if long else min(max(len(str(col)) + 2, sample + 2), 45)
        ws.column_dimensions[get_column_letter(i)].width = width
        if long:
            for cell in ws[get_column_letter(i)][1:]:
                cell.alignment = Alignment(wrap_text=True, vertical="top")


def _chart(ws, df, kind, title, cat, val, anchor):
    if len(df) < 1 or cat not in df.columns or val not in df.columns:
        return
    n = len(df)
    ch = LineChart() if kind == "line" else BarChart()
    ch.title, ch.height, ch.width = title, 8.5, 18
    ch.add_data(Reference(ws, min_col=list(df.columns).index(val) + 1, min_row=1, max_row=n + 1), titles_from_data=True)
    ch.set_categories(Reference(ws, min_col=list(df.columns).index(cat) + 1, min_row=2, max_row=n + 1))
    ws.add_chart(ch, anchor)


def write_workbook(path: Path, sheets: dict[str, pd.DataFrame]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(path, engine="openpyxl", datetime_format="yyyy-mm-dd") as xw:
        for name, df in sheets.items():
            df.to_excel(xw, sheet_name=name[:31], index=False)
            _style(xw.sheets[name[:31]], df)
        if "Platform_Profile" in sheets:
            df = sheets["Platform_Profile"]
            _chart(xw.sheets["Platform_Profile"], df, "bar", "Items by platform", "platform", "items", "N2")
            _chart(xw.sheets["Platform_Profile"], df, "bar", "Avg sentiment by platform", "platform", "avg_sentiment", "N20")
        if "Themes" in sheets:
            _chart(xw.sheets["Themes"], sheets["Themes"], "bar", "Avg sentiment by theme", "theme", "avg_sentiment", "I2")
        if "Timeline" in sheets:
            _chart(xw.sheets["Timeline"], sheets["Timeline"], "line", "Sentiment over time", "month", "avg_sentiment", "G2")
    return path
