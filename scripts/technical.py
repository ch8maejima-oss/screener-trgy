"""
スイング②（ROE・PBR整合性チェッカー）用のテクニカル指標。

ユーザー原案の技術的表現（「反転」「底値圏」等）は主観的な言い回しのため、
以下の通り機械的な定義に落とし込んでいる（tenbagger・daytradeの既存スクリーニングと
同様、閾値の妥当性は継続検証が必要という前提）。

  - ゴールデンクロス: 前日は5日移動平均線 < 25日移動平均線、当日は5日移動平均線
    ≥ 25日移動平均線となった、その「切り替わった日」のみを検知する
    （既にクロス済みの状態が続いているだけの日は対象外）。
  - 25日移動平均線の反転: 25日移動平均線が5営業日前まで下落基調
    （10営業日前→5営業日前で下落）だったものが、直近5営業日で下落していない
    （5営業日前→当日で下落していない）状態に転じた日。
  - 出来高急増（底値圏）: 「底値圏」を、直近60営業日高値から20%以上下落した
    水準にあることと定義する。この水準で、当日出来高が前日比2倍以上、かつ
    陽線（終値>始値）だった日を検知する。
"""

from __future__ import annotations

import pandas as pd

TROUGH_DRAWDOWN_PCT = 20.0  # 底値圏の判定: 直近60営業日高値からの下落率
TROUGH_LOOKBACK_DAYS = 60
VOLUME_SPIKE_RATIO = 2.0
RSI_WINDOW = 14
RSI_OVERBOUGHT = 75.0
BOLLINGER_WINDOW = 20
BOLLINGER_NUM_STD = 2.0


def sma(close: pd.Series, window: int) -> pd.Series:
    return close.rolling(window).mean()


def golden_cross_today(close: pd.Series) -> bool:
    """直近日が5日線と25日線のゴールデンクロスの発生日そのものかどうか。"""
    ma5, ma25 = sma(close, 5), sma(close, 25)
    if len(close) < 26 or ma5.iloc[-2:].isna().any() or ma25.iloc[-2:].isna().any():
        return False
    was_below = ma5.iloc[-2] < ma25.iloc[-2]
    now_above_or_equal = ma5.iloc[-1] >= ma25.iloc[-1]
    return bool(was_below and now_above_or_equal)


def ma25_reversal_today(close: pd.Series) -> bool:
    """25日移動平均線が下落基調から反転した日かどうか（定義はモジュールdocstring参照）。"""
    ma25 = sma(close, 25)
    if len(ma25) < 36 or ma25.iloc[-11:].isna().any():
        return False
    was_declining = ma25.iloc[-6] < ma25.iloc[-11]
    now_not_declining = ma25.iloc[-1] >= ma25.iloc[-6]
    return bool(was_declining and now_not_declining)


def in_trough_zone_today(close: pd.Series) -> bool:
    if len(close) < TROUGH_LOOKBACK_DAYS:
        return False
    recent_high = close.iloc[-TROUGH_LOOKBACK_DAYS:].max()
    if recent_high <= 0:
        return False
    drawdown_pct = (recent_high - close.iloc[-1]) / recent_high * 100
    return bool(drawdown_pct >= TROUGH_DRAWDOWN_PCT)


def volume_spike_today(open_: pd.Series, close: pd.Series, volume: pd.Series) -> bool:
    """底値圏で、前日比2倍以上の出来高を伴う陽線が出た日かどうか。"""
    if len(volume) < 2 or pd.isna(volume.iloc[-1]) or pd.isna(volume.iloc[-2]) or volume.iloc[-2] <= 0:
        return False
    is_bullish = close.iloc[-1] > open_.iloc[-1]
    is_spike = volume.iloc[-1] >= volume.iloc[-2] * VOLUME_SPIKE_RATIO
    return bool(is_bullish and is_spike and in_trough_zone_today(close))


def rsi(close: pd.Series, window: int = RSI_WINDOW) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window).mean()
    avg_loss = loss.rolling(window).mean()
    rs = avg_gain / avg_loss.replace(0, pd.NA)
    return 100 - (100 / (1 + rs))


def rsi_overbought_today(close: pd.Series) -> bool:
    r = rsi(close)
    if r.empty or pd.isna(r.iloc[-1]):
        return False
    return bool(r.iloc[-1] >= RSI_OVERBOUGHT)


def bollinger_upper_touch_today(close: pd.Series) -> bool:
    """当日終値がボリンジャーバンド+2σ以上に達しているかどうか。"""
    if len(close) < BOLLINGER_WINDOW:
        return False
    mean = close.rolling(BOLLINGER_WINDOW).mean().iloc[-1]
    std = close.rolling(BOLLINGER_WINDOW).std().iloc[-1]
    if pd.isna(mean) or pd.isna(std):
        return False
    upper = mean + BOLLINGER_NUM_STD * std
    return bool(close.iloc[-1] >= upper)


def entry_technical_signal(df: pd.DataFrame) -> str | None:
    """条件④（4種のうち1つ以上）を満たすか判定し、満たした最初のシグナル名を返す。
    dfは日次OHLCV（Open, Close, Volume列、日付昇順）。満たさなければNone。"""
    if golden_cross_today(df["Close"]):
        return "goldenCross"
    if ma25_reversal_today(df["Close"]):
        return "ma25Reversal"
    if volume_spike_today(df["Open"], df["Close"], df["Volume"]):
        return "volumeSpike"
    return None


def exit_technical_signal(close: pd.Series) -> str | None:
    """利確条件④（RSI過熱 or ボリンジャーバンド上限タッチ）を満たすか判定する。"""
    if rsi_overbought_today(close):
        return "rsiOverbought"
    if bollinger_upper_touch_today(close):
        return "bollingerUpper"
    return None
