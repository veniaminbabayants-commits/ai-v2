from pathlib import Path
from html import unescape
import re
import sqlite3
import time

from bs4 import BeautifulSoup

BASE_DIR = Path(__file__).resolve().parent
HTML_FILE = BASE_DIR / "test_thread.html.html"
DB_FILE = BASE_DIR / "bob_ai.db"

# Метаданные импортируемой темы
SERVER = "BLACK"
ORGANIZATION = "Правительство"
SPHERE = "Гос. организации"
URL = "https://forum.amazing-online.com/threads/pravitelstvo-reestr-vydachi-vygovorov-i-uvolnenij.937271/"


def split_text(text, size=1200, overlap=180):
    chunks = []
    start = 0

    while start < len(text):
        end = min(start + size, len(text))
        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= len(text):
            break

        start = end - overlap

    return chunks


def main():
    if not HTML_FILE.exists():
        raise FileNotFoundError(f"Не найден HTML-файл: {HTML_FILE}")

    html = HTML_FILE.read_text(encoding="utf-8", errors="replace")
    soup = BeautifulSoup(html, "html.parser")

    articles = soup.select("article.message-body")
    if not articles:
        raise RuntimeError(
            "Сообщения не найдены. Проверь, что сохранена именно страница темы."
        )

    messages = []

    for article in articles:
        body = article.select_one(".bbWrapper")
        if not body:
            continue

        # Убираем цитаты и скрытые элементы, чтобы не смешивать их
        # с авторским текстом текущего сообщения.
        for element in body.select(
            "blockquote, .bbCodeBlock, .js-selectToQuoteEnd, script, style"
        ):
            element.decompose()

        text = body.get_text("\n", strip=True)
        text = unescape(text)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text).strip()

        if text:
            messages.append(text)

    if not messages:
        raise RuntimeError("В найденных сообщениях не удалось извлечь текст.")

    # Сохраняем сообщения отдельно друг от друга, не теряя их границы.
    full_text = "\n\n--- Следующее сообщение ---\n\n".join(messages)
    chunks = split_text(full_text)

    conn = sqlite3.connect(DB_FILE)
    try:
        conn.row_factory = sqlite3.Row

        existing = conn.execute(
            "SELECT id FROM sources WHERE url = ?", (URL,)
        ).fetchone()

        title = "Правительство | Реестр выдачи выговоров и увольнений"

        if existing:
            source_id = existing["id"]
            conn.execute(
                "DELETE FROM chunks WHERE source_id = ?", (source_id,)
            )
            conn.execute(
                """UPDATE sources
                   SET title=?, added_at=?, server=?, organization=?, sphere=?
                   WHERE id=?""",
                (title, int(time.time()), SERVER, ORGANIZATION, SPHERE, source_id),
            )
        else:
            cursor = conn.execute(
                """INSERT INTO sources
                   (url, title, added_at, server, organization, sphere)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (URL, title, int(time.time()), SERVER, ORGANIZATION, SPHERE),
            )
            source_id = cursor.lastrowid

        conn.executemany(
            "INSERT INTO chunks (source_id, chunk_index, text) VALUES (?, ?, ?)",
            [(source_id, i, chunk) for i, chunk in enumerate(chunks)],
        )
        conn.commit()

        print("Импорт завершён.")
        print(f"Источник ID: {source_id}")
        print(f"Сообщений извлечено: {len(messages)}")
        print(f"Фрагментов сохранено: {len(chunks)}")
        print(f"Сервер: {SERVER}")
        print(f"Организация: {ORGANIZATION}")
        print(f"Категория: {SPHERE}")

        print("\nНачало извлечённого текста:")
        print(full_text[:1500])

    finally:
        conn.close()


if __name__ == "__main__":
    main()
