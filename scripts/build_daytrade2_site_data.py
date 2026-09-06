"""
デイトレード用スクリーニング②「決算発表カレンダー」の結果を閲覧UI用のJSONに変換する。

output/ の最新の daytrade2_*.csv / daytrade2_summary_*.json を読み、
app/earnings-calendar/data/latest.json に書き出す。無料公開ページのため
private-data/への分離は行わない（swing-implied-growthと同じ設計）。

使い方:
    python3 scripts/build_daytrade2_site_data.py
"""

import json
import math
import sys

import pandas as pd

from config import OUTPUT_DIR, ROOT

SITE_DATA = ROOT / "app" / "earnings-calendar" / "data"

NUMERIC_COLS = {
    "operating_income": 0,
    "roe_pct": 2,
    "eps": 2,
}
TEXT_COLS = ["announcement_date", "sec_code", "name", "market", "sector33",
            "quarter_type", "fiscal_year_end", "period_end"]


def clean(value, digits: int):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    return round(float(value), digits)


def main() -> int:
    screenings = sorted(OUTPUT_DIR.glob("daytrade2_[0-9]*.csv"))
    summaries = sorted(OUTPUT_DIR.glob("daytrade2_summary_*.json"))
    if not screenings or not summaries:
        print("ERROR: output/ に決算発表カレンダーの結果がありません。先に "
              "screen_daytrade2.py を実行してください。", file=sys.stderr)
        return 1

    latest_csv, latest_json = screenings[-1], summaries[-1]
    df = pd.read_csv(latest_csv, dtype={"sec_code": str})
    summary = json.loads(latest_json.read_text(encoding="utf-8"))

    stocks = []
    for r in df.to_dict("records"):
        row = {c: (None if pd.isna(r.get(c)) else r.get(c)) for c in TEXT_COLS}
        for col, digits in NUMERIC_COLS.items():
            row[col] = clean(r.get(col), digits)
        stocks.append(row)

    # 発表予定日が近い順（初期表示順であって推奨ではない）
    stocks.sort(key=lambda s: (s["announcement_date"] is None, s["announcement_date"]))

    payload = {
        "as_of": summary["基準日"],
        "universe_label": summary["対象ユニバース"],
        "counts": {
            "calendar_total": summary["決算発表予定日_取得件数"],
            "listed": summary["掲載件数"],
            "not_evaluable": summary["算出不能により対象外"],
        },
        "date_range": summary["発表予定日の範囲"],
        "stocks": stocks,
    }

    SITE_DATA.mkdir(parents=True, exist_ok=True)
    out = SITE_DATA / "latest.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"{latest_csv.name} + {latest_json.name} -> {out}")
    print(f"  基準日 {payload['as_of']} / 掲載 {len(stocks)}件")
    return 0


if __name__ == "__main__":
    sys.exit(main())
