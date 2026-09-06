"""
スイング①（期待リターン逆算）用: 現在の株価から市場が織り込んでいる
FCF成長率を逆算する2段階DCFモデル。

前提（ユーザー確認済み、2026-08-31）
  - 割引率(WACC)はCAPMで銘柄ごとに算出する。
      株主資本コスト = 無リスク金利 + β × 株式リスクプレミアム
      負債コスト(税引後) = 支払利息 / 有利子負債 × (1 - 実効税率)
      無リスク金利・株式リスクプレミアム・実効税率は全銘柄共通の固定値
      （config.pyで手動更新する想定）。βは銘柄ごとに5年月次リターンを
      1306.T（TOPIX連動ETF）に回帰して算出する（beta.py）。
  - 予測期間は10年固定。11年目以降はterminal_growth_pctで永久成長すると仮定し
    2段階DCFでEV(企業価値)=時価総額+有利子負債-現金同等物 と一致するよう
    FCF成長率gを二分探索で解く。
  - FCFのベース値(fcf0)はEDINET有報の営業CF − 設備投資額
    （【設備投資等の概要】の開示値をそのまま採用）。投資CFをそのまま使うと、
    現金潤沢企業ほど財務目的の預入・有価証券売買で投資CFが大きく振れ、
    簡易FCFが実態と乖離する（実例: ファーストリテイリングは営業CFと投資CFが
    ほぼ相殺しFCFがほぼ0になっていた）ため採用しなかった。
  - 「10年後想定営業利益」は現在の営業利益を同じgで10年複利成長させた値
    （FCFと営業利益が同率で成長するという単純化した前提）。
"""

from __future__ import annotations

FORECAST_YEARS = 10


def capm_cost_of_equity_pct(beta: float, risk_free_pct: float, erp_pct: float) -> float:
    return risk_free_pct + beta * erp_pct


def cost_of_debt_after_tax_pct(interest_expense: float, interest_bearing_debt: float,
                                tax_rate_pct: float) -> float | None:
    """有利子負債が0（無借金）ならコストも0。負債が無いのにマイナスなど
    不整合な値の場合はNone（呼び出し側で対象外にする）。"""
    if interest_bearing_debt is None or interest_bearing_debt < 0:
        return None
    if interest_bearing_debt == 0:
        return 0.0
    if interest_expense is None:
        return None
    pretax = interest_expense / interest_bearing_debt * 100
    return pretax * (1 - tax_rate_pct / 100)


def wacc_pct(market_cap: float, interest_bearing_debt: float,
             cost_of_equity_pct: float, cost_of_debt_after_tax_pct: float) -> float | None:
    total = market_cap + interest_bearing_debt
    if total is None or total <= 0:
        return None
    w_equity = market_cap / total
    w_debt = interest_bearing_debt / total
    return w_equity * cost_of_equity_pct + w_debt * cost_of_debt_after_tax_pct


def _ev_for_growth(fcf0: float, g: float, wacc: float, terminal_growth: float,
                    years: int = FORECAST_YEARS) -> float:
    """FCFがg（年率）でyears年成長し、その後terminal_growthで永久成長すると
    仮定した場合の企業価値の現在価値。wacc・terminal_growthは小数（0.06=6%）。"""
    pv = 0.0
    fcf = fcf0
    for t in range(1, years + 1):
        fcf = fcf0 * (1 + g) ** t
        pv += fcf / (1 + wacc) ** t
    terminal_value = fcf * (1 + terminal_growth) / (wacc - terminal_growth)
    pv += terminal_value / (1 + wacc) ** years
    return pv


def solve_implied_growth_pct(ev: float, fcf0: float, wacc_pct_value: float,
                              terminal_growth_pct: float,
                              years: int = FORECAST_YEARS,
                              bounds_pct: tuple[float, float] = (-50.0, 200.0),
                              iterations: int = 100) -> float | None:
    """EV = 2段階DCFの現在価値 となる年率成長率g(%)を二分探索で解く。

    fcf0<=0（直近のフリーキャッシュフローが赤字）や wacc<=terminal_growth
    （割引率が永久成長率を上回らず発散し算出不能）の場合はNone。
    boundsの範囲内でEVと一致するgが見つからない場合もNone
    （市場価格と整合するgが現実的な範囲に存在しない＝対象外）。
    """
    if fcf0 is None or fcf0 <= 0:
        return None
    if wacc_pct_value is None or terminal_growth_pct is None:
        return None
    wacc = wacc_pct_value / 100
    tg = terminal_growth_pct / 100
    if wacc <= tg:
        return None
    if ev is None or ev <= 0:
        return None

    lo, hi = bounds_pct[0] / 100, bounds_pct[1] / 100
    ev_lo, ev_hi = _ev_for_growth(fcf0, lo, wacc, tg, years), _ev_for_growth(fcf0, hi, wacc, tg, years)
    if not (ev_lo <= ev <= ev_hi):
        return None  # 探索範囲内にEVと一致するgが無い

    for _ in range(iterations):
        mid = (lo + hi) / 2
        if _ev_for_growth(fcf0, mid, wacc, tg, years) < ev:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2 * 100


def project_value(base_value: float, growth_pct: float, years: int = FORECAST_YEARS) -> float | None:
    """base_valueをgrowth_pct(%)でyears年複利成長させた値。"""
    if base_value is None or growth_pct is None:
        return None
    return base_value * (1 + growth_pct / 100) ** years
