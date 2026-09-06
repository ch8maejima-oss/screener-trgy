"""
スイング用スクリーニング②「ROE・PBR整合性チェッカー」が実際に機能するかを検証する、
本日以降の前向き（フォワード）シミュレーション。daytrade_sim.py・dividend-siteの
equity_sim.pyと同じ「導入日以降のみ積み上げる」設計。ただし判定は日次終値ベース
（保有期間が最大3ヶ月に及ぶため、daytrade_sim.pyのようなイントラデイ精度は不要）。

売買ルール（ユーザー原案・2026-09-02確認済み）
  エントリー: 当日 screen_swing2.py の全条件充足銘柄（output/swing2_buy_{date}.csv）を、
    既にオープンポジションが無ければ当日終値で建てる。
  利確（全部)  : 実績PBRが理論PBRに到達、または理論PBRとの下方乖離率が5%以内に
    縮小した時点で、保有全量（部分決済済みなら残り全量）を手仕舞う。
  利確（半分・1回のみ）: 以下のいずれかで、まだ部分決済していなければ半分を手仕舞う。
    - 下方乖離率が20%→10%以内まで縮小
    - RSI(14日)が75以上、またはボリンジャーバンド+2σにタッチ
    （両条件を同時に満たしても半分決済は1回のみ。ユーザー原案は「全株または半分」と
      部分決済の粒度が曖昧だったため、半分固定・1回限りと定めた。）
  損切り（価格基準）: 終値が購入株価から7%以上下落した時点で残り全量を手仕舞う。
  保有上限: 購入から3ヶ月（63営業日で近似）経過した時点で、達成状況にかかわらず
    残り全量を手仕舞う。
    （ファンダメンタルズ基準の損切り＝業績予想下方修正の検知は、必要なデータが
      J-Quants API等でしか取得できず、同APIは法人利用を禁止しているため実装しない
      とユーザー確認済み。）

理論PBRはエントリー時点の値に固定する（保有中に業種平均PER・調整後ROEを毎日
再計算すると、目標水準自体が動いてしまい「価格が理論値に収束したか」の検証が
曖昧になるため）。理論PBRに対する実績PBRの乖離は、株価の変動に比例して動く前提で、
エントリー時のPBR・株価との比率から日々再計算する（純資産・発行済株式数は
年1回しか更新されないため、この近似で十分）。

出力
  data/swing2-sim-state.json  状態の正本。page.tsx がビルド時にこのファイルを直接読み込む。
"""

from __future__ import annotations

import datetime as dt
import json
import sys

import pandas as pd

import technical as tech
from config import OUTPUT_DIR, ROOT
from market_data import load_daily_cache

STATE_PATH = ROOT / "data" / "swing2-sim-state.json"

STOP_LOSS_PCT = -7.0
TARGET_DEVIATION_MAX_PCT = 5.0  # これ以下に縮小したら全部利確
PARTIAL_DEVIATION_MAX_PCT = 10.0  # これ以下に縮小したら半分利確（初回のみ）
MAX_HOLD_BUSINESS_DAYS = 63  # 3ヶ月の近似（21営業日/月 x 3）


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


def _current_deviation_pct(pos: dict, current_price: float) -> float:
    """エントリー時のPBR・理論PBRを基準に、株価の変動比率だけを反映して
    現在の下方乖離率を近似する（純資産・発行済株式数は年1回更新のため）。"""
    price_ratio = current_price / pos["entryPrice"]
    current_pbr = pos["entryPbr"] * price_ratio
    theoretical = pos["theoreticalPbr"]
    return (theoretical - current_pbr) / theoretical * 100.0


def _return_pct(entry_price: float, exit_price: float) -> float:
    return (exit_price - entry_price) / entry_price * 100.0


def _weighted_return(pos: dict, current_price: float | None) -> float | None:
    """部分決済を考慮した加重平均リターン。closedならexitPrice、openなら
    current_priceを残り分の評価に使う。"""
    if pos.get("partialExitPrice") is not None:
        partial_r = _return_pct(pos["entryPrice"], pos["partialExitPrice"])
        remaining_price = pos["exitPrice"] if pos["status"] == "closed" else current_price
        if remaining_price is None:
            return partial_r  # 残り分の当日価格が取れない場合は部分決済分のみで代用
        remaining_r = _return_pct(pos["entryPrice"], remaining_price)
        return partial_r * 0.5 + remaining_r * 0.5
    final_price = pos["exitPrice"] if pos["status"] == "closed" else current_price
    if final_price is None:
        return None
    return _return_pct(pos["entryPrice"], final_price)


def run(as_of_date: str) -> dict:
    state = _load_state()
    if state.get("startDate") is None:
        state["startDate"] = as_of_date

    positions: list[dict] = state.get("positions", [])
    open_positions = [p for p in positions if p["status"] == "open"]
    open_codes = {p["code"] for p in open_positions}

    buy_path = OUTPUT_DIR / f"swing2_buy_{as_of_date}.csv"
    if not buy_path.exists():
        print(f"ERROR: {buy_path} がありません。先に screen_swing2.py を実行してください。",
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

    # 1) 保有中ポジションの判定（利確全部→損切り→利確半分(初回のみ)→保有上限の優先順）
    for pos in open_positions:
        price = latest_close(pos["code"])
        if price is None:
            continue
        deviation = _current_deviation_pct(pos, price)
        entry_date = dt.datetime.strptime(pos["entryDate"], "%Y-%m-%d").date()
        held_days = _business_days_between(entry_date, today)

        target_hit = deviation <= TARGET_DEVIATION_MAX_PCT
        stop_hit = (price - pos["entryPrice"]) / pos["entryPrice"] * 100.0 <= STOP_LOSS_PCT
        already_partial = pos.get("partialExitPrice") is not None
        partial_hit = (not already_partial) and (
            deviation <= PARTIAL_DEVIATION_MAX_PCT
            or tech.exit_technical_signal(daily_by_code[pos["code"]]["Close"]) is not None
        )
        max_hold_hit = held_days >= MAX_HOLD_BUSINESS_DAYS

        if target_hit or stop_hit or max_hold_hit:
            pos["status"] = "closed"
            pos["exitDate"] = as_of_date
            pos["exitPrice"] = price
            pos["exitReason"] = "target" if target_hit else ("stopLoss" if stop_hit else "maxHold")
            pos["returnPct"] = _weighted_return(pos, price)
        elif partial_hit:
            pos["partialExitDate"] = as_of_date
            pos["partialExitPrice"] = price
            pos["partialExitReason"] = (
                "deviationNarrowed" if deviation <= PARTIAL_DEVIATION_MAX_PCT else "technical"
            )
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
            "entryPbr": float(row["pbr"]),
            "theoreticalPbr": float(row["theoretical_pbr"]),
            "lowerDeviationPctAtEntry": float(row["lower_deviation_pct"]),
            "status": "open",
            "partialExitDate": None,
            "partialExitPrice": None,
            "partialExitReason": None,
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
