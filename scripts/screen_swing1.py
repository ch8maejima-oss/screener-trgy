"""
スイング用スクリーニング①「期待リターン逆算」を実行し、結果を output/ に出力する。

条件・仕組み（ユーザー確認済み、2026-08-31）
  買い候補/空売り候補のような判定を行うスクリーニングではなく、東証プライム市場の
  内国普通株式を対象に、現在の株価から「市場が織り込んでいるFCF成長率」を
  2段階DCFで逆算し、一覧表として掲載する（ソートは閲覧側で行う）。

  EV(企業価値) = 時価総額 + 有利子負債 − 現金同等物 が、
  「FCFが今後10年間、年率gで成長し、11年目以降は永久成長率1%で成長し続ける」
  と仮定した場合の割引現在価値と一致するよう、gを二分探索で解く。
  割引率(WACC)はCAPMで銘柄ごとに算出する
  （株主資本コスト=無リスク金利+β×株式リスクプレミアム、
    β=5年月次リターンの対1306.T回帰、負債コスト=支払利息/有利子負債の税引後）。
  FCFのベース値はEDINET有報の営業CF−設備投資額（【設備投資等の概要】開示値）。
  「10年後想定営業利益」は現在の営業利益を同じgで10年複利成長させた参考値。

  計算の詳細・前提の根拠は reverse_dcf.py・beta.py・parse_edinet.py のdocstring、
  および閾値はconfig.pyのSWING1_*を参照。

  算出に必要な値が欠けている、またはWACC・EVの関係上gが数値的に解けない銘柄は
  「算出不能により対象外」として件数を記録し、恣意的な抽出が生じないようにする。

出力
  output/swing1_YYYY-MM-DD.csv                掲載対象銘柄（算出できた全件）
  output/swing1_all_judgements_YYYY-MM-DD.csv.gz  ユニバース全銘柄の算出結果・対象外理由（gzip）
  output/swing1_summary_YYYY-MM-DD.json       件数サマリと除外理由の内訳
"""

import argparse
import datetime as dt
import json
import sys
import warnings

import pandas as pd

import beta as beta_mod
import reverse_dcf as dcf
from config import (
    OUTPUT_DIR,
    SNAPSHOT_DIR,
    SWING1_EQUITY_RISK_PREMIUM_PCT,
    SWING1_RISK_FREE_RATE_PCT,
    SWING1_TAX_RATE_PCT,
    SWING1_TERMINAL_GROWTH_PCT,
)
from screen import fetch_market_data

warnings.filterwarnings("ignore")

TARGET_MARKET = "プライム（内国株式）"
BETA_CACHE_PATH = SNAPSHOT_DIR / "beta.csv"


def _load_beta(codes: list, refresh: bool) -> pd.DataFrame:
    cache = pd.DataFrame(columns=["sec_code", "beta", "beta_obs"])
    if BETA_CACHE_PATH.exists() and not refresh:
        cache = pd.read_csv(BETA_CACHE_PATH, dtype={"sec_code": str})

    known = set(cache["sec_code"]) if not cache.empty else set()
    missing = [c for c in codes if c not in known]
    if missing:
        print(f"β算出: 新規{len(missing)}銘柄分を取得します（5年月次、1306.T基準）...")
        new_beta = beta_mod.compute_betas(missing)
        cache = pd.concat([cache, new_beta], ignore_index=True)
        cache = cache.drop_duplicates(subset="sec_code", keep="last")
        SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
        cache.to_csv(BETA_CACHE_PATH, index=False, encoding="utf-8-sig")
    else:
        print("β算出: 新規銘柄なし、キャッシュをそのまま使用")
    return cache[cache["sec_code"].isin(codes)]


def compute(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df["market_cap"] = df["price"] * df["shares_issued"]
    # FCFのベース値 = 営業CF − 設備投資額（【設備投資等の概要】の開示値）。
    # 投資CFをそのまま使うと、現金潤沢企業ほど財務目的の預入・有価証券売買で
    # FCFが歪む（実例: ファーストリテイリングは営業CFと投資CFがほぼ相殺していた）ため、
    # 実際の設備投資額だけを控除する。
    df["fcf0"] = df["ocf"] - df["capex"]

    # 有利子負債: 該当科目が1つも取れず、かつ支払利息はある（＝負債はあるが
    # 科目名の想定外パターンで取れていない）ケースは対象外にする。
    # 支払利息も無ければ無借金とみなし0扱いにする。
    debt_ambiguous = df["interest_bearing_debt"].isna() & df["interest_expense"].notna()
    df["interest_bearing_debt_used"] = df["interest_bearing_debt"].fillna(0.0)
    df.loc[debt_ambiguous, "interest_bearing_debt_used"] = pd.NA

    df["ev"] = df["market_cap"] + df["interest_bearing_debt_used"] - df["cash_and_equivalents"]

    df["cost_of_equity_pct"] = df["beta"].apply(
        lambda b: dcf.capm_cost_of_equity_pct(b, SWING1_RISK_FREE_RATE_PCT,
                                              SWING1_EQUITY_RISK_PREMIUM_PCT)
        if pd.notna(b) else None)

    df["cost_of_debt_after_tax_pct"] = df.apply(
        lambda r: dcf.cost_of_debt_after_tax_pct(
            r["interest_expense"], r["interest_bearing_debt_used"], SWING1_TAX_RATE_PCT)
        if pd.notna(r["interest_bearing_debt_used"]) else None,
        axis=1)

    df["wacc_pct"] = df.apply(
        lambda r: dcf.wacc_pct(r["market_cap"], r["interest_bearing_debt_used"],
                               r["cost_of_equity_pct"], r["cost_of_debt_after_tax_pct"])
        if pd.notna(r["cost_of_equity_pct"]) and pd.notna(r["cost_of_debt_after_tax_pct"])
        and pd.notna(r["interest_bearing_debt_used"]) and pd.notna(r["market_cap"])
        else None,
        axis=1)

    df["implied_growth_pct"] = df.apply(
        lambda r: dcf.solve_implied_growth_pct(
            r["ev"], r["fcf0"], r["wacc_pct"], SWING1_TERMINAL_GROWTH_PCT)
        if pd.notna(r["ev"]) and pd.notna(r["wacc_pct"]) else None,
        axis=1)

    df["projected_operating_income_10y"] = df.apply(
        lambda r: dcf.project_value(r["operating_income"], r["implied_growth_pct"])
        if pd.notna(r["implied_growth_pct"]) else None,
        axis=1)

    reason = pd.Series(pd.NA, index=df.index, dtype="object")
    reason[df["price"].isna() | df["shares_issued"].isna()] = "株価・発行済株式数が取得不能"
    reason[reason.isna() & df["ocf"].isna()] = "営業CFが取得不能"
    reason[reason.isna() & df["capex"].isna()] = "設備投資額データ不足"
    reason[reason.isna() & (df["fcf0"] <= 0)] = "FCFがマイナスのため算出不能"
    reason[reason.isna() & df["interest_bearing_debt_used"].isna()] = "有利子負債データ不足"
    reason[reason.isna() & df["cash_and_equivalents"].isna()] = "現金同等物が取得不能"
    reason[reason.isna() & df["beta"].isna()] = "β算出不能（上場5年未満等）"
    reason[reason.isna() & df["wacc_pct"].isna()] = "WACC算出不能"
    reason[reason.isna() & df["implied_growth_pct"].isna()] = "WACCが永久成長率以下、または計算範囲外のため算出不能"
    df["exclusion_reason"] = reason
    df["result"] = df["exclusion_reason"].apply(lambda r: "掲載" if pd.isna(r) else "算出不能により対象外")
    return df


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--no-fetch", action="store_true",
                   help="株価を再取得せず data/snapshot/ のキャッシュを使う")
    p.add_argument("--refresh-beta", action="store_true",
                   help="β算出キャッシュを全銘柄再計算する")
    args = p.parse_args()

    snap_path = SNAPSHOT_DIR / "financials.csv"
    if not snap_path.exists():
        print("ERROR: financials.csv がありません。先に parse_edinet.py を実行してください。",
              file=sys.stderr)
        return 1

    snap = pd.read_csv(snap_path, dtype={"sec_code": str})
    snap = snap[snap["sec_code"].notna() & (snap["market"] == TARGET_MARKET)].copy()
    print(f"対象ユニバース（{TARGET_MARKET}）: {len(snap)}件")

    price_path = SNAPSHOT_DIR / "prices.csv"
    if args.no_fetch and price_path.exists():
        market = pd.read_csv(price_path, dtype={"sec_code": str})
    else:
        print("株価を取得します...")
        market = fetch_market_data(sorted(snap["sec_code"].unique()))
        market.to_csv(price_path, index=False, encoding="utf-8-sig")
    print(f"株価取得: {market['price'].notna().sum()}件")

    beta_df = _load_beta(sorted(snap["sec_code"].unique()), refresh=args.refresh_beta)
    print(f"β取得: {beta_df['beta'].notna().sum()}件")

    snap = snap.merge(market[["sec_code", "price"]], on="sec_code", how="left")
    snap = snap.merge(beta_df[["sec_code", "beta"]], on="sec_code", how="left")
    df = compute(snap)

    today = dt.date.today().isoformat()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    cols = ["sec_code", "name", "market", "sector33", "period_end", "scope", "price",
            "market_cap", "beta", "cost_of_equity_pct", "interest_bearing_debt_used",
            "cost_of_debt_after_tax_pct", "wacc_pct", "fcf0", "ev", "implied_growth_pct",
            "operating_income", "projected_operating_income_10y"]
    cols = [c for c in cols if c in df.columns]

    passed = df[df["result"] == "掲載"].sort_values("implied_growth_pct", ascending=False)
    out = passed[cols].rename(columns={"interest_bearing_debt_used": "interest_bearing_debt"})
    out.to_csv(OUTPUT_DIR / f"swing1_{today}.csv", index=False, encoding="utf-8-sig")

    all_out = df.sort_values("sec_code").copy()
    all_out.to_csv(OUTPUT_DIR / f"swing1_all_judgements_{today}.csv.gz",
                   index=False, encoding="utf-8-sig", compression="gzip")

    summary = {
        "基準日": today,
        "対象ユニバース": "東証プライム市場の内国普通株式",
        "母集団件数": int(len(df)),
        "掲載件数": int((df["result"] == "掲載").sum()),
        "算出不能により対象外": int((df["result"] == "算出不能により対象外").sum()),
        "対象外理由の内訳": {
            k: int(v) for k, v in df["exclusion_reason"].value_counts().items()
        },
        "前提条件": {
            "無リスク金利pct": SWING1_RISK_FREE_RATE_PCT,
            "株式リスクプレミアムpct": SWING1_EQUITY_RISK_PREMIUM_PCT,
            "実効税率pct": SWING1_TAX_RATE_PCT,
            "永久成長率pct": SWING1_TERMINAL_GROWTH_PCT,
            "予測期間年数": dcf.FORECAST_YEARS,
        },
    }
    (OUTPUT_DIR / f"swing1_summary_{today}.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n" + json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"\n掲載 {len(passed)}件 -> output/swing1_{today}.csv")
    if len(passed):
        print(out.head(20).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
