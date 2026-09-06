"""
デイトレード用スクリーニング②「決算発表カレンダー」を実行し、結果を output/ に出力する。

条件・仕組み（ユーザー確認済み、2026-09-01）
  合否判定のスクリーニングではなく、今後の決算発表予定日（JPX公開の一覧、
  fetch_earnings_calendar.py取得）が近い順に、貸借銘柄（screen_daytrade.pyと
  同じ対象範囲）を一覧表示する。直近の有価証券報告書に基づく営業利益・ROE・EPSを
  参考値として併記し、「決算またぎ」でポジションを持つかどうかの判断材料とする。

  当初「業績修正インパクト分析」（業績予想の修正前後の比較）として企画したが、
  修正データの取得にはJ-Quants API等が必要で、同APIの利用規約は法人利用を
  社内限定・非営利目的でも一律禁止しており、当社（法人）での利用に適さないと
  判断し保留とした。決算発表予定日一覧の部分のみ先行して実装する。

出力
  output/daytrade2_YYYY-MM-DD.csv  掲載対象銘柄（貸借銘柄かつ決算発表予定日・
                                    財務データの両方が取得できた銘柄）
  output/daytrade2_summary_YYYY-MM-DD.json  件数サマリ
"""

import argparse
import datetime as dt
import json
import sys
import warnings

import pandas as pd

from config import MASTER_DIR, OUTPUT_DIR, SNAPSHOT_DIR

warnings.filterwarnings("ignore")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    args = p.parse_args()  # noqa: F841 (将来のオプション追加に備えて残す)

    cal_path = MASTER_DIR / "earnings_calendar.csv"
    if not cal_path.exists():
        print("ERROR: earnings_calendar.csv がありません。先に "
              "fetch_earnings_calendar.py を実行してください。", file=sys.stderr)
        return 1
    calendar = pd.read_csv(cal_path, dtype={"code": str}, parse_dates=["announcement_date"])
    calendar = calendar.rename(columns={"code": "sec_code"})
    print(f"決算発表予定日: {len(calendar)}件")

    margin_path = MASTER_DIR / "margin_list.csv"
    if not margin_path.exists():
        print("ERROR: margin_list.csv がありません。先に fetch_margin_list.py を"
              "実行してください。", file=sys.stderr)
        return 1
    margin = pd.read_csv(margin_path, dtype={"code": str})
    margin_codes = set(margin["code"])
    calendar = calendar[calendar["sec_code"].isin(margin_codes)].copy()
    print(f"うち貸借銘柄: {len(calendar)}件")

    # 既に発表済みの日付は「決算またぎ判断」の参考にならないため、当日以降のみを対象とする
    today_ts = pd.Timestamp(dt.date.today())
    calendar = calendar[calendar["announcement_date"] >= today_ts].copy()
    print(f"うち本日以降: {len(calendar)}件")

    fin_path = SNAPSHOT_DIR / "financials.csv"
    if not fin_path.exists():
        print("ERROR: financials.csv がありません。先に parse_edinet.py を実行してください。",
              file=sys.stderr)
        return 1
    fin = pd.read_csv(fin_path, dtype={"sec_code": str})
    fin_cols = ["sec_code", "period_end", "operating_income", "roe_pct", "eps"]
    fin = fin[fin["sec_code"].notna()][fin_cols].drop_duplicates(subset="sec_code")

    df = calendar.merge(fin, on="sec_code", how="left")
    df["has_financials"] = df["operating_income"].notna() | df["roe_pct"].notna() | df["eps"].notna()

    today = dt.date.today().isoformat()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    listed = df[df["has_financials"]].sort_values(["announcement_date", "sec_code"])
    cols = ["announcement_date", "sec_code", "name", "market", "sector33", "quarter_type",
            "fiscal_year_end", "period_end", "operating_income", "roe_pct", "eps"]
    out = listed[[c for c in cols if c in listed.columns]].copy()
    out.to_csv(OUTPUT_DIR / f"daytrade2_{today}.csv", index=False, encoding="utf-8-sig")

    summary = {
        "基準日": today,
        "対象ユニバース": "貸借銘柄（信用区分=貸借銘柄）のうち、直近の決算発表予定日が判明している銘柄",
        "決算発表予定日_取得件数": int(len(calendar)),
        "掲載件数": int(len(out)),
        "算出不能により対象外": int((~df["has_financials"]).sum()),
        "発表予定日の範囲": {
            "開始": str(calendar["announcement_date"].min().date()) if len(calendar) else None,
            "終了": str(calendar["announcement_date"].max().date()) if len(calendar) else None,
        },
    }
    (OUTPUT_DIR / f"daytrade2_summary_{today}.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n" + json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"\n掲載 {len(out)}件 -> output/daytrade2_{today}.csv")
    if len(out):
        print(out.head(20).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
