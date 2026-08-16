"""
スクリーニング結果を閲覧UI用のJSONに変換する。

output/ の最新の screening_*.csv / summary_*.json を読み、app/dividend/data/latest.json を生成する。
UIは静的サイトとしてビルドされるため、この変換を経てから `npm run build` する。

使い方:
    python3 scripts/build_site_data.py
"""

import json
import math
import sys

import pandas as pd

from config import OUTPUT_DIR, ROOT

SITE_DATA = ROOT / "app" / "dividend" / "data"

# UIに渡す列と、表示上の丸め桁数
NUMERIC_COLS = {
    "price": 1,
    "dividend_ttm": 2,
    "dividend_yield_pct": 2,
    "roe_pct": 2,
    "equity_ratio_pct": 2,
    "current_ratio_pct": 1,
    "revenue_change_pct": 1,
    "operating_margin_pct": 2,
    "dps_yuho": 2,
    "dps_diff_pct": 1,
}
TEXT_COLS = ["sec_code", "name", "market", "sector33", "period_end", "scope"]


def clean(value, digits: int):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    return round(float(value), digits)


def main() -> int:
    screenings = sorted(OUTPUT_DIR.glob("screening_*.csv"))
    summaries = sorted(OUTPUT_DIR.glob("summary_*.json"))
    if not screenings or not summaries:
        print("ERROR: output/ に結果がありません。先に screen.py を実行してください。",
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

    # 配当利回りの高い順を既定の並びとする（表示順であって優劣ではない）
    stocks.sort(key=lambda s: (s["dividend_yield_pct"] is None,
                               -(s["dividend_yield_pct"] or 0)))

    payload = {
        "as_of": summary["基準日"],
        "universe_label": summary["対象ユニバース"],
        "counts": {
            "population": summary["母集団件数"],
            "passed": summary["全条件充足"],
            "failed": summary["不通過"],
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
    print(f"  基準日 {payload['as_of']} / 掲載 {len(stocks)}件 "
          f"/ 母集団 {payload['counts']['population']}件")
    return 0


if __name__ == "__main__":
    sys.exit(main())
