"""
テンバガー候補銘柄一覧のスクリーニングを実行し、結果を output/ に出力する。

スクリーニング条件（過去10年の10倍株・7倍株事例の傾向調査を踏まえて設定）

  当初は売上高成長率・経常利益成長率とも15%、上場年数8年以内としていたが、
  9条件すべてをANDで適用すると母集団3,100銘柄に対して該当0件の日がほぼ常態化する
  ことが判明した（2026-08-22実施分で確認、8条件充足でも上場年数以外で該当したのは
  3件のみ、うちいずれも上場20年超）。ユーザー判断により成長率・上場年数の閾値を
  以下まで緩和した上で、さらに「9条件全て充足」だけでなく「8条件以上充足（未達は
  最大1条件）」も掲載する方式に変更している。未達条件がある銘柄には、どの条件を
  満たしていないかを明示することで、対象を恣意的に選んだのではなく、あらかじめ
  定めた基準（未達1条件まで許容）を機械的に適用した結果であることを示す。

  1. 時価総額            100億円以下
  2. 売上高成長率        5期（4年間）の年平均成長率 8%以上
  3. 経常利益成長率      5期（4年間）の年平均成長率 8%以上
                        （5期前が赤字・0以下で直近期が黒字の場合は黒字転換として合格扱い）
  4. 自己資本比率        50%以上
  5. 上場からの年数      12年以内（yfinanceの最古の月次終値データの月を上場月の近似値とする）
  6. 株価                600円以下
  7. 出来高（流動性）    3ヶ月平均出来高が1日あたり3万株以上
                        （極端な低流動性銘柄は仕手化リスクが高いため）
  8. PBR                 同一業種（33業種区分）平均以下
                        （テーマ主導で既に高PBR化した銘柄を除外するのではなく、
                          業種平均比の相対水準で判定する）
  9. 増資の有無          発行済株式数が前期比20%を超えて増加していないこと
                        （大型増資直後の見かけ上の指標変化を排除する簡易代理指標。
                          大株主・役員保有比率や特別損失の直接検出はEDINETのXBRLで
                          構造化データとして安定取得できないため見送っている）

条件はユニバース全銘柄に対して機械的・網羅的に適用する。
判定に必要な数値が開示から取得できない銘柄は「算出不能により対象外」として
件数を記録し、恣意的な抽出が生じないようにする。

出力
  output/tenbagger_YYYY-MM-DD.csv              条件を全て満たした銘柄（全件）
  output/tenbagger_all_judgements_YYYY-MM-DD.csv.gz  ユニバース全銘柄の条件別判定内訳（gzip）
  output/tenbagger_summary_YYYY-MM-DD.json     件数サマリと除外理由の内訳
"""

import argparse
import datetime as dt
import json
import sys
import warnings

import numpy as np
import pandas as pd

from config import OUTPUT_DIR, SNAPSHOT_DIR
from screen import fetch_market_data

warnings.filterwarnings("ignore")

THRESHOLDS = {
    "market_cap_max": 10_000_000_000,
    "revenue_cagr_pct": 8.0,
    "profit_cagr_pct": 8.0,
    "equity_ratio_pct": 50.0,
    "listing_years_max": 12.0,
    "price_max": 600.0,
    "avg_volume_min": 30_000,
    "capital_increase_max_pct": 20.0,
}

CAGR_YEARS = 4  # 5期分（y0〜y4）は4年間の変化

# cond_cols と同じ並び順。unmet_conditions（未達条件の表示名一覧）の生成に使う。
CONDITION_LABELS = [
    "時価総額", "売上高成長率", "経常利益成長率", "自己資本比率",
    "上場からの年数", "株価", "出来高（流動性）", "PBR", "増資の有無",
]


def fetch_listing_dates(codes: list, batch: int = 150) -> pd.DataFrame:
    """
    上場年月日そのものはJPXの銘柄一覧・EDINETのいずれにも機械的に取得できる形で
    含まれていないため、yfinanceの株価データが遡れる最も古い月を上場月の近似値として使う。
    月足・全期間(period=max)で取得することで、日足を全期間取るより軽量に済ませる。

    既に長期上場している銘柄（Yahoo!ファイナンスのデータ取得可能期間の上限、概ね
    1999年前後より前から上場している銘柄）は近似の起点が実際の上場日より新しくなるが、
    その場合でも「8年以内」という条件には該当しないため判定結果への影響はない。
    """
    import yfinance as yf

    rows = []
    for i in range(0, len(codes), batch):
        tickers = [f"{c}.T" for c in codes[i: i + batch]]
        data = yf.download(tickers, period="max", interval="1mo", progress=False,
                           auto_adjust=False, group_by="ticker", threads=True)
        available = set(data.columns.get_level_values(0))
        for t in tickers:
            if t not in available:
                continue
            sub = data[t]
            close = sub["Close"].dropna() if "Close" in sub else []
            rows.append({
                "sec_code": t[:-2],
                "first_trade_date": close.index.min() if len(close) else None,
            })
        print(f"  上場年月取得 [{min(i + batch, len(codes))}/{len(codes)}]")
    return pd.DataFrame(rows)


def _cagr_growth(old: pd.Series, new: pd.Series, allow_turnaround: bool):
    """
    5期前(old)→直近期(new)の年平均成長率(%)を返す。

    old・newのいずれかが欠損している場合はNaN（算出不能）。
    old<=0からnew>0への黒字転換は allow_turnaround=True の場合のみ
    「growth=inf」として扱い、閾値によらず合格とみなす（利益成長率のみ許容。
    売上高は通常0以下にならないため allow_turnaround=False で運用する）。
    """
    valid = old.notna() & new.notna()
    both_positive = valid & (old > 0) & (new > 0)
    turnaround = valid & (old <= 0) & (new > 0) if allow_turnaround else pd.Series(False, index=old.index)

    growth = pd.Series(np.nan, index=old.index)
    growth[both_positive] = (new[both_positive] / old[both_positive]) ** (1 / CAGR_YEARS) - 1
    growth[turnaround] = np.inf
    # 「old>0からnew<=0」「old<=0のまま」等、有効データはあるが計算不能な減益ケースは
    # 「算出不能」ではなく明確な不合格として扱う（growth=-1で必ず閾値を下回る）
    growth[valid & growth.isna()] = -1.0
    return growth


def compute(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df["market_cap"] = df["price"] * df["shares_issued"]

    # --- 条件2: 売上高成長率 ---
    revenue_growth = _cagr_growth(df["revenue_y0"], df["revenue_y4"], allow_turnaround=False)
    df["revenue_cagr_pct"] = (revenue_growth * 100).replace([np.inf, -np.inf], np.nan)
    df["c2_revenue_growth"] = _judge(revenue_growth * 100, THRESHOLDS["revenue_cagr_pct"])

    # --- 条件3: 経常利益成長率（黒字転換は自動合格）---
    profit_growth = _cagr_growth(df["ordinary_income_y0"], df["ordinary_income_y4"], allow_turnaround=True)
    df["profit_cagr_pct"] = profit_growth.replace([np.inf, -np.inf], np.nan) * 100
    df["profit_turnaround"] = np.isposinf(profit_growth)
    df["c3_profit_growth"] = _judge_with_inf(profit_growth * 100, THRESHOLDS["profit_cagr_pct"])

    # --- 条件4: 自己資本比率（有報の開示値をそのまま採用）---
    df["c4_equity_ratio"] = _judge(df["equity_ratio_pct"], THRESHOLDS["equity_ratio_pct"])

    # --- 条件1: 時価総額 ---
    df["c1_market_cap"] = (df["market_cap"] <= THRESHOLDS["market_cap_max"]).where(df["market_cap"].notna())

    # --- 条件5: 上場からの年数 ---
    listing_years = (pd.Timestamp.today().normalize() - df["first_trade_date"]).dt.days / 365.25
    df["listing_years"] = listing_years
    df["c5_listing_years"] = (listing_years <= THRESHOLDS["listing_years_max"]).where(listing_years.notna())

    # --- 条件6: 株価 ---
    df["c6_price"] = (df["price"] <= THRESHOLDS["price_max"]).where(df["price"].notna())

    # --- 条件7: 出来高（流動性）---
    df["c7_volume"] = (df["avg_volume_3m"] >= THRESHOLDS["avg_volume_min"]).where(df["avg_volume_3m"].notna())

    # --- 条件8: PBR（同一業種平均以下）---
    df["pbr"] = (df["market_cap"] / df["net_assets"]).where(
        (df["market_cap"].notna()) & (df["net_assets"] > 0))
    df["sector_avg_pbr"] = df.groupby("sector33")["pbr"].transform("mean")
    df["c8_pbr"] = (df["pbr"] <= df["sector_avg_pbr"]).where(df["pbr"].notna() & df["sector_avg_pbr"].notna())

    # --- 条件9: 増資の有無（発行済株式数の前期比急増を除外）---
    df["shares_growth_pct"] = (
        (df["shares_issued"] / df["shares_issued_prior1"] - 1) * 100
    ).where(df["shares_issued_prior1"] > 0)
    df["c9_no_dilution"] = (
        df["shares_growth_pct"] <= THRESHOLDS["capital_increase_max_pct"]
    ).where(df["shares_growth_pct"].notna())

    cond_cols = ["c1_market_cap", "c2_revenue_growth", "c3_profit_growth", "c4_equity_ratio",
                 "c5_listing_years", "c6_price", "c7_volume", "c8_pbr", "c9_no_dilution"]
    df["n_missing"] = df[cond_cols].isna().sum(axis=1)
    df["n_passed"] = (df[cond_cols] == True).sum(axis=1)  # noqa: E712
    # 未達条件のラベル一覧（掲載対象の銘柄がどの条件を満たしていないかを示す）
    labels = {c: label for c, label in zip(cond_cols, CONDITION_LABELS)}
    df["unmet_conditions"] = df.apply(
        lambda r: [labels[c] for c in cond_cols if r[c] == False], axis=1)  # noqa: E712

    df["result"] = "対象外"
    df.loc[df["n_missing"] > 0, "result"] = "算出不能により対象外"
    df.loc[(df["n_missing"] == 0) & (df["n_passed"] == len(cond_cols) - 1), "result"] = "8/9条件充足"
    df.loc[(df["n_missing"] == 0) & (df["n_passed"] == len(cond_cols)), "result"] = "全条件充足"
    return df


def _judge(series: pd.Series, threshold: float) -> pd.Series:
    return (series >= threshold).where(series.notna())


def _judge_with_inf(series: pd.Series, threshold: float) -> pd.Series:
    """+infを常に合格とみなす以外は _judge と同じ。"""
    result = (series >= threshold)
    result[np.isposinf(series)] = True
    return result.where(series.notna())


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--no-fetch", action="store_true",
                   help="株価・上場年月を再取得せず data/snapshot/ のキャッシュを使う")
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
        print("株価・出来高を取得します...")
        market = fetch_market_data(sorted(snap["sec_code"].unique()))
        market.to_csv(price_path, index=False, encoding="utf-8-sig")
    print(f"株価取得: {market['price'].notna().sum()}件")

    listing_path = SNAPSHOT_DIR / "listing_dates.csv"
    if args.no_fetch and listing_path.exists():
        listing = pd.read_csv(listing_path, dtype={"sec_code": str}, parse_dates=["first_trade_date"])
    else:
        print("上場年月（近似値）を取得します...")
        listing = fetch_listing_dates(sorted(snap["sec_code"].unique()))
        listing.to_csv(listing_path, index=False, encoding="utf-8-sig")
    print(f"上場年月取得: {listing['first_trade_date'].notna().sum()}件")

    snap = snap.merge(market, on="sec_code", how="left")
    snap = snap.merge(listing, on="sec_code", how="left")
    if not pd.api.types.is_datetime64_any_dtype(snap["first_trade_date"]):
        snap["first_trade_date"] = pd.to_datetime(snap["first_trade_date"])
    df = compute(snap)

    today = dt.date.today().isoformat()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    cols = ["sec_code", "name", "market", "sector33", "period_end", "scope", "price",
            "market_cap", "avg_volume_3m", "revenue_cagr_pct", "profit_cagr_pct",
            "profit_turnaround", "equity_ratio_pct", "listing_years", "pbr", "sector_avg_pbr",
            "shares_growth_pct", "unmet_conditions", "result"]
    cols = [c for c in cols if c in df.columns]

    passed = df[df["result"].isin(["全条件充足", "8/9条件充足"])].sort_values(
        ["result", "market_cap"], ascending=[False, True])
    out = passed[cols].copy()
    out["unmet_conditions"] = out["unmet_conditions"].apply(lambda v: "、".join(v) if v else "")
    out.to_csv(OUTPUT_DIR / f"tenbagger_{today}.csv", index=False, encoding="utf-8-sig")

    all_out = df.sort_values("sec_code").copy()
    all_out["unmet_conditions"] = all_out["unmet_conditions"].apply(lambda v: "、".join(v) if v else "")
    all_out.to_csv(OUTPUT_DIR / f"tenbagger_all_judgements_{today}.csv.gz",
                   index=False, encoding="utf-8-sig", compression="gzip")

    cond_cols = ["c1_market_cap", "c2_revenue_growth", "c3_profit_growth", "c4_equity_ratio",
                 "c5_listing_years", "c6_price", "c7_volume", "c8_pbr", "c9_no_dilution"]
    summary = {
        "基準日": today,
        "対象ユニバース": "東証プライム市場・スタンダード市場の内国普通株式",
        "母集団件数": int(len(df)),
        "全条件充足": int((df["result"] == "全条件充足").sum()),
        "8/9条件充足": int((df["result"] == "8/9条件充足").sum()),
        "対象外": int((df["result"] == "対象外").sum()),
        "算出不能により対象外": int((df["result"] == "算出不能により対象外").sum()),
        "条件別_充足件数": {c: int((df[c] == True).sum()) for c in cond_cols},  # noqa: E712
        "条件別_算出不能件数": {c: int(df[c].isna().sum()) for c in cond_cols},
        "閾値": THRESHOLDS,
    }
    (OUTPUT_DIR / f"tenbagger_summary_{today}.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n" + json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"\n8/9条件以上充足 {len(passed)}件 -> output/tenbagger_{today}.csv")
    if len(passed):
        print(out.head(30).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
