from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from .service.stage.export import ProjectStagesReport


HEADERS = [
    "№",
    "Этап",
    "Статус",
    "Плановое начало",
    "Плановое завершение",
    "Фактическое нало",
    "Фактичнское завершение",
    "Ответсвенный",
    "Просрочен",
    "Длительность (дни)",
    "Описание",
    "Критерии завершения",
]


def export_project_stages_to_excel(report: ProjectStagesReport) -> bytes:
    """
    Сформировать Excel-файл отчета по этапам проекта.
    """

    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Этапы проекта"

    worksheet["A1"] = f"Отчет по этапам проекта: {report.project_name}"
    worksheet["A2"] = f"Ключ проекта: {report.project_key}"
    worksheet["A3"] = f"Статус проекта: {report.project_status}"
    worksheet["A4"] = f"Дата формирования: {report.generated_at:%d.%m.%Y %H:%M}"

    for cell in ("A1", "A2", "A3", "A4"):
        worksheet[cell].font = Font(bold=True)

    header_row = 6
    for column_index, header in enumerate(HEADERS, start=1):
        cell = worksheet.cell(row=header_row, column=column_index, value=header)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="4F81BD")
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    for row_index, row in enumerate(report.rows, start=header_row + 1):
        values = [
            row.number,
            row.name,
            row.status,
            row.planned_start,
            row.planned_end,
            row.started_at,
            row.completed_at,
            row.responsible_id,
            row.is_overdue,
            row.planned_duration_days,
            row.description,
            row.completion_criteria,
        ]

        for column_index, value in enumerate(values, start=1):
            cell = worksheet.cell(row=row_index, column=column_index, value=value)
            cell.alignment = Alignment(vertical="top", wrap_text=True)

    worksheet.freeze_panes = "A7"
    worksheet.auto_filter.ref = (
        f"A{header_row}:{get_column_letter(len(HEADERS))}{max(header_row, header_row + len(report.rows))}"
    )

    column_widths = [6, 28, 16, 18, 20, 20, 22, 38, 14, 18, 42, 42]
    for column_index, width in enumerate(column_widths, start=1):
        worksheet.column_dimensions[get_column_letter(column_index)].width = width

    output = BytesIO()
    workbook.save(output)
    return output.getvalue()

def export_project_stages_to_pdf(report: ProjectStagesReport) -> bytes:


def export_project_stages_to_word(report: ProjectStagesReport) -> bytes:
