"""
Post to X (Twitter)
===================
最新のダイジェスト JSON サマリーを読み取り、
X にスレッド形式で投稿する。

環境変数:
    X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_SECRET
    PAGES_URL (optional): GitHub Pages の URL
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

import json
import os
from pathlib import Path

import tweepy


SCRIPT_DIR = Path(__file__).parent
OUTPUT_DIR = SCRIPT_DIR / "output"


def get_latest_summary():
    """最新の JSON サマリーファイルを取得する。"""
    json_files = sorted(OUTPUT_DIR.glob("digest_*.json"))
    if not json_files:
        print("No digest JSON files found")
        sys.exit(1)
    latest = json_files[-1]
    print(f"Using: {latest.name}")
    with open(latest, encoding="utf-8") as f:
        return json.load(f)


def build_thread(summary, pages_url=""):
    """ダイジェストサマリーからツイートスレッドを構築する。

    各ツイートは 280 文字以内に収める。
    """
    tweets = []

    # Tweet 1: ヘッダー
    header = (
        f"Top Papers Weekly Digest\n"
        f"{summary['from_date']} ~ {summary['until_date']}\n\n"
        f"Today: {summary['total_papers']} research papers across top journals "
        f"(Nature, Science, Cell & more)\n"
    )
    if pages_url:
        header += f"\nFull digest: {pages_url}\n"
    header += "\nHighlights below"
    tweets.append(header)

    # Tweet 2-N: カテゴリ別ハイライト
    for cat in summary.get("categories", []):
        for h in cat["highlights"]:
            title = h["title"]
            # タイトルが長すぎる場合は切り詰め
            max_title_len = 180
            if len(title) > max_title_len:
                title = title[:max_title_len - 3] + "..."

            tweet = (
                f"[{h['journal']}]\n"
                f"{title}\n"
                f"- {h['authors']}\n"
            )
            if h.get("url"):
                tweet += f"{h['url']}"

            tweets.append(tweet)

    # 最終ツイート: フッター
    footer = (
        f"Full digest with abstracts:\n"
    )
    if pages_url:
        footer += f"{pages_url}\n\n"
    footer += "#AcademicTwitter #Science #Research"
    tweets.append(footer)

    return tweets


def post_thread(tweets):
    """tweepy を使って X にスレッドを投稿する。"""
    api_key = os.environ.get("X_API_KEY")
    api_secret = os.environ.get("X_API_SECRET")
    access_token = os.environ.get("X_ACCESS_TOKEN")
    access_secret = os.environ.get("X_ACCESS_SECRET")

    if not all([api_key, api_secret, access_token, access_secret]):
        print("X API credentials not set, skipping post")
        return False

    client = tweepy.Client(
        consumer_key=api_key,
        consumer_secret=api_secret,
        access_token=access_token,
        access_token_secret=access_secret,
    )

    # スレッド投稿
    prev_id = None
    for i, text in enumerate(tweets):
        if len(text) > 280:
            text = text[:277] + "..."
            print(f"  Warning: Tweet {i+1} truncated to 280 chars")

        resp = client.create_tweet(
            text=text,
            in_reply_to_tweet_id=prev_id,
        )
        prev_id = resp.data["id"]
        print(f"  Tweet {i+1}/{len(tweets)} posted (id: {prev_id})")

    return True


def main():
    summary = get_latest_summary()
    pages_url = os.environ.get("PAGES_URL", "")

    tweets = build_thread(summary, pages_url)

    # プレビュー表示
    print(f"\n--- Thread Preview ({len(tweets)} tweets) ---")
    for i, t in enumerate(tweets, 1):
        print(f"\n[Tweet {i}] ({len(t)} chars)")
        print(t)
    print("--- End Preview ---\n")

    # 投稿
    if post_thread(tweets):
        print("Thread posted successfully!")
    else:
        print("Thread not posted (credentials missing)")


if __name__ == "__main__":
    main()
