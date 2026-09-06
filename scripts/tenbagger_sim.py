"""
テンバガー候補銘柄一覧が実際に機能するかを検証する、本日以降の前向き（フォワード）
シミュレーション。daytrade_sim.py・swing2_sim.pyと同じ「導入日以降のみ積み上げる」
設計（過去に遡ったバックテストではなく、後知恵バイアスを避ける）。判定は日次終値
ベース（保有期間が最大5年に及ぶため、daytrade_sim.pyのようなイントラデイ精度は不要。
swing2_sim.pyと同じ粒度）。

売買ルール（ユーザー確認済み、2026-09-06）
  エントリー: 当日 screen_tenbagger.py の8/9条件以上充足銘柄（output/tenbagger_{date}.csv）を、
    既にオープンポジションが無ければ当日終値で建てる。
  利確（1回目・1/3）: 実績株価がエントリー株価の3倍に到達した時点で、保有の1/3を手仕舞う。
  利確（2回目・1/3）: 1回目の利確が済んでいる状態で、実績株価がエントリー株価の6倍に
    到達した時点で、さらに1/3（＝残り2/3のうちの半分）を手仕舞う。
  利確（最終・残り全量）: 実績株価がエントリー株価の10倍に到達した時点で、その時点で
    残っている数量をすべて手仕舞う（1回目・2回目の利確を経ずに直接10倍に到達した場合も
    同様に残り全量を手仕舞う。日次終値のみでの判定のため、途中の水準を飛び越えた場合に
    実際には通過していない価格帯での利確を遡って計上することはしない）。
  損切り: 終値が購入株価から40%以上下落した時点で、その時点で残っている数量をすべて
    手仕舞う（小型成長株の通常のボラティリティを踏まえ、swing2_sim.pyの-7%よりかなり
    広く設定）。
  保有上限: 購入から5年（1260営業日で近似）経過した時点で、達成状況にかかわらず
    残っている数量をすべて手仕舞う。

  優先順位（1本の終値は下記の帯のいずれか1つにしか該当しないため、実質的に排他的）:
    損切り(<=-40%) > 最終利確(>=10倍) > 2回目利確(>=6倍、1回目済みの場合のみ)
    > 1回目利確(>=3倍、未利確の場合のみ) > 保有上限。

  再スクリーニングで条件から外れても手仕舞い理由にはしない（daytrade_sim.py・
  swing2_sim.pyと同じく、導入時に固定したルールをその後の成績を見て有利になるよう
  変更しない、という方針を踏襲する）。

出力
  data/tenbagger-sim-state.json  状態の正本。page.tsx がビルド時にこのファイルを
                                 直接読み込む。
"""

from __future__ import annotations

import datetime as dt
import json
import sys

import pandas as pd

from config import OUTPUT_DIR, ROOT
from market_data import load_daily_cache

STATE_PATH = ROOT / "data" / "tenbagger-sim-state.json"

STOP_LOSS_PCT = -40.0
PARTIAL1_MULTIPLE = 3.0   # 到達で1/3を利確
PARTIAL2_MULTIPLE = 6.0   # 到達でさらに1/3を利確（1回目済みの場合のみ）
TARGET_MULTIPLE = 10.0    # 到達で残り全量を利確
MAX_HOLD_BUSINESS_DAYS = 1260  # 5年の近似（252営業日/年 x 5）

PARTIAL1_FRACTION = 1 / 3
PARTIAL2_FRACTION = 1 / 3


def _business_days_between(d1: dt.date, d2: dt.date) -> int:
    if d2 <= d1:
        return 0
    days = 0
    cur = d1
    while cur < d2:
        cur += dt.timedelta(days=1)
        if cur.weekday() < 5:
            days += 1
    return days


def _load_state() -> dict:
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            pass
    return {"startDate": None, "positions": [], "equityCurve": []}


def _return_pct(entry_price: float, exit_price: float) -> float:
    return (exit_price - entry_price) / entry_price * 100.0


def _sold_fraction(pos: dict) -> float:
    fraction = 0.0
    if pos.get("partial1ExitPrice") is not None:
        fraction += PARTIAL1_FRACTION
    if pos.get("partial2ExitPrice") is not None:
        fraction += PARTIAL2_FRACTION
    return fraction


def _weighted_return(pos: dict, current_price: float | None) -> float | None:
    """1回目・2回目の部分利確と、残り分（決済済みならexitPrice、保有中なら
    current_priceで評価）を加重平均したリターン。"""
    segments: list[tuple[float, float]] = []
    if pos.get("partial1ExitPrice") is not None:
        segments.append((PARTIAL1_FRACTION, pos["partial1ExitPrice"]))
    if pos.get("partial2ExitPrice") is not None:
        segments.append((PARTIAL2_FRACTION, pos["partial2ExitPrice"]))

    remaining = 1.0 - sum(f for f, _ in segments)
    if pos["status"] == "closed":
        segments.append((remaining, pos["exitPrice"]))
    elif current_price is not None:
        segments.append((remaining, current_price))
    else:
        # 残り分の当日価格が取れない場合は、確定済みの部分決済のみで代用する
        if not segments:
            return None

    entry = pos["entryPrice"]
    return sum(frac * _return_pct(entry, price) for frac, price in segments)


def run(as_of_date: str) -> dict:
    state = _load_state()
    if state.get("startDate") is None:
        state["startDate"] = as_of_date

    positions: list[dict] = state.get("positions", [])
    open_positions = [p for p in positions if p["status"] == "open"]
    open_codes = {p["code"] for p in open_positions}

    buy_path = OUTPUT_DIR / f"tenbagger_{as_of_date}.csv"
    if not buy_path.exists():
        print(f"ERROR: {buy_path} がありません。先に screen_tenbagger.py を実行してください。",
              file=sys.stderr)
        sys.exit(1)
    buy_list = pd.read_csv(buy_path, dtype={"sec_code": str}).set_index("sec_code")

    entry_candidates = [c for c in buy_list.index if c not in open_codes]
    all_codes = sorted(set(open_codes) | set(entry_candidates))
    daily = load_daily_cache(all_codes)
    daily_by_code = {code: g.sort_values("date") for code, g in daily.groupby("sec_code")}

    def latest_close(code: str) -> float | None:
        g = daily_by_code.get(code)
        if g is None or g.empty:
            return None
        return float(g["Close"].iloc[-1])

    today = dt.datetime.strptime(as_of_date, "%Y-%m-%d").date()

    # 1) 保有中ポジションの判定
    #    損切り > 最終利確(10倍) > 2回目利確(6倍) > 1回目利確(3倍) > 保有上限
    for pos in open_positions:
        price = latest_close(pos["code"])
        if price is None:
            continue
        ratio = price / pos["entryPrice"]
        entry_date = dt.datetime.strptime(pos["entryDate"], "%Y-%m-%d").date()
        held_days = _business_days_between(entry_date, today)
        sold = _sold_fraction(pos)

        if ratio <= 1 + STOP_LOSS_PCT / 100.0:
            pos["status"] = "closed"
            pos["exitDate"] = as_of_date
            pos["exitPrice"] = price
            pos["exitReason"] = "stopLoss"
            pos["returnPct"] = _weighted_return(pos, price)
        elif ratio >= TARGET_MULTIPLE:
            pos["status"] = "closed"
            pos["exitDate"] = as_of_date
            pos["exitPrice"] = price
            pos["exitReason"] = "target"
            pos["returnPct"] = _weighted_return(pos, price)
        elif sold == PARTIAL1_FRACTION and ratio >= PARTIAL2_MULTIPLE:
            pos["partial2ExitDate"] = as_of_date
            pos["partial2ExitPrice"] = price
        elif sold == 0.0 and ratio >= PARTIAL1_MULTIPLE:
            pos["partial1ExitDate"] = as_of_date
            pos["partial1ExitPrice"] = price
        elif held_days >= MAX_HOLD_BUSINESS_DAYS:
            pos["status"] = "closed"
            pos["exitDate"] = as_of_date
            pos["exitPrice"] = price
            pos["exitReason"] = "maxHold"
            pos["returnPct"] = _weighted_return(pos, price)
        # いずれにも該当しなければそのまま保有継続

    # 2) 新規エントリー（当日終値で建てる）
    for code in entry_candidates:
        price = latest_close(code)
        if price is None or price <= 0:
            continue
        row = buy_list.loc[code]
        position = {
            "id": f"{code}-{as_of_date}",
            "code": code,
            "name": str(row["name"]),
            "sector": str(row["sector33"]),
            "entryDate": as_of_date,
            "entryPrice": price,
            "status": "open",
            "partial1ExitDate": None,
            "partial1ExitPrice": None,
            "partial2ExitDate": None,
            "partial2ExitPrice": None,
            "exitDate": None,
            "exitPrice": None,
            "exitReason": None,
            "returnPct": None,
        }
        positions.append(position)

    # 3) 本日時点の集計
    returns = []
    win = loss = 0
    for pos in positions:
        current_price = None if pos["status"] == "closed" else latest_close(pos["code"])
        r = _weighted_return(pos, current_price)
        if r is None:
            continue
        returns.append(r)
        if pos["status"] == "closed":
            if r >= 0:
                win += 1
            else:
                loss += 1

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

    state["positions"] = positions
    state["equityCurve"] = curve
    state["lastUpdated"] = as_of_date

    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    return state


def main() -> int:
    as_of_date = dt.date.today().isoformat()
    state = run(as_of_date)
    latest = state["equityCurve"][-1]
    print(f"\n{as_of_date} 更新完了: 保有中{latest['openCount']}件 / "
          f"決済済み{latest['closedCount']}件（勝ち{latest['winCount']}・負け{latest['lossCount']}） "
          f"/ 平均リターン{latest['avgReturnPct']:.2f}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
