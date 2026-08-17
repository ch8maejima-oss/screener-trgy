"""
デイトレード用スクリーニングを実行し、結果を output/ に出力する。

上昇モメンタム（買い候補）と下落モメンタム（空売り候補）の2種類のリストを作る。
「前日+2〜10%」と「前日-2〜-10%」は同時には成立しない対の条件のため、
2リストに分けている。空売り候補側の20日・5日騰落率条件は、前島さんの原案に
下落側の数値が無かったため、上昇側条件をミラーして補完したもの。

共通条件
  - 東証プライム市場・スタンダード市場の内国普通株式（母集団は data/master/universe.csv）
  - 貸借銘柄（信用区分=貸借銘柄。空売りも可能な銘柄に限定。data/master/margin_list.csv）
  - 株価           500円以上
  - 売買代金       50億円以上（直近終値 × 直近出来高）
  - 出来高増加傾向 直近5日平均出来高 > 直近20日平均出来高

買い候補（上昇モメンタム）
  - 前日騰落率     +2%  〜 +10%
  - 20日騰落率     +10% 以上
  - 5日騰落率      +5%  以上

空売り候補（下落モメンタム）
  - 前日騰落率     -10% 〜 -2%
  - 20日騰落率     -10% 以下
  - 5日騰落率      -5%  以下

時価総額500億円以上の銘柄は除外せず、一覧の表示順で優先する（is_large_cap列）。
条件はユニバース全銘柄に機械的・網羅的に適用し、算出不能（株価履歴が20日分に
満たない新規上場銘柄等）は「算出不能により対象外」として件数を記録する。

出力
  output/daytrade_buy_YYYY-MM-DD.csv        買い候補（全件）
  output/daytrade_short_YYYY-MM-DD.csv      空売り候補（全件）
  output/daytrade_all_judgements_YYYY-MM-DD.csv.gz  ユニバース全銘柄の判定内訳（gzip）
  output/daytrade_summary_YYYY-MM-DD.json   件数サマリと閾値
"""

import argparse
import datetime as dt
import json
import sys
import warnings

import pandas as pd

from config import MASTER_DIR, OUTPUT_DIR, SNAPSHOT_DIR

warnings.filterwarnings("ignore")

PRICE_MIN = 500.0
TURNOVER_MIN = 5_000_000_000.0  # 売買代金 50億円
LARGE_CAP_MIN = 50_000_000_000.0  # 時価総額 500億円（フィルタではなく優先表示に使う）

BUY_THRESHOLDS = {
    "change_1d_min": 2.0, "change_1d_max": 10.0,
    "change_20d_min": 10.0, "change_5d_min": 5.0,
}
SHORT_THRESHOLDS = {
    "change_1d_min": -10.0, "change_1d_max": -2.0,
    "change_20d_max": -10.0, "change_5d_max": -5.0,
}


def fetch_ohlcv(codes: list, batch: int = 150) -> pd.DataFrame:
    """
    直近2か月のOHLCVを一括取得し、株価・騰落率・出来高の指標を算出する。

    20日騰落率の算出には直近21営業日分の終値が必要。2か月（≒40営業日前後）
    あれば祝日を挟んでも十分な余裕がある。取得できた日数が足りない銘柄
    （新規上場間もない銘柄等）は算出不能としてNoneを返す。
    """
    import yfinance as yf

    rows = []
    for i in range(0, len(codes), batch):
        tickers = [f"{c}.T" for c in codes[i: i + batch]]
        data = yf.download(tickers, period="2mo", progress=False,
                           auto_adjust=False, group_by="ticker", threads=True)
        available = set(data.columns.get_level_values(0))
        for t in tickers:
            if t not in available:
                continue
            sub = data[t]
            close = sub["Close"].dropna() if "Close" in sub else pd.Series(dtype=float)
            volume = sub["Volume"].dropna() if "Volume" in sub else pd.Series(dtype=float)
            rows.append({
                "sec_code": t[:-2],
                "price": _last(close),
                "change_1d_pct": _pct_change(close, 1),
                "change_5d_pct": _pct_change(close, 5),
                "change_20d_pct": _pct_change(close, 20),
                "volume": _last(volume),
                "vol_avg5": _mean_tail(volume, 5),
                "vol_avg20": _mean_tail(volume, 20),
            })
        print(f"  株価・出来高取得 [{min(i + batch, len(codes))}/{len(codes)}]")
    return pd.DataFrame(rows)


def _last(s: pd.Series):
    return float(s.iloc[-1]) if len(s) else None


def _pct_change(s: pd.Series, n: int):
    if len(s) <= n:
        return None
    return float((s.iloc[-1] / s.iloc[-1 - n] - 1) * 100)


def _mean_tail(s: pd.Series, n: int):
    if len(s) < n:
        return None
    return float(s.iloc[-n:].mean())


def compute(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df["turnover_yen"] = df["price"] * df["volume"]
    df["volume_rising"] = (df["vol_avg5"] > df["vol_avg20"]).where(
        df["vol_avg5"].notna() & df["vol_avg20"].notna())
    df["market_cap"] = df["price"] * df["shares_issued"]
    df["is_large_cap"] = (df["market_cap"] >= LARGE_CAP_MIN).fillna(False)

    common_cols = ["price", "turnover_yen", "volume_rising"]
    common_missing = df[common_cols].isna().any(axis=1)
    common_ok = (
        (df["price"] >= PRICE_MIN)
        & (df["turnover_yen"] >= TURNOVER_MIN)
        & (df["volume_rising"] == True)  # noqa: E712
        & (df["is_margin"] == True)  # noqa: E712
    )

    change_cols = ["change_1d_pct", "change_5d_pct", "change_20d_pct"]
    change_missing = df[change_cols].isna().any(axis=1)

    buy_ok = (
        (df["change_1d_pct"] >= BUY_THRESHOLDS["change_1d_min"])
        & (df["change_1d_pct"] <= BUY_THRESHOLDS["change_1d_max"])
        & (df["change_20d_pct"] >= BUY_THRESHOLDS["change_20d_min"])
        & (df["change_5d_pct"] >= BUY_THRESHOLDS["change_5d_min"])
    )
    short_ok = (
        (df["change_1d_pct"] >= SHORT_THRESHOLDS["change_1d_min"])
        & (df["change_1d_pct"] <= SHORT_THRESHOLDS["change_1d_max"])
        & (df["change_20d_pct"] <= SHORT_THRESHOLDS["change_20d_max"])
        & (df["change_5d_pct"] <= SHORT_THRESHOLDS["change_5d_max"])
    )

    missing = common_missing | change_missing
    df["result_buy"] = "不通過"
    df.loc[missing, "result_buy"] = "算出不能により対象外"
    df.loc[~missing & common_ok & buy_ok, "result_buy"] = "候補"

    df["result_short"] = "不通過"
    df.loc[missing, "result_short"] = "算出不能により対象外"
    df.loc[~missing & common_ok & short_ok, "result_short"] = "候補"

    return df


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--no-fetch", action="store_true",
                   help="株価を再取得せず data/snapshot/daytrade_prices.csv を使う")
    args = p.parse_args()

    universe = pd.read_csv(MASTER_DIR / "universe.csv", dtype={"code": str})
    universe = universe.rename(columns={"code": "sec_code"})
    print(f"ユニバース: {len(universe)}件")

    margin_path = MASTER_DIR / "margin_list.csv"
    if not margin_path.exists():
        print("ERROR: margin_list.csv がありません。先に fetch_margin_list.py を"
              "実行してください。", file=sys.stderr)
        return 1
    margin = pd.read_csv(margin_path, dtype={"code": str})
    margin_codes = set(margin["code"])
    universe["is_margin"] = universe["sec_code"].isin(margin_codes)
    print(f"貸借銘柄: {universe['is_margin'].sum()}件")

    fin_path = SNAPSHOT_DIR / "financials.csv"
    shares = pd.DataFrame(columns=["sec_code", "shares_issued"])
    if fin_path.exists():
        fin = pd.read_csv(fin_path, dtype={"sec_code": str})
        if "shares_issued" in fin.columns:
            shares = fin[fin["sec_code"].notna()][["sec_code", "shares_issued"]]
    universe = universe.merge(shares, on="sec_code", how="left")

    price_path = SNAPSHOT_DIR / "daytrade_prices.csv"
    if args.no_fetch and price_path.exists():
        market = pd.read_csv(price_path, dtype={"sec_code": str})
    else:
        print("株価・出来高を取得します...")
        market = fetch_ohlcv(sorted(universe["sec_code"].unique()))
        SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
        market.to_csv(price_path, index=False, encoding="utf-8-sig")
    print(f"株価取得: {market['price'].notna().sum()}件")

    df = universe.merge(market, on="sec_code", how="left")
    df = compute(df)

    today = dt.date.today().isoformat()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    cols = ["sec_code", "name", "market", "sector33", "price", "change_1d_pct",
            "change_5d_pct", "change_20d_pct", "volume", "turnover_yen",
            "volume_rising", "market_cap", "is_large_cap"]

    def _sorted(result_col: str, ascending: bool) -> pd.DataFrame:
        passed = df[df[result_col] == "候補"].copy()
        passed = passed.sort_values(
            ["is_large_cap", "change_5d_pct"], ascending=[False, ascending])
        return passed

    buy = _sorted("result_buy", ascending=False)
    short = _sorted("result_short", ascending=True)

    buy[cols].to_csv(OUTPUT_DIR / f"daytrade_buy_{today}.csv",
                     index=False, encoding="utf-8-sig")
    short[cols].to_csv(OUTPUT_DIR / f"daytrade_short_{today}.csv",
                       index=False, encoding="utf-8-sig")
    df.sort_values("sec_code").to_csv(
        OUTPUT_DIR / f"daytrade_all_judgements_{today}.csv.gz",
        index=False, encoding="utf-8-sig", compression="gzip")

    summary = {
        "基準日": today,
        "対象ユニバース": "東証プライム市場・スタンダード市場の内国普通株式",
        "母集団件数": int(len(df)),
        "貸借銘柄件数": int(df["is_margin"].sum()),
        "買い候補": int((df["result_buy"] == "候補").sum()),
        "空売り候補": int((df["result_short"] == "候補").sum()),
        "算出不能により対象外": int((df["result_buy"] == "算出不能により対象外").sum()),
        "共通閾値": {
            "株価下限": PRICE_MIN,
            "売買代金下限": TURNOVER_MIN,
            "時価総額優先表示ライン": LARGE_CAP_MIN,
        },
        "買い候補閾値": BUY_THRESHOLDS,
        "空売り候補閾値": SHORT_THRESHOLDS,
    }
    (OUTPUT_DIR / f"daytrade_summary_{today}.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n" + json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"\n買い候補 {len(buy)}件 -> output/daytrade_buy_{today}.csv")
    print(f"空売り候補 {len(short)}件 -> output/daytrade_short_{today}.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
