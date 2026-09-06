"""
デイトレード用スクリーニング①（上昇モメンタム）が実際に機能するかを検証する、
本日以降の前向き（フォワード）シミュレーション。dividend-siteのequity_sim.pyと同じ
「導入日以降のみ積み上げる」設計（過去に遡ったバックテストではなく、後知恵バイアスを避ける）。

売買ルール（ユーザー確認済み、2026-09-01）
  1. エントリー: 当日の上昇モメンタム条件通過銘柄（output/daytrade_buy_{date}.csv）を、
     既にオープンポジションが無ければ、前場終値（11:30 JST時点の直近5分足終値）で
     成行エントリーする。
  2. 利食い: 後場（12:30 JST以降）の5分足で、株価がエントリー時点の
     「前日騰落率」（change_1d_pct）分だけ上昇した水準（＝targetPrice）に達したら、
     その水準（targetPrice）で手仕舞う。
  3. 損切り: 利食いに該当せず、後場終値（大引け、15:00 JST時点の終値）が
     エントリー株価より5%以上下落していたら、後場終値で手仕舞う。
  4. 保有上限: 2・3いずれにも該当しなかった場合、その日は持ち越し、翌営業日の
     前場終値で強制的に手仕舞う（プラス圏で利食い未達の場合も同様。保有は最大1泊）。

  各ポジションは高々「エントリー当日の後場」＋「翌営業日の前場」までしか存続しない。
  優先順位は 2(利食い) → 3(損切り) → 4(保有上限)。

  このスクリーニングは自動売買や投資判断そのものではなく、あらかじめ固定した
  機械的ルールでの仮想売買実績を検証目的で記録するものです。手数料・税金・
  スリッページ・資金制約は考慮していません。

実行タイミング: 後場の取引時間終了後（15:00 JST以降）に1日1回実行する想定。
  当日の5分足（前場・後場とも）が出そろっている必要がある。

出力
  data/daytrade-sim-state.json  状態の正本。page.tsx がビルド時にこのファイルを
                                直接読み込む（dividend-site/scripts/equity_sim.py と
                                同じ設計だが、会員限定配信が無いため公開用の複製は作らない）。
"""

from __future__ import annotations

import datetime as dt
import json
import sys
from zoneinfo import ZoneInfo

import pandas as pd

from config import OUTPUT_DIR, ROOT
from market_data import fetch_ohlcv_batched

STATE_PATH = ROOT / "data" / "daytrade-sim-state.json"

STOP_LOSS_PCT = -5.0
JST = ZoneInfo("Asia/Tokyo")
MORNING_CLOSE_TIME = dt.time(11, 30)
AFTERNOON_START_TIME = dt.time(12, 30)
NIKKEI_TICKER = "^N225"
TOPIX_TICKER = "1306.T"  # NEXT FUNDS TOPIX連動型上場投信（equity_sim.pyと同じ代用）


def _load_state() -> dict:
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001 - 壊れていれば初期化からやり直す
            pass
    return {"startDate": None, "positions": [], "equityCurve": [], "nikkei": [], "topix": []}


def fetch_intraday(codes: list[str]) -> dict[str, pd.DataFrame]:
    """codesごとに当日の5分足（JST変換済み、時刻でソート済み）を返す。
    データが無い銘柄（新規上場直後・取得失敗等）はキーごと省略する。"""
    if not codes:
        return {}
    long_df = fetch_ohlcv_batched(codes, period="1d", interval="5m")
    if long_df.empty or "Datetime" not in long_df.columns:
        return {}
    out = {}
    for code, g in long_df.groupby("sec_code"):
        g = g.dropna(subset=["Close"]).sort_values("Datetime")
        if g.empty:
            continue
        g = g.copy()
        g["Datetime"] = g["Datetime"].dt.tz_convert(JST)
        out[code] = g
    return out


def morning_close_price(df: pd.DataFrame) -> float | None:
    morning = df[df["Datetime"].dt.time <= MORNING_CLOSE_TIME]
    if morning.empty:
        return None
    return float(morning["Close"].iloc[-1])


def day_close_price(df: pd.DataFrame) -> float | None:
    if df.empty:
        return None
    return float(df["Close"].iloc[-1])


def target_hit_price(df: pd.DataFrame, target_price: float) -> float | None:
    """後場の5分足でHigh(高値)がtarget_price以上になった最初のバーがあれば
    target_priceそのものを返す（その水準で約定したとみなす）。"""
    afternoon = df[df["Datetime"].dt.time >= AFTERNOON_START_TIME]
    hit = afternoon[afternoon["High"] >= target_price]
    return target_price if not hit.empty else None


def fetch_index_close(ticker: str) -> float | None:
    import yfinance as yf

    try:
        d = yf.download(ticker, period="1d", interval="1d", progress=False, auto_adjust=False)
    except Exception:  # noqa: BLE001 - 取得失敗時はこの日の記録を諦める
        return None
    if d.empty:
        return None
    close = d["Close"].iloc[-1]
    return float(close.item() if hasattr(close, "item") else close)


def _append_point(series: list[dict], as_of_date: str, price: float) -> None:
    if series and series[-1].get("date") == as_of_date:
        series[-1]["price"] = price
    else:
        series.append({"date": as_of_date, "price": price})


def run(as_of_date: str) -> dict:
    state = _load_state()
    if state.get("startDate") is None:
        state["startDate"] = as_of_date

    positions: list[dict] = state.get("positions", [])
    open_positions = [p for p in positions if p["status"] == "open"]
    open_codes = {p["code"] for p in open_positions}

    buy_path = OUTPUT_DIR / f"daytrade_buy_{as_of_date}.csv"
    if not buy_path.exists():
        print(f"ERROR: {buy_path} がありません。先に screen_daytrade.py を実行してください。",
              file=sys.stderr)
        sys.exit(1)
    buy_list = pd.read_csv(buy_path, dtype={"sec_code": str}).set_index("sec_code")

    entry_candidates = [c for c in buy_list.index if c not in open_codes]
    fetch_codes = sorted(set(open_codes) | set(entry_candidates))
    print(f"対象銘柄: 保有中{len(open_codes)}件 + 新規候補{len(entry_candidates)}件"
          f"（重複除き{len(fetch_codes)}件）の当日5分足を取得します...")
    intraday = fetch_intraday(fetch_codes)

    # 1) 保有中ポジション（前営業日以前にエントリー済み）は、本日の前場終値で
    #    強制的に手仕舞う（ルール4: 保有上限＝最大1泊）。
    for pos in open_positions:
        df = intraday.get(pos["code"])
        if df is None:
            continue  # データ取得不能。次回実行時に再判定する
        price = morning_close_price(df)
        if price is None:
            continue
        pos["status"] = "closed"
        pos["exitDate"] = as_of_date
        pos["exitPrice"] = price
        pos["exitReason"] = "maxHold"
        pos["returnPct"] = (price - pos["entryPrice"]) / pos["entryPrice"] * 100.0

    # 2) 新規エントリー: 前場終値で建て、同日の後場中に利食い・損切り判定まで行う。
    for code in entry_candidates:
        df = intraday.get(code)
        if df is None:
            continue
        entry_price = morning_close_price(df)
        if entry_price is None or entry_price <= 0:
            continue
        change_1d_pct = float(buy_list.loc[code, "change_1d_pct"])
        target_price = entry_price * (1 + change_1d_pct / 100.0)

        position = {
            "id": f"{code}-{as_of_date}",
            "code": code,
            "name": str(buy_list.loc[code, "name"]),
            "sector": str(buy_list.loc[code, "sector33"]),
            "entryDate": as_of_date,
            "entryPrice": entry_price,
            "targetPrice": target_price,
            "changeOnEntryDay1dPct": change_1d_pct,
            "status": "open",
            "exitDate": None,
            "exitPrice": None,
            "exitReason": None,
            "returnPct": None,
        }

        hit_price = target_hit_price(df, target_price)
        close_price = day_close_price(df)
        if hit_price is not None:
            position.update(status="closed", exitDate=as_of_date, exitPrice=hit_price,
                            exitReason="target",
                            returnPct=(hit_price - entry_price) / entry_price * 100.0)
        elif close_price is not None and (close_price - entry_price) / entry_price * 100.0 <= STOP_LOSS_PCT:
            position.update(status="closed", exitDate=as_of_date, exitPrice=close_price,
                            exitReason="stopLoss",
                            returnPct=(close_price - entry_price) / entry_price * 100.0)
        # どちらでもなければ status="open" のまま（翌営業日の前場終値で手仕舞う）

        positions.append(position)

    # 3) 本日時点の集計
    returns = []
    win = loss = 0
    for pos in positions:
        if pos["status"] == "closed":
            returns.append(pos["returnPct"])
            if pos["returnPct"] >= 0:
                win += 1
            else:
                loss += 1
        else:
            df = intraday.get(pos["code"])
            close_price = day_close_price(df) if df is not None else None
            if close_price is not None:
                returns.append((close_price - pos["entryPrice"]) / pos["entryPrice"] * 100.0)

    avg_return = sum(returns) / len(returns) if returns else 0.0
    open_count = sum(1 for p in positions if p["status"] == "open")
    closed_count = sum(1 for p in positions if p["status"] == "closed")

    curve: list[dict] = [c for c in state.get("equityCurve", []) if c.get("date") != as_of_date]
    curve.append({
        "date": as_of_date,
        "avgReturnPct": avg_return,
        "openCount": open_count,
        "closedCount": closed_count,
        "winCount": win,
        "lossCount": loss,
    })

    nikkei: list[dict] = state.get("nikkei", [])
    nikkei_price = fetch_index_close(NIKKEI_TICKER)
    if nikkei_price is not None:
        _append_point(nikkei, as_of_date, nikkei_price)

    topix: list[dict] = state.get("topix", [])
    topix_price = fetch_index_close(TOPIX_TICKER)
    if topix_price is not None:
        _append_point(topix, as_of_date, topix_price)

    state["positions"] = positions
    state["equityCurve"] = curve
    state["nikkei"] = nikkei
    state["topix"] = topix
    state["lastUpdated"] = as_of_date

    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

    return state


def main() -> int:
    as_of_date = dt.datetime.now(JST).date().isoformat()
    state = run(as_of_date)
    latest = state["equityCurve"][-1]
    print(f"\n{as_of_date} 更新完了: 保有中{latest['openCount']}件 / "
          f"決済済み{latest['closedCount']}件（勝ち{latest['winCount']}・負け{latest['lossCount']}） "
          f"/ 平均リターン{latest['avgReturnPct']:.2f}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
