"""
スイング用スクリーニング②「ROE・PBR整合性チェッカー」の当日エントリー候補を
算出し、結果を output/ に出力する。

PBR＝ROE×PERの恒等式から、経常利益ベースの調整後ROEに業種平均PERを乗じた
「理論PBR」を算出し、実際のPBRとの下方乖離を機械的に検知する
（計算式の詳細は roe_pbr.py・technical.py のdocstring、閾値はTHRESHOLDSを参照）。

対象ユニバース: 東証プライム・スタンダード市場の内国普通株式のうち、
  時価総額300億円以上（中型株以上の目安）・3ヶ月平均出来高10万株以上（流動性）
  （ユーザー原案は「流動性がある中大型株」という定性的な条件のみだったため、
  具体的な閾値はこちらで設定した。tenbagger等の既存閾値設定と同じ判断方針）。

エントリー条件（すべて満たすこと）
  条件①: 理論PBRに対する実績PBRの下方乖離率が20%以上
  条件②: 調整後ROE（経常利益ベース）が8%以上、かつ過去3年間で2期連続悪化していないこと
  条件③: PERが業種平均PERより低い、かつ自己資本比率が40%以上
  条件④: ゴールデンクロス／25日線反転／出来高急増（底値圏）のいずれか1つ以上

条件はユニバース全銘柄に機械的・網羅的に適用し、算出に必要な数値が取得できない
銘柄は「算出不能により対象外」として件数を記録する。

出力
  output/swing2_buy_YYYY-MM-DD.csv          当日エントリー候補（全件）
  output/swing2_all_judgements_YYYY-MM-DD.csv.gz  ユニバース全銘柄の判定内訳（gzip）
  output/swing2_summary_YYYY-MM-DD.json     件数サマリと閾値
"""

import argparse
import datetime as dt
import json
import sys
import warnings

import pandas as pd

import technical as tech
from config import MASTER_DIR, OUTPUT_DIR, SNAPSHOT_DIR
from market_data import load_daily_cache
from roe_pbr import adjusted_roe_pct, lower_deviation_pct, roe_not_declining_3y, theoretical_pbr
from screen import fetch_market_data

warnings.filterwarnings("ignore")

THRESHOLDS = {
    "market_cap_min": 30_000_000_000.0,  # 300億円（中型株以上の目安）
    "avg_volume_min": 100_000.0,  # 3ヶ月平均出来高10万株（流動性の目安）
    "lower_deviation_min_pct": 20.0,
    "adjusted_roe_min_pct": 8.0,
    "equity_ratio_min_pct": 40.0,
}
TARGET_MARKETS = {"プライム（内国株式）", "スタンダード（内国株式）"}

CONDITION_LABELS = ["理論PBRとの下方乖離", "ROEの質（水準・トレンド）", "安全性フィルター", "テクニカル条件"]


def compute_fundamentals(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["market_cap"] = df["price"] * df["shares_issued"]
    df["pbr"] = (df["market_cap"] / df["net_assets"]).where(df["net_assets"] > 0)
    df["per"] = (df["price"] / df["eps"]).where(df["eps"] > 0)

    df["adjusted_roe_pct"] = df.apply(
        lambda r: adjusted_roe_pct(r["ordinary_income_y4"], r["net_assets_y4"]), axis=1)
    roe_y2 = df.apply(lambda r: adjusted_roe_pct(r["ordinary_income_y2"], r["net_assets_y2"]), axis=1)
    roe_y3 = df.apply(lambda r: adjusted_roe_pct(r["ordinary_income_y3"], r["net_assets_y3"]), axis=1)
    df["roe_not_declining_3y"] = [
        roe_not_declining_3y([o, m, latest])
        for o, m, latest in zip(roe_y2, roe_y3, df["adjusted_roe_pct"])
    ]

    # 単純平均だと赤字転換寸前などPERが極端に大きい銘柄（実データで業種内最大3855倍を確認）
    # に平均が引っ張られ、業種によっては平均が中央値の3倍近くまで乖離する
    # （例: 小売業 平均47.2倍 対 中央値16.3倍）。理論PBRの分母に使うには不適切なため、
    # 外れ値に頑健な中央値を業種平均PERの代用として使う。
    sector_avg_per = df.groupby("sector33")["per"].transform("median")
    df["sector_avg_per"] = sector_avg_per
    df["theoretical_pbr"] = df.apply(
        lambda r: theoretical_pbr(r["adjusted_roe_pct"], r["sector_avg_per"]), axis=1)
    df["lower_deviation_pct"] = df.apply(
        lambda r: lower_deviation_pct(r["theoretical_pbr"], r["pbr"]), axis=1)
    return df


def judge(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df["c1_deviation"] = (
        df["lower_deviation_pct"] >= THRESHOLDS["lower_deviation_min_pct"]
    ).where(df["lower_deviation_pct"].notna())

    roe_level_ok = df["adjusted_roe_pct"] >= THRESHOLDS["adjusted_roe_min_pct"]
    df["c2_roe_quality"] = (roe_level_ok & df["roe_not_declining_3y"].fillna(False)).where(
        df["adjusted_roe_pct"].notna() & df["roe_not_declining_3y"].notna())

    per_ok = df["per"] < df["sector_avg_per"]
    equity_ok = df["equity_ratio_pct"] >= THRESHOLDS["equity_ratio_min_pct"]
    df["c3_safety"] = (per_ok & equity_ok).where(
        df["per"].notna() & df["sector_avg_per"].notna() & df["equity_ratio_pct"].notna())

    df["c4_technical"] = df["technical_signal"].notna().where(df["_technical_evaluable"])

    cond_cols = ["c1_deviation", "c2_roe_quality", "c3_safety", "c4_technical"]
    df["n_missing"] = df[cond_cols].isna().sum(axis=1)
    df["n_passed"] = (df[cond_cols] == True).sum(axis=1)  # noqa: E712
    df["result"] = "対象外"
    df.loc[df["n_missing"] > 0, "result"] = "算出不能により対象外"
    df.loc[(df["n_missing"] == 0) & (df["n_passed"] == len(cond_cols)), "result"] = "全条件充足"
    return df


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--no-fetch", action="store_true",
                   help="株価を再取得せず data/snapshot/ のキャッシュを使う")
    args = p.parse_args()

    snap_path = SNAPSHOT_DIR / "financials.csv"
    if not snap_path.exists():
        print("ERROR: financials.csv がありません。先に parse_edinet.py を実行してください。",
              file=sys.stderr)
        return 1
    snap = pd.read_csv(snap_path, dtype={"sec_code": str})
    snap = snap[snap["sec_code"].notna() & snap["market"].isin(TARGET_MARKETS)].copy()
    print(f"対象ユニバース: {len(snap)}件")

    price_path = SNAPSHOT_DIR / "prices.csv"
    if args.no_fetch and price_path.exists():
        market = pd.read_csv(price_path, dtype={"sec_code": str})
    else:
        print("株価を取得します...")
        market = fetch_market_data(sorted(snap["sec_code"].unique()))
        market.to_csv(price_path, index=False, encoding="utf-8-sig")
    snap = snap.merge(market[["sec_code", "price", "avg_volume_3m"]], on="sec_code", how="left")

    snap = compute_fundamentals(snap)
    snap["c0_size_liquidity"] = (
        (snap["market_cap"] >= THRESHOLDS["market_cap_min"])
        & (snap["avg_volume_3m"] >= THRESHOLDS["avg_volume_min"])
    ).where(snap["market_cap"].notna() & snap["avg_volume_3m"].notna())

    universe_codes = sorted(snap.loc[snap["c0_size_liquidity"] == True, "sec_code"].unique())  # noqa: E712
    print(f"中大型・流動性フィルター通過: {len(universe_codes)}件（テクニカル判定を実施）")
    daily = load_daily_cache(universe_codes)

    technical_signal = {}
    evaluable = {}
    for code, g in daily.groupby("sec_code"):
        g = g.sort_values("date")
        evaluable[code] = len(g) >= 26  # 25日移動平均に必要な最低本数
        technical_signal[code] = tech.entry_technical_signal(g) if evaluable[code] else None
    snap["technical_signal"] = snap["sec_code"].map(technical_signal)
    snap["_technical_evaluable"] = snap["sec_code"].map(evaluable).fillna(False)
    # サイズ・流動性フィルターを通らなかった銘柄はテクニカル自体を評価対象外とする
    snap.loc[snap["c0_size_liquidity"] != True, "_technical_evaluable"] = False  # noqa: E712

    df = judge(snap)
    # サイズ・流動性フィルターを明確に「通らなかった」銘柄（False。時価総額・出来高
    # 自体は取得できている）は、個別条件の充足有無によらず対象外にする。
    # フィルター自体が算出不能（NaN）な銘柄は、judge()側の「算出不能により対象外」の
    # 判定をそのまま使う（ここで一律に上書きすると除外理由の内訳が不正確になるため）。
    df.loc[df["c0_size_liquidity"] == False, "result"] = "対象外（規模・流動性フィルター未通過）"  # noqa: E712

    today = dt.date.today().isoformat()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    cols = ["sec_code", "name", "market", "sector33", "period_end", "scope", "price",
            "market_cap", "avg_volume_3m", "pbr", "theoretical_pbr", "lower_deviation_pct",
            "adjusted_roe_pct", "per", "sector_avg_per", "equity_ratio_pct", "technical_signal",
            "result"]
    cols = [c for c in cols if c in df.columns]

    passed = df[df["result"] == "全条件充足"].sort_values("lower_deviation_pct", ascending=False)
    out = passed[cols].copy()
    out.to_csv(OUTPUT_DIR / f"swing2_buy_{today}.csv", index=False, encoding="utf-8-sig")

    all_out = df.sort_values("sec_code").copy()
    all_out.to_csv(OUTPUT_DIR / f"swing2_all_judgements_{today}.csv.gz",
                   index=False, encoding="utf-8-sig", compression="gzip")

    cond_cols = ["c1_deviation", "c2_roe_quality", "c3_safety", "c4_technical"]
    summary = {
        "基準日": today,
        "対象ユニバース": "東証プライム市場・スタンダード市場の内国普通株式のうち中大型株・流動性フィルター通過銘柄",
        "母集団件数": int(len(df)),
        "規模流動性フィルター通過": int((df["c0_size_liquidity"] == True).sum()),  # noqa: E712
        "全条件充足": int((df["result"] == "全条件充足").sum()),
        "対象外": int((df["result"] == "対象外").sum()),
        "算出不能により対象外": int((df["result"] == "算出不能により対象外").sum()),
        "条件別_充足件数": {c: int((df[c] == True).sum()) for c in cond_cols},  # noqa: E712
        "条件別_算出不能件数": {c: int(df[c].isna().sum()) for c in cond_cols},
        "閾値": THRESHOLDS,
    }
    (OUTPUT_DIR / f"swing2_summary_{today}.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n" + json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"\n全条件充足 {len(passed)}件 -> output/swing2_buy_{today}.csv")
    if len(passed):
        print(out.head(20).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
