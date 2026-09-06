"""共有Yahoo Finance日次取得レイヤー。

screen.py・screen_daytrade.py・screen_tenbagger.pyがそれぞれ独立に
`yf.download(period="1y", actions=True, ...)`相当の日次OHLCV+配当を取得しており
（screen_tenbagger.pyはscreen.pyのfetch_market_data経由で、実質同一銘柄・同一期間の
リクエストを完全に重複して発生させていた）、日次バッチ内でYahoo Financeへ最大3回
アクセスしていた問題を解消するための共通モジュール。

日次バッチの最初にfetch_daily_prices.pyが1回だけ全銘柄分の1年分日次OHLCVを取得して
data/snapshot/daily_ohlcv_1y.csv.gzへキャッシュし、screen.py・screen_daytrade.pyは
このキャッシュを読んで必要な範囲を集計するだけにする（screen_tenbagger.pyはscreen.pyの
fetch_market_data経由で自動的にキャッシュ経由になるため、この差し替え自体では変更不要）。

対象外: screen_tenbagger.pyのfetch_listing_dates（月足・全期間で上場年月を近似する処理）は
時間軸が数十年に及び、1年分の日次キャッシュでは代替できないため、この共有キャッシュの
対象にはしない（バッチ分割ループ自体はfetch_ohlcv_batchedを再利用する）。
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pandas as pd

from config import SNAPSHOT_DIR

DAILY_CACHE_PATH = SNAPSHOT_DIR / "daily_ohlcv_1y.csv.gz"


def fetch_ohlcv_batched(codes: list[str], batch: int = 150, **yf_kwargs) -> pd.DataFrame:
    """codesをbatch件ずつに分けてyf.downloadし、long形式
    （sec_code, date, Open, High, Low, Close, Volume, Dividends...）に整形して結合する。
    screen.py・screen_daytrade.py・screen_tenbagger.pyのfetch_*関数に重複していた
    バッチ分割ループの共通化。yf_kwargsはそのままyf.download()に渡す
    （period="1y", actions=True 等、呼び出し側の用途に応じて指定する）。
    """
    import yfinance as yf

    frames = []
    for i in range(0, len(codes), batch):
        tickers = [f"{c}.T" for c in codes[i: i + batch]]
        data = yf.download(tickers, group_by="ticker", threads=True, progress=False, **yf_kwargs)
        available = set(data.columns.get_level_values(0))
        for t in tickers:
            if t not in available:
                continue
            sub = data[t].dropna(how="all")
            if sub.empty:
                continue
            sub = sub.reset_index().rename(columns={"Date": "date"})
            sub.insert(0, "sec_code", t[:-2])
            frames.append(sub)
        print(f"  株価取得 [{min(i + batch, len(codes))}/{len(codes)}]")

    if not frames:
        return pd.DataFrame(columns=["sec_code", "date"])
    return pd.concat(frames, ignore_index=True)


def build_daily_cache(codes: list[str]) -> pd.DataFrame:
    """1年分の日次OHLCV+配当をcodes全件についてまとめて取得し、キャッシュに書き出す。"""
    df = fetch_ohlcv_batched(codes, period="1y", actions=True, auto_adjust=False)
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(DAILY_CACHE_PATH, index=False, encoding="utf-8-sig", compression="gzip")
    return df


def load_daily_cache(codes: list[str] | None = None) -> pd.DataFrame:
    """当日分のキャッシュを読む。ファイルが無ければ空DataFrameを返す
    （呼び出し側で「先にfetch_daily_prices.pyを実行してください」等のエラーを出す想定）。
    """
    if not DAILY_CACHE_PATH.exists():
        return pd.DataFrame(columns=["sec_code", "date"])
    df = pd.read_csv(DAILY_CACHE_PATH, dtype={"sec_code": str}, parse_dates=["date"])
    if codes is not None:
        df = df[df["sec_code"].isin(codes)]
    return df


def is_fresh_today(path: Path) -> bool:
    """pathの更新日が今日かどうか（当日分のキャッシュとして使えるか）。"""
    if not path.exists():
        return False
    mtime = dt.date.fromtimestamp(path.stat().st_mtime)
    return mtime == dt.date.today()
