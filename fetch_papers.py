"""
Top Papers Weekly Digest
========================
トップジャーナル（Nature, Science, Cell 等）の過去2週間の論文を
CrossRef API 経由で取得し、Markdown レポートとして出力する。

Usage:
    python fetch_papers.py                  # デフォルト設定で実行
    python fetch_papers.py --days 7         # 過去7日間
    python fetch_papers.py --category top3  # 三大誌のみ
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

import argparse
import datetime
import json
import re
import time
from pathlib import Path

import requests
import yaml


CROSSREF_API = "https://api.crossref.org/journals/{issn}/works"
CROSSREF_MAILTO = "journal-club-digest@example.com"  # Polite pool 用

SCRIPT_DIR = Path(__file__).parent
CONFIG_PATH = SCRIPT_DIR / "config.yaml"
OUTPUT_DIR = SCRIPT_DIR / "output"


def load_config():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def fetch_journal_papers(issn, journal_name, from_date, until_date, max_results=30):
    """CrossRef API から特定ジャーナルの論文を取得する。

    type=journal-article フィルタで原著論文のみを取得。
    一部のジャーナルは日付を年-月のみで登録するため、
    from_date を月初に拡張してフェッチし、後でフィルタする。
    """
    # 月初に拡張 (Cell等の年-月のみ登録ジャーナル対策)
    from_date_expanded = from_date[:8] + "01"

    params = {
        "filter": f"from-pub-date:{from_date_expanded},until-pub-date:{until_date},type:journal-article",
        "rows": max_results,
        "sort": "published",
        "order": "desc",
        "select": "DOI,title,author,published,abstract,type,subject,is-referenced-by-count",
        "mailto": CROSSREF_MAILTO,
    }

    try:
        resp = requests.get(
            CROSSREF_API.format(issn=issn),
            params=params,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        items = data.get("message", {}).get("items", [])
        print(f"  {journal_name}: {len(items)} papers found")
        return items
    except requests.RequestException as e:
        print(f"  {journal_name}: ERROR - {e}")
        return []


def parse_paper(item):
    """CrossRef のレスポンスアイテムを整形する。"""
    # タイトル
    title_list = item.get("title", [])
    title = title_list[0] if title_list else "(No title)"

    # 著者
    authors_raw = item.get("author", [])
    if authors_raw:
        first = authors_raw[0]
        first_name = f"{first.get('family', '')}"
        if first.get("given"):
            first_name = f"{first['given']} {first_name}"
        if len(authors_raw) > 1:
            authors = f"{first_name} et al."
        else:
            authors = first_name
    else:
        authors = "(Unknown)"

    # 発行日
    pub_parts = item.get("published", {}).get("date-parts", [[None]])
    date_parts = pub_parts[0] if pub_parts else [None]
    if len(date_parts) >= 3 and all(date_parts[:3]):
        pub_date = f"{date_parts[0]}-{date_parts[1]:02d}-{date_parts[2]:02d}"
    elif len(date_parts) >= 2 and all(date_parts[:2]):
        pub_date = f"{date_parts[0]}-{date_parts[1]:02d}"
    elif date_parts and date_parts[0]:
        pub_date = str(date_parts[0])
    else:
        pub_date = "N/A"

    # DOI
    doi = item.get("DOI", "")

    # アブストラクト (HTML タグ・余分な空白・参照番号を除去)
    abstract = item.get("abstract", "")
    if abstract:
        abstract = re.sub(r"<[^>]+>", "", abstract)  # HTMLタグ除去
        abstract = re.sub(r"\s+", " ", abstract).strip()  # 余分な空白を正規化
        abstract = re.sub(r"\s*\d+(?:,\d+)*(?:–\d+)?\s*(?=[\.,;]|$)", "", abstract)  # 参照番号除去
        # 長すぎる場合は切り詰め
        if len(abstract) > 500:
            abstract = abstract[:497] + "..."

    # 被引用数
    citations = item.get("is-referenced-by-count", 0)

    # 論文タイプ
    paper_type = item.get("type", "unknown")

    # Nature系のニュース/コメント記事を判別
    # d41586 = News/Comment, s41586 = Research Article
    is_news = False
    if doi:
        if re.search(r"/d\d{5}-", doi):
            is_news = True

    # タイトルから Correction/Erratum/Retraction を判別
    title_lower = title.lower()
    is_correction = any(
        kw in title_lower
        for kw in ("correction:", "author correction:", "erratum:", "retraction:", "editorial expression of concern")
    )

    return {
        "title": title,
        "authors": authors,
        "pub_date": pub_date,
        "doi": doi,
        "url": f"https://doi.org/{doi}" if doi else "",
        "abstract": abstract,
        "citations": citations,
        "type": paper_type,
        "is_news": is_news,
        "is_correction": is_correction,
    }


def generate_report(all_papers, config, from_date, until_date):
    """Markdown レポートを生成する。"""
    today = datetime.date.today().isoformat()
    lines = []

    lines.append(f"# Top Papers Weekly Digest")
    lines.append(f"")
    lines.append(f"**生成日:** {today}  ")
    lines.append(f"**対象期間:** {from_date} ~ {until_date}  ")
    lines.append(f"")

    # 統計サマリー
    total = sum(len(papers) for papers in all_papers.values())
    lines.append(f"**総論文数:** {total}  ")
    lines.append(f"")
    lines.append(f"---")
    lines.append(f"")

    # カテゴリ順に出力
    category_order = config.get("category_order", [])
    category_labels = {
        "top3": "Nature / Science / Cell (三大誌)",
        "nature_family": "Nature 姉妹誌",
        "cell_family": "Cell 姉妹誌",
        "medical": "医学系トップジャーナル",
    }

    # ジャーナルをカテゴリ別にグループ化
    journal_categories = {}
    for j in config["journals"]:
        cat = j.get("category", "other")
        if cat not in journal_categories:
            journal_categories[cat] = []
        journal_categories[cat].append(j["name"])

    for cat in category_order:
        journal_names = journal_categories.get(cat, [])
        cat_papers = []
        for name in journal_names:
            cat_papers.extend(
                [(name, p) for p in all_papers.get(name, [])]
            )

        if not cat_papers:
            continue

        label = category_labels.get(cat, cat)
        lines.append(f"## {label}")
        lines.append(f"")

        # ジャーナルごとにグループ
        for journal_name in journal_names:
            papers = all_papers.get(journal_name, [])
            if not papers:
                continue

            # 原著論文のみ (ニュース記事・修正・撤回を除外)
            research_papers = [
                p for p in papers
                if p["type"] in ("journal-article", "article", "unknown")
                and not p.get("is_news", False)
                and not p.get("is_correction", False)
            ]

            lines.append(f"### {journal_name} ({len(research_papers)} papers)")
            lines.append(f"")

            for i, p in enumerate(research_papers, 1):
                lines.append(f"**{i}. {p['title']}**  ")
                lines.append(f"*{p['authors']}* | {p['pub_date']}")
                if p["citations"]:
                    lines.append(f" | Citations: {p['citations']}")
                lines.append(f"  ")
                if p["url"]:
                    lines.append(f"DOI: [{p['doi']}]({p['url']})  ")
                if p["abstract"] and config["output"].get("include_abstract", True):
                    lines.append(f"")
                    lines.append(f"> {p['abstract']}")
                lines.append(f"")

            lines.append(f"---")
            lines.append(f"")

    return "\n".join(lines)


def generate_json_summary(all_papers, config, from_date, until_date):
    """X 投稿用の JSON サマリーを生成する。

    カテゴリごとにトップ2論文を抽出し、コンパクトな構造で出力する。
    """
    category_order = config.get("category_order", [])
    category_labels = {
        "top3": "Nature / Science / Cell",
        "nature_family": "Nature 姉妹誌",
        "cell_family": "Cell 姉妹誌",
        "medical": "医学系トップ",
    }

    journal_categories = {}
    for j in config["journals"]:
        cat = j.get("category", "other")
        if cat not in journal_categories:
            journal_categories[cat] = []
        journal_categories[cat].append(j["name"])

    # 全原著論文数を計算
    total_research = 0
    categories_summary = []

    for cat in category_order:
        journal_names = journal_categories.get(cat, [])
        cat_highlights = []

        for journal_name in journal_names:
            papers = all_papers.get(journal_name, [])
            research = [
                p for p in papers
                if p["type"] in ("journal-article", "article", "unknown")
                and not p.get("is_news", False)
                and not p.get("is_correction", False)
            ]
            total_research += len(research)
            for p in research[:1]:  # 各ジャーナルからトップ1
                cat_highlights.append({
                    "journal": journal_name,
                    "title": p["title"],
                    "authors": p["authors"],
                    "doi": p["doi"],
                    "url": p["url"],
                })

        if cat_highlights:
            categories_summary.append({
                "category": cat,
                "label": category_labels.get(cat, cat),
                "highlights": cat_highlights[:3],  # カテゴリあたり最大3
            })

    return {
        "generated": datetime.date.today().isoformat(),
        "from_date": from_date,
        "until_date": until_date,
        "total_papers": total_research,
        "categories": categories_summary,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Top Papers Weekly Digest - トップジャーナル論文ダイジェスト"
    )
    parser.add_argument(
        "--days", type=int, default=None,
        help="検索対象の日数 (デフォルト: config.yaml の lookback_days)"
    )
    parser.add_argument(
        "--category", type=str, default=None,
        help="特定カテゴリのみ取得 (例: top3, nature_family)"
    )
    parser.add_argument(
        "--output", type=str, default=None,
        help="出力ファイルパス (デフォルト: output/digest_YYYY-MM-DD.md)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="API を呼ばずに設定を確認するだけ"
    )
    args = parser.parse_args()

    # 設定読み込み
    config = load_config()
    lookback = args.days or config.get("lookback_days", 14)

    until_date = datetime.date.today().isoformat()
    from_date = (datetime.date.today() - datetime.timedelta(days=lookback)).isoformat()

    print(f"Top Papers Weekly Digest")
    print(f"対象期間: {from_date} ~ {until_date}")
    print(f"")

    # 対象ジャーナル
    journals = config["journals"]
    if args.category:
        journals = [j for j in journals if j.get("category") == args.category]

    if args.dry_run:
        print("--- DRY RUN ---")
        for j in journals:
            print(f"  [{j.get('category')}] {j['name']} (ISSN: {j['issn']})")
        return

    max_papers = config["output"].get("max_papers_per_journal", 30)

    # ジャーナルごとに取得
    all_papers = {}
    for j in journals:
        items = fetch_journal_papers(
            j["issn"], j["name"], from_date, until_date, max_papers
        )
        parsed = [parse_paper(item) for item in items]
        all_papers[j["name"]] = parsed
        # CrossRef の Rate limit 配慮 (polite pool でも間隔を空ける)
        time.sleep(1.0)

    # レポート生成
    report = generate_report(all_papers, config, from_date, until_date)

    # 出力
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if args.output:
        out_path = Path(args.output)
    else:
        out_path = OUTPUT_DIR / f"digest_{until_date}.md"

    out_path.write_text(report, encoding="utf-8")
    print(f"")
    print(f"Report saved: {out_path}")

    # JSON サマリー出力 (X 投稿用)
    summary = generate_json_summary(all_papers, config, from_date, until_date)
    json_path = out_path.with_suffix(".json")
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"JSON summary saved: {json_path}")

    # 統計表示
    print(f"Total research papers: {summary['total_papers']}")


if __name__ == "__main__":
    main()
