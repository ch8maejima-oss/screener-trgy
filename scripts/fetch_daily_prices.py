"""日次バッチの最初に1回だけ実行する、1年分日次OHLCV+配当のYahoo Finance取得。

screen.py・screen_daytrade.py・screen_tenbagger.pyがそれぞれ独立に取得していた
（screen_tenbagger.pyはscreen.py経由で完全に重複取得していた）1年分日次データを
ここで1本化する。対象はdata/master/universe.csv（東証プライム・スタンダード全件）で、
screen.py用のfinancials.csv銘柄集合はこの部分集合のため、この全件取得でどちらの
用途もまかなえる。

出力
    data/snapshot/daily_ohlcv_1y.csv.gz  銘柄×日付のlong形式OHLCV+配当

使い方:
    python3 scripts/fetch_daily_prices.py
"""

from __future__ import annotations

import sys

import pandas as pd

from config import MASTER_DIR
from market_data import build_daily_cache


def main() -> int:
    universe_path = MASTER_DIR / "universe.csv"
    if not universe_path.exists():
        print(f"ERROR: {universe_path} がありません。先に build_universe.py を実行してください。",
              file=sys.stderr)
        return 1

    universe = pd.read_csv(universe_path, dtype={"code": str})
    codes = sorted(universe["code"].dropna().unique())
    print(f"対象: {len(codes)}銘柄")

    df = build_daily_cache(codes)
    covered = df["sec_code"].nunique() if not df.empty else 0
    print(f"取得完了: {covered}/{len(codes)}銘柄 -> data/snapshot/daily_ohlcv_1y.csv.gz")
    return 0


if __name__ == "__main__":
    sys.exit(main())
