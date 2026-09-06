"""
デイトレード用スクリーニング②「業績修正インパクト分析」用: JPXが公開する
「決算発表予定日」一覧（Excel）を取得し、data/master/earnings_calendar.csv に出力する。

一覧ページには、決算期末を迎えた直近数ヶ月分のコホートごとにExcelファイルが
分かれて掲載されており（例: 6月期末コホート・7月期末コホート）、ファイル名は
更新日を含むため固定URLでは取れない（fetch_margin_list.pyと同じ理由）。
掲載されているファイルを全て取得して結合する。JPXはこのページを毎営業日
17時頃を目処に更新している。

貸借銘柄・市場区分による絞り込みはこの時点では行わない
（screen_daytrade2.py側でmargin_list.csvと突き合わせて行う）。

出力: data/master/earnings_calendar.csv (code, name, market, sector, fiscal_year_end,
      quarter_type, announcement_date)
"""

import io
import re
import sys
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
MASTER_DIR = ROOT / "data" / "master"

INDEX_URL = "https://www.jpx.co.jp/listing/event-schedules/financial-announcement/index.html"


def find_list_urls() -> list[str]:
    res = requests.get(INDEX_URL, timeout=60)
    res.raise_for_status()
    matches = re.findall(r'href="([^"]+/kessan[^"]+\.xlsx)"', res.text)
    if not matches:
        raise SystemExit(
            f"ERROR: {INDEX_URL} 内に決算発表予定日一覧xlsxへのリンクが見つかりません。"
            "JPX側でページ構成が変わった可能性があります。"
        )
    return sorted({m if m.startswith("http") else f"https://www.jpx.co.jp{m}" for m in matches})


def fetch_one(url: str) -> pd.DataFrame:
    res = requests.get(url, timeout=60)
    res.raise_for_status()
    df = pd.read_excel(io.BytesIO(res.content), sheet_name="List", header=4,
                       dtype={"コード\nCode": str})
    return df


def build_calendar(frames: list[pd.DataFrame]) -> pd.DataFrame:
    df = pd.concat(frames, ignore_index=True)
    df = df.rename(columns={
        "決算発表予定日\nScheduled Dates for Earnings Announcements": "announcement_date",
        "コード\nCode": "code",
        "会社名": "name",
        "決算期末\nFiscal Year-end": "fiscal_year_end",
        "業種名": "sector33",
        "種別": "quarter_type",
        "市場区分": "market",
    })
    keep = ["announcement_date", "code", "name", "fiscal_year_end", "sector33",
            "quarter_type", "market"]
    df = df[[c for c in keep if c in df.columns]].copy()
    df["code"] = df["code"].astype(str).str.strip()
    df = df[df["code"].str.len() == 4]
    df["announcement_date"] = pd.to_datetime(df["announcement_date"], errors="coerce")
    df = df[df["announcement_date"].notna()]
    # 同一銘柄が複数コホートファイルに重複して載ることがあるため、コード+発表予定日で重複排除
    df = df.drop_duplicates(subset=["code", "announcement_date"])
    df = df.sort_values(["announcement_date", "code"]).reset_index(drop=True)
    return df


def main() -> int:
    print(f"一覧ページを取得します... ({INDEX_URL})")
    urls = find_list_urls()
    print(f"  対象ファイル: {len(urls)}件")

    frames = []
    for url in urls:
        print(f"  -> {url}")
        frames.append(fetch_one(url))

    calendar = build_calendar(frames)
    if calendar.empty:
        print("ERROR: 決算発表予定日を1件も取得できませんでした。列名が変わった可能性があります。",
              file=sys.stderr)
        return 1

    MASTER_DIR.mkdir(parents=True, exist_ok=True)
    out = MASTER_DIR / "earnings_calendar.csv"
    calendar.to_csv(out, index=False, encoding="utf-8-sig")

    print(f"決算発表予定日: {len(calendar)}件 "
          f"({calendar['announcement_date'].min().date()} 〜 {calendar['announcement_date'].max().date()}) "
          f"-> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
