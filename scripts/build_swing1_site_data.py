"""
スイング用スクリーニング①「期待リターン逆算」の結果を閲覧UI用のJSONに変換する。

output/ の最新の swing1_*.csv / swing1_summary_*.json を読み、
app/swing-implied-growth/data/latest.json に書き出す。dividend/daytrade/tenbagger と異なり
現時点ではサブスク非対応の無料公開ページのため、private-data/への分離は行わず
銘柄配列も含めてそのままapp/配下に置く。

使い方:
    python3 scripts/build_swing1_site_data.py
"""

import json
import math
import sys

import pandas as pd

from config import (
    OUTPUT_DIR,
    ROOT,
    SWING1_EQUITY_RISK_PREMIUM_PCT,
    SWING1_RISK_FREE_RATE_PCT,
    SWING1_TAX_RATE_PCT,
    SWING1_TERMINAL_GROWTH_PCT,
)
from reverse_dcf import FORECAST_YEARS

SITE_DATA = ROOT / "app" / "swing-implied-growth" / "data"

NUMERIC_COLS = {
    "price": 1,
    "market_cap": 0,
    "beta": 3,
    "cost_of_equity_pct": 2,
    "interest_bearing_debt": 0,
    "cost_of_debt_after_tax_pct": 2,
    "wacc_pct": 2,
    "fcf0": 0,
    "ev": 0,
    "implied_growth_pct": 2,
    "operating_income": 0,
    "projected_operating_income_10y": 0,
}
TEXT_COLS = ["sec_code", "name", "market", "sector33", "period_end", "scope"]


def clean(value, digits: int):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    return round(float(value), digits)


def main() -> int:
    screenings = sorted(OUTPUT_DIR.glob("swing1_[0-9]*.csv"))
    summaries = sorted(OUTPUT_DIR.glob("swing1_summary_*.json"))
    if not screenings or not summaries:
        print("ERROR: output/ にスイング①の結果がありません。先に screen_swing1.py を実行してください。",
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

    # 市場織込み成長率が高い（＝市場の期待が強い）順を初期表示順とする（表示上の並びであって推奨ではない）
    stocks.sort(key=lambda s: (s["implied_growth_pct"] is None, -(s["implied_growth_pct"] or 0)))

    payload = {
        "as_of": summary["基準日"],
        "universe_label": summary["対象ユニバース"],
        "counts": {
            "population": summary["母集団件数"],
            "listed": summary["掲載件数"],
            "not_evaluable": summary["算出不能により対象外"],
        },
        "exclusion_reasons": summary["対象外理由の内訳"],
        "assumptions": {
            "risk_free_rate_pct": SWING1_RISK_FREE_RATE_PCT,
            "equity_risk_premium_pct": SWING1_EQUITY_RISK_PREMIUM_PCT,
            "tax_rate_pct": SWING1_TAX_RATE_PCT,
            "terminal_growth_pct": SWING1_TERMINAL_GROWTH_PCT,
            "forecast_years": FORECAST_YEARS,
        },
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
