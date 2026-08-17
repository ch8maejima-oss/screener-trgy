"""
デイトレード用スクリーニング結果を閲覧UI用のJSONに変換する。

output/ の最新の daytrade_buy_*.csv / daytrade_short_*.csv / daytrade_summary_*.json を読み、
集計値（銘柄配列を含まない）を app/daytrade/data/latest.json に、銘柄配列（stocks）を
private-data/daytrade/ 配下に分けて書き出す。前者はNext.jsのビルドにそのまま埋め込まれる
公開データ、後者はEA EXPO購入者限定のゲート配信用データ。同じ分割を
app/daytrade/data/archive/{基準日}.json（公開・集計値のみ）と
private-data/daytrade/archive/{基準日}-{buy,short}.json（非公開・銘柄配列）にも適用し、
日次バッチを重ねるたびに過去の結果がアーカイブとして蓄積されるようにする
（latest.json は毎回上書きだが archive/ 配下は削除しない）。

使い方:
    python3 scripts/build_daytrade_site_data.py
"""

import json
import math
import sys

import pandas as pd

from config import OUTPUT_DIR, ROOT

SITE_DATA = ROOT / "app" / "daytrade" / "data"
ARCHIVE_DIR = SITE_DATA / "archive"
PRIVATE_DATA = ROOT / "private-data" / "daytrade"
PRIVATE_ARCHIVE_DIR = PRIVATE_DATA / "archive"

# UIに渡す列と、表示上の丸め桁数
NUMERIC_COLS = {
    "price": 1,
    "change_1d_pct": 2,
    "change_5d_pct": 2,
    "change_20d_pct": 2,
    "volume": 0,
    "turnover_yen": 0,
    "market_cap": 0,
}
BOOL_COLS = ["volume_rising", "is_large_cap"]
TEXT_COLS = ["sec_code", "name", "market", "sector33"]


def clean(value, digits: int):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    return round(float(value), digits)


def to_stocks(csv_path) -> list:
    df = pd.read_csv(csv_path, dtype={"sec_code": str})
    stocks = []
    for r in df.to_dict("records"):
        row = {c: (None if pd.isna(r.get(c)) else r.get(c)) for c in TEXT_COLS}
        for col, digits in NUMERIC_COLS.items():
            row[col] = clean(r.get(col), digits)
        for col in BOOL_COLS:
            row[col] = bool(r.get(col)) if pd.notna(r.get(col)) else None
        stocks.append(row)
    return stocks


def main() -> int:
    buys = sorted(OUTPUT_DIR.glob("daytrade_buy_*.csv"))
    shorts = sorted(OUTPUT_DIR.glob("daytrade_short_*.csv"))
    summaries = sorted(OUTPUT_DIR.glob("daytrade_summary_*.json"))
    if not buys or not shorts or not summaries:
        print("ERROR: output/ にデイトレード結果がありません。"
              "先に screen_daytrade.py を実行してください。", file=sys.stderr)
        return 1

    latest_buy, latest_short, latest_json = buys[-1], shorts[-1], summaries[-1]
    summary = json.loads(latest_json.read_text(encoding="utf-8"))

    buy_stocks = to_stocks(latest_buy)
    short_stocks = to_stocks(latest_short)

    payload = {
        "as_of": summary["基準日"],
        "universe_label": summary["対象ユニバース"],
        "counts": {
            "population": summary["母集団件数"],
            "margin_eligible": summary["貸借銘柄件数"],
            "buy_passed": summary["買い候補"],
            "short_passed": summary["空売り候補"],
            "not_evaluable": summary["算出不能により対象外"],
        },
        "common_thresholds": summary["共通閾値"],
        "buy": {"thresholds": summary["買い候補閾値"]},
        "short": {"thresholds": summary["空売り候補閾値"]},
    }

    SITE_DATA.mkdir(parents=True, exist_ok=True)
    out = SITE_DATA / "latest.json"
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    out.write_text(text, encoding="utf-8")

    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    archive_out = ARCHIVE_DIR / f"{payload['as_of']}.json"
    archive_out.write_text(text, encoding="utf-8")

    PRIVATE_DATA.mkdir(parents=True, exist_ok=True)
    PRIVATE_ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    (PRIVATE_DATA / "buy.json").write_text(
        json.dumps(buy_stocks, ensure_ascii=False, indent=2), encoding="utf-8")
    (PRIVATE_DATA / "short.json").write_text(
        json.dumps(short_stocks, ensure_ascii=False, indent=2), encoding="utf-8")
    (PRIVATE_ARCHIVE_DIR / f"{payload['as_of']}-buy.json").write_text(
        json.dumps(buy_stocks, ensure_ascii=False, indent=2), encoding="utf-8")
    (PRIVATE_ARCHIVE_DIR / f"{payload['as_of']}-short.json").write_text(
        json.dumps(short_stocks, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"{latest_buy.name} + {latest_short.name} + {latest_json.name} -> {out}, {archive_out} "
          f"(集計値・公開) / {PRIVATE_DATA} (銘柄配列・非公開)")
    print(f"  基準日 {payload['as_of']} / 買い候補 {len(buy_stocks)}件 "
          f"/ 空売り候補 {len(short_stocks)}件")
    return 0


if __name__ == "__main__":
    sys.exit(main())
