"""
スイング用スクリーニング②「ROE・PBR整合性チェッカー」の結果を閲覧UI用のJSONに変換する。

output/ の最新の swing2_buy_*.csv / swing2_summary_*.json を読み、
app/swing-roe-pbr/data/latest.json に書き出す。swing-implied-growthと同じく
無料公開ページのためprivate-data/への分離は行わない。

使い方:
    python3 scripts/build_swing2_site_data.py
"""

import json
import math
import sys

import pandas as pd

from config import OUTPUT_DIR, ROOT

SITE_DATA = ROOT / "app" / "swing-roe-pbr" / "data"

NUMERIC_COLS = {
    "price": 1,
    "market_cap": 0,
    "avg_volume_3m": 0,
    "pbr": 3,
    "theoretical_pbr": 3,
    "lower_deviation_pct": 1,
    "adjusted_roe_pct": 2,
    "per": 2,
    "sector_avg_per": 2,
    "equity_ratio_pct": 2,
}
TEXT_COLS = ["sec_code", "name", "market", "sector33", "period_end", "scope", "technical_signal"]


def clean(value, digits: int):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    return round(float(value), digits)


def main() -> int:
    screenings = sorted(OUTPUT_DIR.glob("swing2_buy_[0-9]*.csv"))
    summaries = sorted(OUTPUT_DIR.glob("swing2_summary_*.json"))
    if not screenings or not summaries:
        print("ERROR: output/ にスイング②の結果がありません。先に screen_swing2.py を実行してください。",
              file=sys.stderr)
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

    stocks.sort(key=lambda s: (s["lower_deviation_pct"] is None, -(s["lower_deviation_pct"] or 0)))

    payload = {
        "as_of": summary["基準日"],
        "universe_label": summary["対象ユニバース"],
        "counts": {
            "population": summary["母集団件数"],
            "size_liquidity_passed": summary["規模流動性フィルター通過"],
            "listed": summary["全条件充足"],
            "not_evaluable": summary["算出不能により対象外"],
        },
        "per_condition_passed": summary["条件別_充足件数"],
        "per_condition_missing": summary["条件別_算出不能件数"],
        "thresholds": summary["閾値"],
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
