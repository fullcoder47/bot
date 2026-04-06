from __future__ import annotations

import io
import re
import zipfile
from calendar import monthrange
from datetime import date, datetime, timedelta, timezone
from xml.sax.saxutils import escape
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.attendance_record_repo import AttendanceRecordRepository
from app.domain.dto.company_dto import CompanyAdminAccessDTO
from app.domain.enums.attendance_status import AttendanceStatus


def _app_tz():
    try:
        return ZoneInfo("Asia/Tashkent")
    except ZoneInfoNotFoundError:
        return timezone(timedelta(hours=5))


class AttendanceExportService:
    APP_TZ = _app_tz()

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.attendance_record_repo = AttendanceRecordRepository(session)

    @classmethod
    def today(cls) -> date:
        return datetime.now(cls.APP_TZ).date()

    @staticmethod
    def _slugify(value: str) -> str:
        cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", value.strip())
        return cleaned.strip("_") or "company"

    @staticmethod
    def _format_dt(value: datetime | None) -> str:
        return value.astimezone(AttendanceExportService.APP_TZ).strftime("%Y-%m-%d %H:%M") if value else ""

    @staticmethod
    def _status_text(status: AttendanceStatus) -> str:
        mapping = {
            AttendanceStatus.PRESENT: "PRESENT",
            AttendanceStatus.LATE: "LATE",
            AttendanceStatus.ABSENT: "ABSENT",
            AttendanceStatus.EARLY_LEAVE: "EARLY_LEAVE",
            AttendanceStatus.HALF_DAY: "HALF_DAY",
            AttendanceStatus.ON_LEAVE: "ON_LEAVE",
            AttendanceStatus.SICK_LEAVE: "SICK_LEAVE",
            AttendanceStatus.WEEKEND: "WEEKEND",
        }
        return mapping.get(status, status.value)

    @classmethod
    def _resolve_period(cls, preset: str) -> tuple[date | None, date | None, str]:
        today = cls.today()
        if preset == "today":
            return today, today, today.isoformat()
        if preset == "month":
            first_day = today.replace(day=1)
            last_day = today.replace(day=monthrange(today.year, today.month)[1])
            return first_day, last_day, f"{today.year}-{today.month:02d}"
        return None, None, "all"

    @staticmethod
    def _column_name(index: int) -> str:
        result = ""
        current = index
        while current > 0:
            current, remainder = divmod(current - 1, 26)
            result = chr(65 + remainder) + result
        return result

    @classmethod
    def _worksheet_xml(cls, headers: list[str], rows: list[list[str]]) -> str:
        def inline_cell(ref: str, value: str) -> str:
            safe = escape(value)
            return (
                f'<c r="{ref}" t="inlineStr"><is><t xml:space="preserve">{safe}</t></is></c>'
            )

        all_rows = [headers, *rows]
        row_xml_parts: list[str] = []
        for row_index, row_values in enumerate(all_rows, start=1):
            cells = [
                inline_cell(f"{cls._column_name(column_index)}{row_index}", str(value))
                for column_index, value in enumerate(row_values, start=1)
            ]
            row_xml_parts.append(f'<row r="{row_index}">{"".join(cells)}</row>')

        last_column = cls._column_name(len(headers))
        dimension = f"A1:{last_column}{max(len(all_rows), 1)}"
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            f'<dimension ref="{dimension}"/>'
            '<sheetViews><sheetView workbookViewId="0"/></sheetViews>'
            '<sheetFormatPr defaultRowHeight="15"/>'
            f'<sheetData>{"".join(row_xml_parts)}</sheetData>'
            '</worksheet>'
        )

    @classmethod
    def _build_xlsx(cls, sheet_name: str, headers: list[str], rows: list[list[str]]) -> bytes:
        content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>"""
        rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>"""
        workbook = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>
    <sheet name="{escape(sheet_name)}" sheetId="1" r:id="rId1"/>
  </sheets>
</workbook>"""
        workbook_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>"""
        core = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:dcmitype="http://purl.org/dc/dcmitype/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:creator>attendance-bot</dc:creator>
  <cp:lastModifiedBy>attendance-bot</cp:lastModifiedBy>
</cp:coreProperties>"""
        app = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
  <Application>attendance-bot</Application>
</Properties>"""
        worksheet = cls._worksheet_xml(headers, rows)

        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as workbook_zip:
            workbook_zip.writestr("[Content_Types].xml", content_types)
            workbook_zip.writestr("_rels/.rels", rels)
            workbook_zip.writestr("xl/workbook.xml", workbook)
            workbook_zip.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
            workbook_zip.writestr("xl/worksheets/sheet1.xml", worksheet)
            workbook_zip.writestr("docProps/core.xml", core)
            workbook_zip.writestr("docProps/app.xml", app)
        return buffer.getvalue()

    async def export_company_attendance(
        self,
        access: CompanyAdminAccessDTO,
        *,
        preset: str,
    ) -> tuple[str, bytes, int]:
        date_from, date_to, label = self._resolve_period(preset)
        records = await self.attendance_record_repo.list_for_company_period(
            access.company.id,
            date_from=date_from,
            date_to=date_to,
        )

        headers = [
            "Date",
            "Employee",
            "Employee Code",
            "Telegram ID",
            "Branch",
            "Shift",
            "Check In",
            "Check Out",
            "Status",
            "Late Minutes",
            "Early Leave Minutes",
            "Worked Minutes",
            "Suspicious",
        ]
        rows: list[list[str]] = []
        for record in records:
            employee = record.employee
            branch_name = employee.branch.name if employee and employee.branch else ""
            shift_name = employee.shift.name if employee and employee.shift else ""
            rows.append(
                [
                    record.date.isoformat(),
                    employee.full_name if employee else "",
                    employee.employee_code or "" if employee else "",
                    str(employee.telegram_id) if employee and employee.telegram_id else "",
                    branch_name,
                    shift_name,
                    self._format_dt(record.check_in_time),
                    self._format_dt(record.check_out_time),
                    self._status_text(record.status),
                    str(record.late_minutes),
                    str(record.early_leave_minutes),
                    str(record.worked_minutes),
                    "YES" if record.is_suspicious else "NO",
                ]
            )

        file_name = f"attendance_{self._slugify(access.company.name)}_{label}.xlsx"
        return file_name, self._build_xlsx("Attendance", headers, rows), len(rows)
