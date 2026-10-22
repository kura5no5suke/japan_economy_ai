import html
import os
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from email.utils import parsedate_to_datetime
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

import requests
from dotenv import load_dotenv


load_dotenv()

JST = ZoneInfo("Asia/Tokyo")

MAX_ITEMS = int(
    os.getenv(
        "MONEY_NEWS_MAX_ITEMS",
        "12",
    )
)

LOOKBACK_HOURS = int(
    os.getenv(
        "MONEY_NEWS_LOOKBACK_HOURS",
        "36",
    )
)

GOOGLE_NEWS_RSS = (
    "https://news.google.com/rss/search"
)

USER_AGENT = (
    "JapanEconomyMonitor/1.0 "
    "(money-news RSS reader)"
)

NEWS_QUERIES = [
    (
        "景気・物価",
        "日本 経済 景気 GDP CPI 物価 消費",
    ),
    (
        "金利・日銀",
        "日銀 金利 金融政策 住宅ローン 預金金利",
    ),
    (
        "為替",
        "ドル円 円相場 円安 円高 為替 日本",
    ),
    (
        "雇用・賃金",
        "日本 (賃金 OR 給与 OR 雇用 OR 失業率 OR 求人 OR 最低賃金 OR 春闘 OR 手取り)",
    ),
    (
        "株式・企業",
        "日経平均 TOPIX 株価 企業決算 設備投資 日本",
    ),
    (
        "税・社会保障",
        "税金 社会保険 年金 給付 補助金 日本",
    ),
    (
        "生活コスト",
        "日本 (食品 OR 値上げ OR ガソリン OR 電気料金 OR 電気代 OR ガス代 OR 生活費 OR 家計)",
    ),
    (
        "海外経済",
        "米国経済 中国経済 日本経済 影響",
    ),
]

RELEVANT_KEYWORDS = {
    "経済", "景気", "GDP", "国内総生産",
    "CPI", "物価", "インフレ", "デフレ",
    "消費", "小売", "家計", "賃金", "給与",
    "給料", "雇用", "失業", "求人", "春闘",
    "日銀", "日本銀行", "金利", "金融政策",
    "国債", "住宅ローン", "預金金利",
    "円相場", "ドル円", "円安", "円高", "為替",
    "日経平均", "TOPIX", "株価", "株式",
    "企業", "決算", "設備投資", "機械受注",
    "鉱工業生産", "生産", "輸出", "輸入",
    "貿易", "原油", "ガソリン", "電気料金",
    "値上げ", "値下げ", "食品", "税", "税金",
    "社会保険", "年金", "補助金", "給付",
    "米国経済", "中国経済", "FRB", "FOMC",
}

IMPORTANT_KEYWORDS = {
    "日銀", "日本銀行", "金融政策", "政策金利",
    "利上げ", "利下げ", "長期金利",
    "GDP", "国内総生産", "CPI", "消費者物価",
    "失業率", "雇用統計", "円急落", "円急騰",
    "為替介入", "日経平均", "暴落", "急落",
    "急騰", "景気後退", "リセッション",
    "経済対策", "税制改正", "社会保険料",
}

NORMAL_KEYWORDS = {
    "賃金", "給与", "給料", "消費", "小売",
    "企業決算", "決算", "設備投資",
    "鉱工業生産", "機械受注", "輸出", "輸入",
    "原油", "ガソリン", "電気料金", "値上げ",
    "住宅ローン", "預金金利", "株価", "TOPIX",
    "円安", "円高", "ドル円", "為替",
    "物価", "インフレ",
}


def clean_html(text):
    text = html.unescape(text or "")
    text = re.sub(
        r"<[^>]+>",
        " ",
        text,
    )
    text = re.sub(
        r"\s+",
        " ",
        text,
    )
    return text.strip()


def normalize_title(title):
    text = clean_html(title).lower()
    text = re.sub(
        r"\s*[-－—|｜]\s*[^-－—|｜]{1,30}$",
        "",
        text,
    )
    text = re.sub(
        r"[^\w一-龥ぁ-んァ-ヶー]",
        "",
        text,
    )
    return text


def remove_source_suffix(title, source):
    title = clean_html(title)
    source = clean_html(source)

    if not source:
        return title

    suffixes = [
        f" - {source}",
        f"－{source}",
        f" — {source}",
        f" | {source}",
        f"｜{source}",
    ]

    for suffix in suffixes:
        if title.endswith(suffix):
            return title[:-len(suffix)].strip()

    return title


def parse_pub_date(value):
    if not value:
        return None

    try:
        dt = parsedate_to_datetime(value)
    except (
        TypeError,
        ValueError,
        OverflowError,
    ):
        return None

    if dt.tzinfo is None:
        dt = dt.replace(
            tzinfo=timezone.utc
        )

    return dt.astimezone(JST)


def is_recent(pub_dt):
    if pub_dt is None:
        return True

    cutoff = (
        datetime.now(JST)
        - timedelta(
            hours=LOOKBACK_HOURS
        )
    )

    return pub_dt >= cutoff



NON_NEWS_TITLE_PATTERNS = (
    "リアルタイム表示",
    "レート・チャート",
    "為替レート・チャート",
    "株価・チャート",
    "リアルタイムチャート",
)


def is_probably_news(item):
    title = clean_html(
        item.get("title", "")
    )

    if not title:
        return False

    return not any(
        pattern in title
        for pattern in NON_NEWS_TITLE_PATTERNS
    )



FOREIGN_COUNTRY_TERMS = {
    "チリ", "フランス", "ドイツ", "イタリア", "スペイン",
    "英国", "イギリス", "韓国", "中国", "台湾", "香港",
    "インド", "ブラジル", "メキシコ", "カナダ",
    "オーストラリア", "ロシア", "トルコ",
}

JAPAN_DOMESTIC_TERMS = {
    "日本の", "日本で", "日本では", "国内", "厚生労働省",
    "厚労省", "総務省", "日本企業", "春闘",
    "最低賃金", "実質賃金", "毎月勤労統計",
    "完全失業率", "有効求人倍率", "日銀", "日本銀行",
    "日経平均", "TOPIX", "消費者物価", "家計調査",
    "電気料金", "ガソリン価格", "消費税",
    "社会保険", "年金",
}



JAPAN_REGION_TERMS = {
    "北海道", "青森", "岩手", "宮城", "秋田", "山形", "福島",
    "茨城", "栃木", "群馬", "埼玉", "千葉", "東京", "神奈川",
    "新潟", "富山", "石川", "福井", "山梨", "長野", "岐阜",
    "静岡", "愛知", "三重", "滋賀", "京都", "大阪", "兵庫",
    "奈良", "和歌山", "鳥取", "島根", "岡山", "広島", "山口",
    "徳島", "香川", "愛媛", "高知", "福岡", "佐賀", "長崎",
    "熊本", "大分", "宮崎", "鹿児島", "沖縄",
}

JAPAN_SYSTEM_TERMS = {
    "厚生労働省", "厚労省", "総務省", "財務省", "内閣府",
    "日銀", "日本銀行", "国税庁", "年金機構",
    "春闘", "最低賃金", "実質賃金", "完全失業率",
    "有効求人倍率", "毎月勤労統計", "消費者物価",
    "家計調査", "日経平均", "TOPIX",
    "消費税", "社会保険", "年金", "住宅ローン",
    "電気料金", "ガソリン価格",
}


def has_japan_domestic_signal(item):
    title = clean_html(
        item.get("title", "")
    )

    direct_terms = {
        "日本", "国内", "日本企業",
        "日本経済", "日本人",
    }

    if any(
        term in title
        for term in direct_terms
    ):
        return True

    if any(
        term in title
        for term in JAPAN_REGION_TERMS
    ):
        return True

    if any(
        term in title
        for term in JAPAN_SYSTEM_TERMS
    ):
        return True

    return False


def domestic_category_needs_signal(item):
    return item["category"] in {
        "雇用・賃金",
        "生活コスト",
        "税・社会保障",
    }


def looks_foreign_only(item):
    if item["category"] not in {
        "雇用・賃金",
        "生活コスト",
        "景気・物価",
        "税・社会保障",
    }:
        return False

    title = clean_html(
        item.get("title", "")
    )

    has_foreign = any(
        term in title
        for term in FOREIGN_COUNTRY_TERMS
    )

    if not has_foreign:
        return False

    has_japan_domestic = any(
        term in title
        for term in JAPAN_DOMESTIC_TERMS
    )

    return not has_japan_domestic


def is_relevant(item):
    if not is_probably_news(item):
        return False

    if looks_foreign_only(item):
        return False

    if (
        domestic_category_needs_signal(item)
        and not has_japan_domestic_signal(item)
    ):
        return False

    text = (
        f"{item['title']} "
        f"{item['description']} "
        f"{item['category']}"
    )

    text_lower = text.lower()

    if not any(
        keyword.lower() in text_lower
        for keyword in RELEVANT_KEYWORDS
    ):
        return False

    if item["category"] == "海外経済":
        japan_terms = {
            "日本", "円", "日経", "輸出", "輸入",
            "日本企業", "日本経済", "為替",
        }
        money_terms = {
            "経済", "景気", "GDP", "金利", "物価",
            "株", "市場", "貿易", "原油", "ドル",
            "FRB", "FOMC",
        }

        has_japan = any(
            term.lower() in text_lower
            for term in japan_terms
        )
        has_money = any(
            term.lower() in text_lower
            for term in money_terms
        )

        return has_japan and has_money

    return True


def importance_level(item):
    text = (
        f"{item['title']} "
        f"{item['description']}"
    )

    if any(
        keyword.lower() in text.lower()
        for keyword in IMPORTANT_KEYWORDS
    ):
        return "important"

    if any(
        keyword.lower() in text.lower()
        for keyword in NORMAL_KEYWORDS
    ):
        return "normal"

    return "reference"


def importance_label(level):
    return {
        "important": "🔥 重要",
        "normal": "🟡 通常",
        "reference": "⚪ 参考",
    }.get(
        level,
        "⚪ 参考",
    )


def fetch_google_news(
    category,
    query,
):
    params = {
        "q": f"{query} when:1d",
        "hl": "ja",
        "gl": "JP",
        "ceid": "JP:ja",
    }

    url = (
        GOOGLE_NEWS_RSS
        + "?"
        + urlencode(params)
    )

    response = requests.get(
        url,
        headers={
            "User-Agent": USER_AGENT,
        },
        timeout=30,
    )
    response.raise_for_status()

    root = ET.fromstring(
        response.content
    )

    items = []

    for node in root.findall(
        "./channel/item"
    ):
        title = clean_html(
            node.findtext(
                "title",
                default="",
            )
        )

        link = clean_html(
            node.findtext(
                "link",
                default="",
            )
        )

        description = clean_html(
            node.findtext(
                "description",
                default="",
            )
        )

        pub_date = parse_pub_date(
            node.findtext(
                "pubDate",
                default="",
            )
        )

        source_node = node.find(
            "source"
        )

        source = (
            clean_html(
                source_node.text
            )
            if (
                source_node is not None
                and source_node.text
            )
            else ""
        )

        title = remove_source_suffix(
            title,
            source,
        )

        if not title or not link:
            continue

        item = {
            "title": title,
            "link": link,
            "description": description,
            "source": source or "Google News",
            "published_at": pub_date,
            "category": category,
        }

        if not is_recent(pub_date):
            continue

        if not is_relevant(item):
            continue

        item["importance"] = (
            importance_level(item)
        )

        items.append(item)

    return items


def title_similarity(a, b):
    a_norm = normalize_title(a)
    b_norm = normalize_title(b)

    if not a_norm or not b_norm:
        return 0.0

    if (
        a_norm in b_norm
        or b_norm in a_norm
    ):
        shorter = min(
            len(a_norm),
            len(b_norm),
        )
        longer = max(
            len(a_norm),
            len(b_norm),
        )

        if longer > 0:
            ratio = shorter / longer

            if ratio >= 0.70:
                return 1.0

    return SequenceMatcher(
        None,
        a_norm,
        b_norm,
    ).ratio()



TOPIC_GROUPS = [
    {
        "name": "ドル円",
        "keywords": {
            "ドル", "円", "ドル円", "円高", "円安",
            "東京外為", "外為", "為替",
        },
    },
    {
        "name": "日本株",
        "keywords": {
            "日経平均", "日本株", "TOPIX", "東京株",
            "株価", "株安", "株高",
        },
    },
    {
        "name": "日銀",
        "keywords": {
            "日銀", "日本銀行", "政策金利",
            "利上げ", "利下げ", "金融政策",
        },
    },
    {
        "name": "物価",
        "keywords": {
            "CPI", "消費者物価", "物価",
            "インフレ", "値上げ",
        },
    },
    {
        "name": "雇用賃金",
        "keywords": {
            "賃金", "給与", "給料", "雇用",
            "失業率", "求人", "最低賃金", "春闘",
        },
    },
]


def detect_topic(title):
    text = clean_html(title).lower()

    best_name = None
    best_hits = 0

    for group in TOPIC_GROUPS:
        hits = sum(
            1
            for keyword in group["keywords"]
            if keyword.lower() in text
        )

        if hits > best_hits:
            best_hits = hits
            best_name = group["name"]

    if best_hits == 0:
        return None

    return best_name


def same_event_window(a, b):
    a_dt = a.get("published_at")
    b_dt = b.get("published_at")

    if not a_dt or not b_dt:
        return True

    return abs(
        (a_dt - b_dt).total_seconds()
    ) <= 8 * 60 * 60


def topic_duplicate(a, b):
    topic_a = detect_topic(a["title"])
    topic_b = detect_topic(b["title"])

    if (
        not topic_a
        or not topic_b
        or topic_a != topic_b
    ):
        return False

    if not same_event_window(a, b):
        return False

    # For broad market topics, require some textual similarity too.
    similarity = title_similarity(
        a["title"],
        b["title"],
    )

    if topic_a in {"ドル円", "日本株"}:
        return similarity >= 0.42

    return similarity >= 0.50


def deduplicate_news(items):
    def sort_key(item):
        pub = (
            item["published_at"]
            or datetime.min.replace(
                tzinfo=JST
            )
        )
        return pub

    ordered = sorted(
        items,
        key=sort_key,
        reverse=True,
    )

    unique = []

    for item in ordered:
        duplicate = False

        for saved in unique:
            if (
                title_similarity(
                    item["title"],
                    saved["title"],
                ) >= 0.82
                or topic_duplicate(
                    item,
                    saved,
                )
            ):
                duplicate = True
                break

        if not duplicate:
            unique.append(item)

    return unique


def select_balanced_items(
    items,
    max_items=MAX_ITEMS,
):
    importance_order = {
        "important": 0,
        "normal": 1,
        "reference": 2,
    }

    # Newer items first inside the same importance level.
    ordered = sorted(
        items,
        key=lambda item: (
            importance_order[
                item["importance"]
            ],
            -(
                item["published_at"].timestamp()
                if item["published_at"]
                else 0
            ),
        ),
    )

    selected = []
    topic_counts = {}
    category_counts = {}

    # Broad market themes can otherwise dominate the whole report.
    topic_limits = {
        "ドル円": 2,
        "日本株": 2,
        "日銀": 2,
        "物価": 2,
        "雇用賃金": 2,
    }

    # First pass: favor category diversity.
    for item in ordered:
        if len(selected) >= max_items:
            break

        category = item["category"]

        if category_counts.get(
            category,
            0,
        ) >= 2:
            continue

        topic = detect_topic(
            item["title"]
        )

        if (
            topic in topic_limits
            and topic_counts.get(
                topic,
                0,
            ) >= topic_limits[topic]
        ):
            continue

        selected.append(item)

        category_counts[category] = (
            category_counts.get(
                category,
                0,
            )
            + 1
        )

        if topic:
            topic_counts[topic] = (
                topic_counts.get(
                    topic,
                    0,
                )
                + 1
            )

    selected_ids = {
        id(item)
        for item in selected
    }

    # Second pass: fill remaining space, while still respecting topic caps.
    for item in ordered:
        if len(selected) >= max_items:
            break

        if id(item) in selected_ids:
            continue

        topic = detect_topic(
            item["title"]
        )

        if (
            topic in topic_limits
            and topic_counts.get(
                topic,
                0,
            ) >= topic_limits[topic]
        ):
            continue

        selected.append(item)
        selected_ids.add(
            id(item)
        )

        if topic:
            topic_counts[topic] = (
                topic_counts.get(
                    topic,
                    0,
                )
                + 1
            )

    return selected[:max_items]


def collect_money_news(
    max_items=MAX_ITEMS,
):
    print(
        "===== お金・経済ニュース取得 ====="
    )

    all_items = []
    errors = []

    for category, query in NEWS_QUERIES:
        try:
            fetched = (
                fetch_google_news(
                    category,
                    query,
                )
            )

            print(
                f"{category}: "
                f"{len(fetched)}件取得"
            )

            all_items.extend(
                fetched
            )

        except (
            requests.RequestException,
            ET.ParseError,
        ) as exc:
            errors.append(
                f"{category}: {exc}"
            )
            print(
                f"{category}: 取得失敗"
            )

        time.sleep(0.15)

    unique = deduplicate_news(
        all_items
    )

    selected = (
        select_balanced_items(
            unique,
            max_items=max_items,
        )
    )

    print(
        "候補:",
        len(all_items),
        "重複除去後:",
        len(unique),
        "掲載:",
        len(selected),
    )

    print(
        "AI要約: 使用しません（API料金 0円）"
    )

    return {
        "items": selected,
        "errors": errors,
        "generated_at": datetime.now(
            JST
        ),
    }


def format_news_item(
    item,
    index,
):
    pub = item.get(
        "published_at"
    )

    if pub:
        time_text = (
            pub.strftime(
                "%m/%d %H:%M"
            )
        )
    else:
        time_text = "時刻不明"

    title = item["title"]

    if len(title) > 120:
        title = title[:119] + "…"

    return (
        f"**{index}. {title}**\n"
        f"`{item['category']} | "
        f"{item['source']} | "
        f"{time_text}` "
        f"[記事]({item['link']})"
    )


def build_news_sections(items):
    groups = [
        (
            "important",
            "🔥 重要ニュース",
        ),
        (
            "normal",
            "🟡 通常ニュース",
        ),
        (
            "reference",
            "⚪ その他・参考",
        ),
    ]

    blocks = []
    index = 1

    for level, heading in groups:
        rows = [
            item
            for item in items
            if item[
                "importance"
            ] == level
        ]

        if not rows:
            continue

        section = [
            f"**{heading}**"
        ]

        for item in rows:
            section.append(
                format_news_item(
                    item,
                    index,
                )
            )
            index += 1

        blocks.append(
            "\n\n".join(section)
        )

    return blocks


def split_sections_for_discord(
    sections,
    max_chars=3600,
):
    chunks = []
    current = ""

    for section in sections:
        candidate = (
            section
            if not current
            else current
            + "\n\n"
            + section
        )

        if (
            len(candidate)
            <= max_chars
        ):
            current = candidate
            continue

        if current:
            chunks.append(
                current
            )

        current = section

    if current:
        chunks.append(
            current
        )

    return chunks[:2]


def build_discord_news_embeds(
    result,
    color=0x3498DB,
):
    items = result.get(
        "items",
        []
    )

    if not items:
        return [
            {
                "title": (
                    "📰 今日のお金・経済ニュース"
                ),
                "description": (
                    "直近の対象時間内で、"
                    "掲載できるニュースを取得できませんでした。"
                ),
                "color": color,
            }
        ]

    sections = (
        build_news_sections(
            items
        )
    )

    chunks = (
        split_sections_for_discord(
            sections
        )
    )

    embeds = []

    for index, chunk in enumerate(
        chunks
    ):
        if index == 0:
            title = (
                "📰 今日のお金・経済ニュース"
            )
        else:
            title = (
                "🗞 お金・経済ニュース｜続き"
            )

        embed = {
            "title": title,
            "description": chunk,
            "color": color,
        }

        if index == len(chunks) - 1:
            embed["footer"] = {
                "text": (
                    "Google News RSSから取得・重複除去 | "
                    "AI要約なし | "
                    "重要度にかかわらず幅広く掲載"
                )
            }

        embeds.append(
            embed
        )

    return embeds


def get_money_news_embeds():
    try:
        result = (
            collect_money_news()
        )

        return (
            build_discord_news_embeds(
                result
            )
        )

    except Exception as exc:
        print(
            "ニュース機能全体エラー:",
            exc,
        )

        return [
            {
                "title": (
                    "📰 今日のお金・経済ニュース"
                ),
                "description": (
                    "ニュース取得中にエラーが発生しました。"
                    "経済監視レポート本体は通常どおり送信します。"
                ),
                "color": 0x95A5A6,
            }
        ]


def main():
    result = collect_money_news()

    print()
    print(
        "===== 掲載ニュース ====="
    )

    for index, item in enumerate(
        result["items"],
        start=1,
    ):
        print(
            f"{index}. "
            f"{importance_label(item['importance'])} "
            f"[{item['category']}] "
            f"{item['title']}"
        )
        print(
            "   出典:",
            item["source"],
        )
        print(
            "   URL:",
            item["link"],
        )
        print()


if __name__ == "__main__":
    main()
