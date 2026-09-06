"""
スイング②（ROE・PBR整合性チェッカー）用の計算ロジック。

PBR = ROE × PER という会計上の恒等式（PBR=株価/BPS, PER=株価/EPS, ROE=EPS/BPS
なのでPER×ROE=株価/BPSと一致する）を用いて、「実績ROEに業種平均PERを乗じた
理論PBR」と実際のPBRを比較する（ユーザー確認済み、2026-09-02）。

  理論PBR = 調整後ROE（経常利益ベース）× 業種平均PER（標準PER基準）

ROEには開示された当期純利益ベースの値ではなく、経常利益ベースの調整後ROEを使う。
特別利益（資産売却等）による一時的なROE押し上げを理論PBRの計算に反映させない
ため（ユーザー確認済み）。
"""

from __future__ import annotations


def adjusted_roe_pct(ordinary_income: float | None, net_assets: float | None) -> float | None:
    """経常利益ベースの調整後ROE（%）。特別利益を含む当期純利益ベースの開示ROEとは別物。"""
    if ordinary_income is None or net_assets is None or net_assets <= 0:
        return None
    return ordinary_income / net_assets * 100


def theoretical_pbr(adjusted_roe_pct_value: float | None, sector_avg_per: float | None) -> float | None:
    if adjusted_roe_pct_value is None or sector_avg_per is None:
        return None
    if adjusted_roe_pct_value <= 0 or sector_avg_per <= 0:
        return None
    return (adjusted_roe_pct_value / 100) * sector_avg_per


def lower_deviation_pct(theoretical_pbr_value: float | None, actual_pbr: float | None) -> float | None:
    """理論PBRに対して実績PBRがどれだけ下方に乖離しているか（%）。
    プラスが大きいほど「理論値より割安」。実績PBRが理論PBR以上ならマイナス
    （割安ではない）になる。"""
    if theoretical_pbr_value is None or actual_pbr is None or theoretical_pbr_value <= 0:
        return None
    return (theoretical_pbr_value - actual_pbr) / theoretical_pbr_value * 100


def roe_not_declining_3y(roe_series: list[float | None]) -> bool | None:
    """直近3期のROEが右肩下がりでないかどうか。
    roe_seriesは古い順（例: [3期前, 2期前, 直近]）。3期分そろわなければNone
    （算出不能）。「右肩下がり」は2期連続の減少（3期前>2期前>直近）と定義する
    （1期だけの落ち込みは許容し、2期連続の悪化トレンドのみを排除する）。"""
    if len(roe_series) != 3 or any(v is None for v in roe_series):
        return None
    old, mid, latest = roe_series
    is_declining = old > mid > latest
    return not is_declining
