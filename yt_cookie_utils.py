"""Проверка Netscape cookies для YouTube и атомарная запись в файл из памяти."""

import os
import tempfile


def validate_netscape_youtube_cookies(text: str) -> tuple[bool, str]:
    """
    Проверяет, что текст похож на авторизованный экспорт cookies YouTube в формате Netscape.
    Возвращает (успех, сообщение об ошибке).
    """
    if not text or not text.strip():
        return False, "Файл пустой."

    stripped = text.strip()
    if stripped.startswith("\ufeff"):
        stripped = stripped[1:]

    data_lines: list[str] = []
    for raw in stripped.splitlines():
        line = raw.rstrip("\r")
        s = line.strip()
        if not s:
            continue
        if s.startswith("#") and not s.startswith("#HttpOnly_"):
            continue
        data_lines.append(line)

    if not data_lines:
        return False, "Нет строк с данными cookies (ожидается формат Netscape)."

    valid_lines = 0
    youtube_or_google = False

    for line in data_lines:
        if "\t" not in line:
            continue
        parts = line.split("\t")
        if len(parts) < 7:
            continue
        valid_lines += 1
        domain = parts[0].strip()
        if domain.startswith("#HttpOnly_"):
            domain = domain[len("#HttpOnly_") :]
        elif domain.startswith("#"):
            domain = domain[1:]
        domain = domain.lower()
        if "youtube" in domain or domain.endswith("google.com") or ".google." in domain:
            youtube_or_google = True

    if valid_lines == 0:
        return (
            False,
            "Ни одна строка не похожа на Netscape cookie (нужны 7 полей, разделитель — табуляция).",
        )
    if not youtube_or_google:
        return (
            False,
            "Нет cookies для youtube.com или google.com — экспортируйте cookies с авторизованной сессии YouTube.",
        )
    return True, ""


def write_cookie_file_atomic(target_path: str, content: str) -> None:
    """Записывает содержимое в target_path атомарно (без отдельного сохранения загрузки Telegram)."""
    directory = os.path.dirname(os.path.abspath(target_path)) or "."
    os.makedirs(directory, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix=".yt_cookie_", suffix=".tmp", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
            f.write(content)
        os.replace(tmp_path, target_path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
