import feedparser
import smtplib
import os
import re
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta

FEEDS = {
    "ASML Official":       "https://www.asml.com/en/news/rss",
    "Reuters Tech":        "https://feeds.reuters.com/reuters/technologyNews",
    "EE Times":            "https://www.eetimes.com/feed/",
    "The Register":        "https://www.theregister.com/headlines.atom",
    "Ars Technica":        "https://feeds.arstechnica.com/arstechnica/technology-lab",
    "IEEE Spectrum":       "https://spectrum.ieee.org/rss",
    "SemiAnalysis":        "https://www.semianalysis.com/feed",
    "Tom's Hardware":      "https://www.tomshardware.com/feeds/all",
    "AnandTech":           "https://www.anandtech.com/rss/",
    "DIGITIMES":           "https://www.digitimes.com/rss/daily.xml",
    "Nikkei Asia Tech":    "https://asia.nikkei.com/rss/feed/section/Technology",
}

KEYWORDS = [
    "ASML", "EUV", "DUV", "lithography", "immersion",
    "semiconductor", "chipmaker", "wafer", "fab",
    "TSMC", "Samsung Foundry", "Intel Foundry",
    "export control", "export ban", "entity list", "sanctions", "BIS",
    "Applied Materials", "Tokyo Electron", "Lam Research", "KLA",
    "advanced packaging", "HBM", "CoWoS", "3nm", "2nm",
    "NVIDIA", "AI chip", "China chip",
    "geopolitics", "trade war", "technology war",
]

CATEGORY_RULES = {
    "ASML 公司動態": lambda t: "asml" in t,
    "地緣政治 / 出口管制": lambda t: any(
        k in t for k in ["export", "sanction", "entity list", "bis ", "ban",
                         "restriction", "china chip", "trade war", "technology war"]
    ),
    "台積電 / 三星 / Intel": lambda t: any(
        k in t for k in ["tsmc", "samsung foundry", "intel foundry", "intel fab",
                         "taiwan semiconductor"]
    ),
    "EUV / 半導體設備": lambda t: any(
        k in t for k in ["euv", "duv", "lithography", "applied materials",
                         "tokyo electron", "lam research", "kla", "amat", " tel "]
    ),
    "其他半導體新聞": lambda t: True,
}


def fetch_news(hours: int = 24) -> list[dict]:
    cutoff = datetime.now() - timedelta(hours=hours)
    articles: list[dict] = []
    seen_titles: set[str] = set()

    for source, url in FEEDS.items():
        try:
            feed = feedparser.parse(url, request_headers={"User-Agent": "Mozilla/5.0"})
            for entry in feed.entries:
                published = None
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    published = datetime.fromtimestamp(time.mktime(entry.published_parsed))
                    if published < cutoff:
                        continue

                title = entry.get("title", "").strip()
                summary = re.sub(r"<[^>]+>", "", entry.get("summary", "")).strip()
                link = entry.get("link", "")

                if not title or title in seen_titles:
                    continue

                text = (title + " " + summary).lower()
                matched = [kw for kw in KEYWORDS if kw.lower() in text]
                if not matched:
                    continue

                seen_titles.add(title)
                articles.append({
                    "source": source,
                    "title": title,
                    "summary": summary[:350],
                    "link": link,
                    "published": published,
                    "keywords": matched[:4],
                })
        except Exception as exc:
            print(f"[warn] {source}: {exc}")

    articles.sort(key=lambda x: x["published"] or datetime.min, reverse=True)
    return articles


def categorize(articles: list[dict]) -> dict[str, list[dict]]:
    categories: dict[str, list[dict]] = {k: [] for k in CATEGORY_RULES}
    for article in articles:
        text = (article["title"] + " " + article["summary"]).lower()
        for cat, rule in CATEGORY_RULES.items():
            if rule(text):
                categories[cat].append(article)
                break
    return categories


def build_html(categories: dict[str, list[dict]], date_str: str) -> str:
    total = sum(len(v) for v in categories.values())
    cat_colors = {
        "ASML 公司動態":       "#0057b7",
        "地緣政治 / 出口管制":  "#c0392b",
        "台積電 / 三星 / Intel": "#27ae60",
        "EUV / 半導體設備":    "#8e44ad",
        "其他半導體新聞":       "#2c3e50",
    }

    html = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head><meta charset="UTF-8">
<style>
  body {{ font-family: 'Helvetica Neue', Arial, sans-serif; max-width: 760px;
         margin: 0 auto; padding: 20px; color: #333; background: #f5f5f5; }}
  .header {{ background: #1a1a2e; color: white; padding: 24px 28px;
             border-radius: 8px; margin-bottom: 20px; }}
  .header h1 {{ margin: 0 0 6px 0; font-size: 22px; }}
  .header p {{ margin: 0; color: #aaa; font-size: 13px; }}
  .section {{ margin-bottom: 24px; }}
  .section-title {{ font-size: 16px; font-weight: bold; color: white;
                    padding: 8px 14px; border-radius: 4px; margin-bottom: 10px; }}
  .card {{ background: white; border-radius: 6px; padding: 14px 16px;
           margin-bottom: 8px; box-shadow: 0 1px 3px rgba(0,0,0,.08);
           border-left: 4px solid #ddd; }}
  .card-meta {{ font-size: 11px; color: #999; margin-bottom: 4px; }}
  .card a {{ color: #1a1a2e; font-weight: 600; text-decoration: none; font-size: 14px; }}
  .card a:hover {{ text-decoration: underline; }}
  .card-summary {{ font-size: 12px; color: #666; margin: 6px 0 0 0; line-height: 1.5; }}
  .tag {{ display: inline-block; background: #eef; color: #556; font-size: 10px;
          padding: 1px 6px; border-radius: 10px; margin-right: 3px; }}
  .footer {{ text-align: center; color: #aaa; font-size: 11px; margin-top: 30px; }}
</style>
</head>
<body>
<div class="header">
  <h1>半導體產業日報</h1>
  <p>{date_str} &nbsp;|&nbsp; 共 {total} 則相關新聞 &nbsp;|&nbsp; ASML & 相關產業動態追蹤</p>
</div>
"""

    for cat, articles in categories.items():
        if not articles:
            continue
        color = cat_colors.get(cat, "#2c3e50")
        html += f'<div class="section">'
        html += f'<div class="section-title" style="background:{color}">{cat} ({len(articles)})</div>'

        for a in articles[:6]:
            date_display = a["published"].strftime("%m/%d %H:%M") if a["published"] else ""
            tags = "".join(f'<span class="tag">{kw}</span>' for kw in a["keywords"])
            html += f"""
<div class="card" style="border-left-color:{color}">
  <div class="card-meta">{a['source']} &nbsp;·&nbsp; {date_display} &nbsp; {tags}</div>
  <a href="{a['link']}" target="_blank">{a['title']}</a>
  <p class="card-summary">{a['summary']}</p>
</div>"""

        html += "</div>"

    html += f"""
<div class="footer">
  自動生成於 {datetime.now().strftime('%Y-%m-%d %H:%M')} UTC &nbsp;|&nbsp;
  來源：{', '.join(FEEDS.keys())}
</div>
</body></html>"""
    return html


def send_email(html_content: str, recipient: str, date_str: str) -> None:
    sender = os.environ["GMAIL_USER"]
    password = os.environ["GMAIL_APP_PASSWORD"]

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"📡 半導體日報 {date_str} — ASML & 產業動態"
    msg["From"] = f"半導體日報 <{sender}>"
    msg["To"] = recipient
    msg.attach(MIMEText(html_content, "html", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender, password)
        server.sendmail(sender, recipient, msg.as_string())
    print(f"Email sent → {recipient}")


if __name__ == "__main__":
    date_str = datetime.now().strftime("%Y-%m-%d")
    print(f"[{date_str}] Fetching semiconductor news...")

    articles = fetch_news(hours=24)
    print(f"Found {len(articles)} relevant articles")

    if not articles:
        print("No articles found, skipping email.")
    else:
        categories = categorize(articles)
        for cat, items in categories.items():
            print(f"  {cat}: {len(items)}")

        html = build_html(categories, date_str)

        recipient = os.environ.get("RECIPIENT_EMAIL") or os.environ["GMAIL_USER"]
        send_email(html, recipient, date_str)
