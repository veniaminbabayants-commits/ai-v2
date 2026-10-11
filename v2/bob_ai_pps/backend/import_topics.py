
import json
import sqlite3
import time
from pathlib import Path

DB_FILE = Path("bob_ai.db")
JSON_FILE = Path("collected_topics_v2.json")

SERVER = "RED"
ORGANIZATION = "Правительство"
SPHERE = "Гос. организации"

CHUNK_SIZE = 1200
CHUNK_OVERLAP = 180


def split_text(text):
    text = text.strip()
    if not text:
        return []

    chunks = []
    start = 0

    while start < len(text):
        end = min(start + CHUNK_SIZE, len(text))
        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= len(text):
            break

        start = end - CHUNK_OVERLAP

    return chunks


def main():
    if not DB_FILE.exists():
        print("ОШИБКА: база bob_ai.db не найдена.")
        return

    if not JSON_FILE.exists():
        print("ОШИБКА: файл collected_topics_v2.json не найден.")
        return

    topics = json.loads(JSON_FILE.read_text(encoding="utf-8"))

    if not isinstance(topics, list):
        print("ОШИБКА: JSON должен содержать список тем.")
        return

    connection = sqlite3.connect(DB_FILE)

    added_sources = 0
    added_chunks = 0
    skipped = 0
    empty = 0

    try:
        with connection:
            for topic in topics:
                title = str(topic.get("title", "")).strip()
                url = str(topic.get("url", "")).strip()
                content = str(topic.get("content", "")).strip()

                if not title or not url or not content:
                    empty += 1
                    print("Пропуск: пустое название, URL или текст.")
                    continue

                existing = connection.execute(
                    "SELECT id FROM sources WHERE url = ?",
                    (url,)
                ).fetchone()

                if existing:
                    skipped += 1
                    print("Уже есть в базе:", title)
                    continue

                cursor = connection.execute(
                    """
                    INSERT INTO sources
                        (url, title, added_at, server, organization, sphere)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        url,
                        title,
                        int(time.time()),
                        SERVER,
                        ORGANIZATION,
                        SPHERE,
                    )
                )

                source_id = cursor.lastrowid
                chunks = split_text(content)

                connection.executemany(
                    """
                    INSERT INTO chunks (source_id, chunk_index, text)
                    VALUES (?, ?, ?)
                    """,
                    [
                        (source_id, index, chunk)
                        for index, chunk in enumerate(chunks)
                    ]
                )

                added_sources += 1
                added_chunks += len(chunks)

                print(
                    f"Добавлено: {title} "
                    f"| фрагментов: {len(chunks)}"
                )

        print("\n--- РЕЗУЛЬТАТ ---")
        print("Новых источников:", added_sources)
        print("Новых фрагментов:", added_chunks)
        print("Пропущено уже существующих:", skipped)
        print("Пропущено пустых записей:", empty)

    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


if __name__ == "__main__":
    main()
