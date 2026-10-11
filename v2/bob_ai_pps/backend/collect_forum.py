
import json
import re
from pathlib import Path
from urllib.parse import urljoin

from playwright.sync_api import sync_playwright

BASE_URL = "https://forum.amazing-online.com"
SECTION_URL = BASE_URL + "/forums/pravitelstvo.144/"
OUTPUT_FILE = Path("collected_topics_v2.json")


def clean_thread_url(url):
    match = re.search(r"/threads/([^/?#]+?\.\d+)", url)
    if not match:
        return None
    return BASE_URL + "/threads/" + match.group(1) + "/"


with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    topics = {}

    # Р С›Р В±РЎвЂ¦Р С•Р Т‘Р С‘Р С РЎРѓРЎвЂљРЎР‚Р В°Р Р…Р С‘РЎвЂ РЎвЂ№ РЎР‚Р В°Р В·Р Т‘Р ВµР В»Р В°
    for page_num in range(1, 101):
        section_url = (
            SECTION_URL if page_num == 1
            else f"{SECTION_URL}page-{page_num}"
        )

        print(f"\nР В Р В°Р В·Р Т‘Р ВµР В»: РЎРѓРЎвЂљРЎР‚Р В°Р Р…Р С‘РЎвЂ Р В° {page_num}")
        page.goto(
            section_url,
            wait_until="domcontentloaded",
            timeout=60000
        )
        page.wait_for_timeout(1500)

        # Р вЂР ВµРЎР‚РЎвЂР С РЎвЂљР С•Р В»РЎРЉР С”Р С• Р В·Р В°Р С–Р С•Р В»Р С•Р Р†Р С”Р С‘ РЎвЂљР ВµР С, Р В° Р Р…Р Вµ Р Т‘Р В°РЎвЂљРЎвЂ№ Р С‘ Р Р…Р С•Р СР ВµРЎР‚Р В° РЎРѓРЎвЂљРЎР‚Р В°Р Р…Р С‘РЎвЂ 
        titles = page.locator(
            ".structItem-title a[href*='/threads/']"
        ).evaluate_all("""
            els => els.map(a => ({
                title: a.innerText.trim(),
                url: a.href
            }))
        """)

        if not titles:
            print("Р вЂ”Р В°Р С–Р С•Р В»Р С•Р Р†Р С”Р С‘ РЎвЂљР ВµР С Р Р…Р Вµ Р Р…Р В°Р в„–Р Т‘Р ВµР Р…РЎвЂ№ РІР‚вЂќ Р В·Р В°Р С”Р В°Р Р…РЎвЂЎР С‘Р Р†Р В°РЎР‹ Р С•Р В±РЎвЂ¦Р С•Р Т‘.")
            break

        new_count = 0
        for item in titles:
            url = clean_thread_url(item["url"])
            title = item["title"].strip()

            if url and title and url not in topics:
                topics[url] = title
                new_count += 1

        print(
            f"Р СњР В°Р в„–Р Т‘Р ВµР Р…Р С• Р В·Р В°Р С–Р С•Р В»Р С•Р Р†Р С”Р С•Р Р†: {len(titles)}; "
            f"Р Р…Р С•Р Р†РЎвЂ№РЎвЂ¦ РЎвЂљР ВµР С: {new_count}"
        )

        # Р вЂўРЎРѓР В»Р С‘ Р Р…Р С•Р Р†РЎвЂ№РЎвЂ¦ РЎвЂљР ВµР С Р Р…Р ВµРЎвЂљ, Р Т‘Р В°Р В»РЎРЉРЎв‚¬Р Вµ Р С‘Р Т‘РЎвЂљР С‘ Р С•Р В±РЎвЂ№РЎвЂЎР Р…Р С• Р Р…Р Вµ Р Р…РЎС“Р В¶Р Р…Р С•
        if page_num > 1 and new_count == 0:
            break

    print(f"\nР вЂ™РЎРѓР ВµР С–Р С• РЎС“Р Р…Р С‘Р С”Р В°Р В»РЎРЉР Р…РЎвЂ№РЎвЂ¦ РЎвЂљР ВµР С: {len(topics)}")

    results = []
    for index, (url, title) in enumerate(topics.items(), start=1):
        print(f"[{index}/{len(topics)}] {title[:80]}")


        try:
            page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=60000
            )
            page.wait_for_timeout(2500)

            print("    URL:", page.url)
            print("    Р вЂ”Р В°Р С–Р С•Р В»Р С•Р Р†Р С•Р С” Р Р†Р С”Р В»Р В°Р Т‘Р С”Р С‘:", page.title())

            # Р СџРЎР‚Р С•Р В±РЎС“Р ВµР С Р Р…Р ВµРЎРѓР С”Р С•Р В»РЎРЉР С”Р С• Р Р†Р В°РЎР‚Р С‘Р В°Р Р…РЎвЂљР С•Р Р† Р В·Р В°Р С–Р С•Р В»Р С•Р Р†Р С”Р В°
            actual_title = ""
            for selector in [
                ".p-title-value",
                "h1",
                ".p-body-pageTitle"
            ]:
                try:
                    locator = page.locator(selector).first
                    if locator.count() > 0:
                        candidate = locator.inner_text(timeout=2000).strip()
                        if candidate:
                            actual_title = candidate
                            break
                except Exception:
                    pass

            # Р РЋР С•Р В±Р С‘РЎР‚Р В°Р ВµР С РЎвЂљР ВµР С”РЎРѓРЎвЂљ РЎРѓР С•Р С•Р В±РЎвЂ°Р ВµР Р…Р С‘Р в„– РЎвЂљР ВµР СРЎвЂ№
            posts = page.locator(
                ".message .bbWrapper"
            ).all_inner_texts()

            content = "\n\n".join(
                text.strip() for text in posts if text.strip()
            )

            if not content:
                print("    Р СћР ВµР С”РЎРѓРЎвЂљ РЎвЂљР ВµР СРЎвЂ№ Р Р…Р Вµ Р Р…Р В°Р в„–Р Т‘Р ВµР Р….")
                print(
                    "    Р СњР В°РЎвЂЎР В°Р В»Р С• РЎРѓРЎвЂљРЎР‚Р В°Р Р…Р С‘РЎвЂ РЎвЂ№:",
                    page.locator("body").inner_text()[:500]
                )
                continue

            results.append({
                "title": title,
                "url": url,
                "content": content,
            })

            print("    Р вЂ”Р В°Р С–Р С•Р В»Р С•Р Р†Р С•Р С”:", actual_title or title)
            print("    Р РЋР С‘Р СР Р†Р С•Р В»Р С•Р Р†:", len(content))

        except Exception as error:
            print("    Р С›РЎв‚¬Р С‘Р В±Р С”Р В°:", str(error)[:250])


    OUTPUT_FILE.write_text(
        json.dumps(results, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print("\nР РЋР С•РЎвЂ¦РЎР‚Р В°Р Р…Р ВµР Р…Р С• РЎвЂљР ВµР С:", len(results))
    print("Р В¤Р В°Р в„–Р В»:", OUTPUT_FILE.resolve())

    input("Р СњР В°Р В¶Р СР С‘ Enter Р Т‘Р В»РЎРЏ Р В·Р В°Р С”РЎР‚РЎвЂ№РЎвЂљР С‘РЎРЏ Р В±РЎР‚Р В°РЎС“Р В·Р ВµРЎР‚Р В°...")
    browser.close()
