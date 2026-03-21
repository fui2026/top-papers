"""
Generate GitHub Pages Index
===========================
docs/ ディレクトリ内のダイジェスト Markdown ファイルを
一覧するインデックスページを生成する。
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

from pathlib import Path

REPO_ROOT = Path(__file__).parent
DOCS_DIR = REPO_ROOT / "docs"


def main():
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    # ダイジェストファイルを日付降順でリスト
    digests = sorted(DOCS_DIR.glob("digest_*.md"), reverse=True)

    lines = [
        "# Journal Club - Weekly Paper Digests",
        "",
        "トップジャーナル（Nature, Science, Cell 等）の最新論文を毎週自動収集しています。",
        "",
        "| Date | Digest |",
        "|------|--------|",
    ]

    for digest in digests:
        # ファイル名から日付を抽出: digest_2026-03-21.md -> 2026-03-21
        date_str = digest.stem.replace("digest_", "")
        lines.append(f"| {date_str} | [{digest.name}]({digest.name}) |")

    if not digests:
        lines.append("| - | No digests yet |")

    lines.append("")

    index_path = DOCS_DIR / "index.md"
    index_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Index generated: {index_path} ({len(digests)} digests)")


if __name__ == "__main__":
    main()
