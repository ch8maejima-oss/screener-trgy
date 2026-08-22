"""
テンバガー候補スクリーニング結果を閲覧UI用のJSONに変換する。

output/ の最新の tenbagger_*.csv / tenbagger_summary_*.json を読み、集計値
（銘柄配列を含まない）を app/tenbagger/data/latest.json に、銘柄配列（stocks）を
private-data/tenbagger/stocks.json に分けて書き出す。前者はNext.jsのビルドに
そのまま埋め込まれる公開データ、後者はEA EXPO購入者限定のゲート配信用データで、
app/配下に置かないことでビルド成果物に含まれないようにする（build_site_data.pyと同じ設計）。

使い方:
    python3 scripts/build_tenbagger_site_data.py
"""

import json
import math
import sys

import pandas as pd

from config import OUTPUT_DIR, ROOT

SITE_DATA = ROOT / "app" / "tenbagger" / "data"
PRIVATE_DATA = ROOT / "private-data" / "tenbagger"

NUMERIC_COLS = {
    "price": 1,
    "market_cap": 0,
    "avg_volume_3m": 0,
    "revenue_cagr_pct": 1,
    "profit_cagr_pct": 1,
    "equity_ratio_pct": 2,
    "listing_years": 1,
    "pbr": 2,
    "sector_avg_pbr": 2,
    "shares_growth_pct": 1,
}
BOOL_COLS = ["profit_turnaround"]
TEXT_COLS = ["sec_code", "name", "market", "sector33", "period_end", "scope", "result"]


def clean(value, digits: int):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    return round(float(value), digits)


def clean_bool(value):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return False
    return bool(value)


def main() -> int:
    screenings = sorted(OUTPUT_DIR.glob("tenbagger_[0-9]*.csv"))
    summaries = sorted(OUTPUT_DIR.glob("tenbagger_summary_*.json"))
    if not screenings or not summaries:
        print("ERROR: output/ にテンバガー候補の結果がありません。先に screen_tenbagger.py を実行してください。",
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
        for col in BOOL_COLS:
            row[col] = clean_bool(r.get(col))
        unmet = r.get("unmet_conditions")
        row["unmet_conditions"] = (
            [x for x in str(unmet).split("、") if x] if isinstance(unmet, str) and unmet else []
        )
        stocks.append(row)

    # 全条件充足を優先し、同順位内は時価総額の小さい順とする（表示順であって優劣ではない）
    stocks.sort(key=lambda s: (
        s["result"] != "全条件充足", s["market_cap"] is None, s["market_cap"] or 0))

    payload = {
        "as_of": summary["基準日"],
        "universe_label": summary["対象ユニバース"],
        "counts": {
            "population": summary["母集団件数"],
            "full_match": summary["全条件充足"],
            "near_match": summary["8/9条件充足"],
            "passed": summary["全条件充足"] + summary["8/9条件充足"],
            "failed": summary["対象外"],
            "not_evaluable": summary["算出不能により対象外"],
        },
        "per_condition_passed": summary["条件別_充足件数"],
        "per_condition_missing": summary["条件別_算出不能件数"],
        "thresholds": summary["閾値"],
    }

    SITE_DATA.mkdir(parents=True, exist_ok=True)
    out = SITE_DATA / "latest.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    PRIVATE_DATA.mkdir(parents=True, exist_ok=True)
    stocks_out = PRIVATE_DATA / "stocks.json"
    stocks_out.write_text(json.dumps(stocks, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"{latest_csv.name} + {latest_json.name} -> {out} (集計値), {stocks_out} (銘柄配列)")
    print(f"  基準日 {payload['as_of']} / 掲載 {len(stocks)}件 "
          f"/ 母集団 {payload['counts']['population']}件")
    return 0


if __name__ == "__main__":
    sys.exit(main())
