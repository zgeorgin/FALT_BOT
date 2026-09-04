import re
from pathlib import Path

from docxtpl import DocxTemplate


def parse_string(s):
    pattern = r'^(Пользователь|Дата|Комментарий)\s*:\s*(.*?)(?=\n\w+\s*:|\Z)'
    matches = re.findall(pattern, s, re.DOTALL | re.MULTILINE)
    result = [i[1] for i in matches]
    return result


async def generate_file(text):
    base_dir = Path(__file__).resolve().parent
    template_path = base_dir / "studyroom_booked_template.docx"
    files_dir = base_dir.parent / "files"
    files_dir.mkdir(parents=True, exist_ok=True)

    doc = DocxTemplate(str(template_path))
    username, date, comment = parse_string(text)
    context = {
        "username": username,
        "date": date,
        "comment": comment
    }
    doc.render(context)
    safe_date = "".join([i if i.isalnum() else "_" for i in date])
    safe_date = re.sub(r"_+", "_", safe_date).strip("_") or "unknown"
    path = files_dir / f"Бронирование_боталки_{safe_date}.docx"
    doc.save(str(path))
    return str(path)
