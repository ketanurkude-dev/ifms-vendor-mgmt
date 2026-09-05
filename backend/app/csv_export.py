"""Shared CSV-export helper for reports (FR "export in approved formats
such as PDF and CSV/XLSX" -- this prototype supports CSV)."""

import csv
import io

from fastapi.responses import StreamingResponse


def rows_to_csv_response(rows: list[dict], filename: str) -> StreamingResponse:
    buffer = io.StringIO()
    if rows:
        writer = csv.DictWriter(buffer, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]), media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
