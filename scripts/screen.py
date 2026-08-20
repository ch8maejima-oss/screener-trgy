"""
6条件のスクリーニングを実行し、結果を output/ に出力する。

スクリーニング条件
  1. 配当利回り        3.5% 以上   （直近12か月の実績配当合計 ÷ 株価）
  2. ROE               10%  以上   （有報【主要な経営指標等の推移】の自己資本利益率）
  3. 自己資本比率      50%  以上   （同上の開示値）
  4. 流動比率          200% 以上   （流動資産 ÷ 流動負債）
  5. 売上高            直近5期で減収していないこと
  6. 売上高営業利益率  10%  以上   （営業利益 ÷ 売上高）

条件はユニバース全銘柄に対して機械的・網羅的に適用する。
判定に必要な数値が開示から取得できない銘柄は「算出不能により対象外」として
件数を記録し、恣意的な抽出が生じないようにする。

出力
  output/screening_YYYY-MM-DD.csv       条件を全て満たした銘柄（全件）
  output/all_judgements_YYYY-MM-DD.csv.gz  ユニバース全銘柄の条件別判定内訳（gzip）
  output/summary_YYYY-MM-DD.json        件数サマリと除外理由の内訳
"""

import argparse
import datetime as dt
import json
import sys
import warnings

import pandas as pd

from config import OUTPUT_DIR, SNAPSHOT_DIR

warnings.filterwarnings("ignore")

THRESHOLDS = {
    "dividend_yield_pct": 3.5,
    "roe_pct": 10.0,
    "equity_ratio_pct": 50.0,
    "current_ratio_pct": 200.0,
    "operating_margin_pct": 10.0,
}


def fetch_market_data(codes: list, batch: int = 150) -> pd.DataFrame:
    """
    直近終値、直近12か月に実際に支払われた配当の合計、直近3か月の平均出来高を一括取得する。

    配当に有報の「1株当たり配当額」をそのまま使うことはできない。期中に株式分割が
    あると、有報の値は中間配当が分割前・期末配当が分割後の基準で合算され、分割後の
    株価と組み合わせると利回りが実態より大きくなるため（例: ニトリHDは有報92.4円
    に対し分割調整後は30.8円）。株価と同じ分割調整済みの系列から算出する。
    """
    import yfinance as yf

    rows = []
    for i in range(0, len(codes), batch):
        tickers = [f"{c}.T" for c in codes[i: i + batch]]
        data = yf.download(tickers, period="1y", actions=True, progress=False,
                           auto_adjust=False, group_by="ticker", threads=True)
        available = set(data.columns.get_level_values(0))
        for t in tickers:
            if t not in available:
                continue
            sub = data[t]
            close = sub["Close"].dropna() if "Close" in sub else []
            if "Volume" in sub and len(sub["Volume"].dropna()):
                cutoff = sub.index.max() - pd.DateOffset(months=3)
                vol_3m = sub["Volume"][sub.index >= cutoff].dropna()
                avg_volume_3m = float(vol_3m.mean()) if len(vol_3m) else None
            else:
                avg_volume_3m = None
            rows.append({
                "sec_code": t[:-2],
                "price": float(close.iloc[-1]) if len(close) else None,
                "avg_volume_3m": avg_volume_3m,
                "dividend_ttm": (float(sub["Dividends"].sum())
                                 if "Dividends" in sub else None),
            })
        print(f"  株価・配当取得 [{min(i + batch, len(codes))}/{len(codes)}]")
    return pd.DataFrame(rows)


def compute(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df["dividend_yield_pct"] = (
        df["dividend_ttm"] / df["price"] * 100
    ).where(df["price"] > 0)
    df["market_cap"] = df["price"] * df["shares_issued"]
    # 有報の開示値との乖離。株式分割や決算期ズレの検出用に残す
    df["dps_yuho"] = df["dps"]
    df["dps_diff_pct"] = ((df["dividend_ttm"] / df["dps"] - 1) * 100).where(df["dps"] > 0)

    df["current_ratio_pct"] = (
        df["current_assets"] / df["current_liabilities"] * 100
    ).where(df["current_liabilities"] > 0)

    # 分母は【主要な経営指標等の推移】の直近期売上高（営業利益と同一スコープ）
    df["operating_margin_pct"] = (
        df["operating_income"] / df["revenue_y4"] * 100
    ).where(df["revenue_y4"] > 0)

    # 条件5: 有報の【主要な経営指標等の推移】5期分のうち、
    # 最も古い期と直近期を比較して減収していないこと
    df["revenue_oldest"] = df["revenue_y0"]
    df["revenue_latest"] = df["revenue_y4"]
    df["revenue_change_pct"] = (
        (df["revenue_latest"] / df["revenue_oldest"] - 1) * 100
    ).where(df["revenue_oldest"] > 0)

    # 条件別の判定。数値が無いものは False ではなく NaN（=算出不能）とする
    df["c1_dividend"] = _judge(df["dividend_yield_pct"], THRESHOLDS["dividend_yield_pct"])
    df["c2_roe"] = _judge(df["roe_pct"], THRESHOLDS["roe_pct"])
    df["c3_equity_ratio"] = _judge(df["equity_ratio_pct"], THRESHOLDS["equity_ratio_pct"])
    df["c4_current_ratio"] = _judge(df["current_ratio_pct"], THRESHOLDS["current_ratio_pct"])
    df["c5_revenue"] = _judge(df["revenue_change_pct"], 0.0)
    df["c6_op_margin"] = _judge(df["operating_margin_pct"], THRESHOLDS["operating_margin_pct"])

    cond_cols = ["c1_dividend", "c2_roe", "c3_equity_ratio",
                 "c4_current_ratio", "c5_revenue", "c6_op_margin"]
    df["n_missing"] = df[cond_cols].isna().sum(axis=1)
    df["n_passed"] = (df[cond_cols] == True).sum(axis=1)  # noqa: E712
    df["result"] = "不通過"
    df.loc[df["n_missing"] > 0, "result"] = "算出不能により対象外"
    df.loc[(df["n_missing"] == 0) & (df["n_passed"] == 6), "result"] = "全条件充足"
    return df


def _judge(series: pd.Series, threshold: float) -> pd.Series:
    return (series >= threshold).where(series.notna())


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--no-fetch", action="store_true",
                   help="株価を再取得せず data/snapshot/prices.csv を使う")
    args = p.parse_args()

    snap_path = SNAPSHOT_DIR / "financials.csv"
    if not snap_path.exists():
        print("ERROR: financials.csv がありません。先に parse_edinet.py を実行してください。",
              file=sys.stderr)
        return 1

    snap = pd.read_csv(snap_path, dtype={"sec_code": str})
    snap = snap[snap["sec_code"].notna()].copy()
    print(f"財務スナップショット: {len(snap)}件")

    price_path = SNAPSHOT_DIR / "prices.csv"
    if args.no_fetch and price_path.exists():
        market = pd.read_csv(price_path, dtype={"sec_code": str})
    else:
        print("株価・配当を取得します...")
        market = fetch_market_data(sorted(snap["sec_code"].unique()))
        market.to_csv(price_path, index=False, encoding="utf-8-sig")
    print(f"株価取得: {market['price'].notna().sum()}件")

    snap = snap.merge(market, on="sec_code", how="left")
    df = compute(snap)

    today = dt.date.today().isoformat()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    cols = ["sec_code", "name", "market", "sector33", "period_end", "scope", "price",
            "market_cap", "avg_volume_3m",
            "dividend_ttm", "dividend_yield_pct", "roe_pct", "equity_ratio_pct",
            "current_ratio_pct", "revenue_change_pct", "operating_margin_pct",
            "dps_yuho", "dps_diff_pct", "result"]
    cols = [c for c in cols if c in df.columns]

    passed = df[df["result"] == "全条件充足"].sort_values(
        "dividend_yield_pct", ascending=False)
    passed[cols].to_csv(OUTPUT_DIR / f"screening_{today}.csv",
                        index=False, encoding="utf-8-sig")
    # 母集団全銘柄の判定内訳は日次で1.8MB程度になるため gzip 圧縮して保存する
    df.sort_values("sec_code").to_csv(OUTPUT_DIR / f"all_judgements_{today}.csv.gz",
                                      index=False, encoding="utf-8-sig",
                                      compression="gzip")

    cond_cols = ["c1_dividend", "c2_roe", "c3_equity_ratio",
                 "c4_current_ratio", "c5_revenue", "c6_op_margin"]
    summary = {
        "基準日": today,
        "対象ユニバース": "東証プライム市場・スタンダード市場の内国普通株式",
        "母集団件数": int(len(df)),
        "全条件充足": int((df["result"] == "全条件充足").sum()),
        "不通過": int((df["result"] == "不通過").sum()),
        "算出不能により対象外": int((df["result"] == "算出不能により対象外").sum()),
        "条件別_充足件数": {c: int((df[c] == True).sum()) for c in cond_cols},  # noqa: E712
        "条件別_算出不能件数": {c: int(df[c].isna().sum()) for c in cond_cols},
        "閾値": THRESHOLDS,
    }
    (OUTPUT_DIR / f"summary_{today}.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n" + json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"\n全条件充足 {len(passed)}件 -> output/screening_{today}.csv")
    if len(passed):
        print(passed[cols].head(30).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
