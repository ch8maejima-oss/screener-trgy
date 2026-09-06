"""
スイング①（期待リターン逆算）用: 個別銘柄のβ（対1306.T、5年月次リターン回帰）を算出する。

Yahoo Financeの日次終値に、前後の日と比べて明らかにおかしい単発の異常値が
混入することを実データで確認した（例: 1306.T の2026-03-30/31が本来380円前後の
ところ36円台になっていた）。市場代理指標(1306.T)のこの系列は全銘柄のβ計算で
共有するため、ここが汚染されると全銘柄のβが同時に壊れる。月次終値化する前に
despike()で単発の異常値を除去する。

βは市場環境の急変が無い限り短期間で大きくは動かないため、日次では再計算せず
data/snapshot/beta.csv に永続キャッシュし、まだキャッシュに無い銘柄
（新規上場等）の分だけ追加取得する（screen_tenbagger.pyのlisting_dates.csvと
同じ運用方針）。まとめて再計算したい場合は screen_swing1.py --refresh-beta を使う。

使い方:
    python3 scripts/beta.py --codes 6457,4820   # 動作確認用
"""

from __future__ import annotations

import argparse
import sys

import pandas as pd

from market_data import fetch_ohlcv_batched

MARKET_PROXY_CODE = "1306"  # TOPIX連動型上場投信（野村アセットマネジメント）
LOOKBACK_PERIOD = "5y"
MIN_MONTHLY_OBS = 24  # 上場間もない銘柄は5年分そろわないため算出不能扱いにする閾値


def despike(series: pd.Series, window: int = 5, threshold: float = 0.5) -> pd.Series:
    """前後合わせてwindow*2+1日の中央値と比べ、threshold倍未満または
    1/threshold倍超の値を異常値とみなし線形補間で置き換える。"""
    med = series.rolling(window * 2 + 1, center=True, min_periods=window + 1).median()
    bad = (series < med * threshold) | (series > med / threshold)
    return series.mask(bad).interpolate(limit_direction="both")


def _monthly_close(codes: list[str]) -> pd.DataFrame:
    df = fetch_ohlcv_batched(codes, period=LOOKBACK_PERIOD, interval="1d")
    series = {}
    for code, g in df.groupby("sec_code"):
        g = g.sort_values("date").set_index("date")
        close = g["Close"].dropna()
        if close.empty:
            continue
        series[code] = despike(close).resample("ME").last()
    return pd.DataFrame(series)


def compute_betas(codes: list[str], min_obs: int = MIN_MONTHLY_OBS) -> pd.DataFrame:
    """codes（証券コード、末尾.T無し）ごとのβを算出する。
    戻り値: DataFrame(sec_code, beta, beta_obs)。算出不能な銘柄はbeta=NaN。"""
    target = sorted(set(codes) | {MARKET_PROXY_CODE})
    monthly = _monthly_close(target)
    if MARKET_PROXY_CODE not in monthly.columns:
        raise SystemExit(
            f"ERROR: 市場代理指標({MARKET_PROXY_CODE}.T)の株価が取得できませんでした。"
        )
    mkt_ret = monthly[MARKET_PROXY_CODE].pct_change()

    rows = []
    for code in codes:
        if code not in monthly.columns:
            rows.append({"sec_code": code, "beta": None, "beta_obs": 0})
            continue
        stk_ret = monthly[code].pct_change()
        joined = pd.concat([stk_ret, mkt_ret], axis=1, keys=["s", "m"]).dropna()
        if len(joined) < min_obs:
            rows.append({"sec_code": code, "beta": None, "beta_obs": len(joined)})
            continue
        var_m = joined["m"].var()
        beta = float(joined["s"].cov(joined["m"]) / var_m) if var_m else None
        rows.append({"sec_code": code, "beta": beta, "beta_obs": len(joined)})
    return pd.DataFrame(rows)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--codes", required=True, help="カンマ区切りの証券コード（動作確認用）")
    args = p.parse_args()
    codes = [c.strip() for c in args.codes.split(",") if c.strip()]
    out = compute_betas(codes)
    print(out.to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
