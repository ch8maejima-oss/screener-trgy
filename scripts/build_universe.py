"""
銘柄マスタの構築。

JPX公開の「東証上場銘柄一覧」(data_j.xls) を取得し、
スクリーニング対象ユニバース（プライム市場・スタンダード市場の内国普通株式）を
data/master/universe.csv に出力する。

対象の絞り込みは市場区分のみで機械的に行い、個別銘柄の裁量的な除外は行わない。
"""

import io
import sys
from pathlib import Path

import pandas as pd
import requests

JPX_URL = (
    "https://www.jpx.co.jp/markets/statistics-equities/misc/"
    "tvdivq0000001vg2-att/data_j.xls"
)

ROOT = Path(__file__).resolve().parent.parent
MASTER_DIR = ROOT / "data" / "master"

# 対象とする市場区分（data_j.xls の「市場・商品区分」列の表記に一致させる）
TARGET_MARKETS = [
    "プライム（内国株式）",
    "スタンダード（内国株式）",
]


def fetch_jpx_list() -> pd.DataFrame:
    res = requests.get(JPX_URL, timeout=60)
    res.raise_for_status()
    return pd.read_excel(io.BytesIO(res.content), dtype={"コード": str})


def build_universe(df: pd.DataFrame) -> pd.DataFrame:
    df = df.rename(
        columns={
            "日付": "date",
            "コード": "code",
            "銘柄名": "name",
            "市場・商品区分": "market",
            "33業種区分": "sector33",
            "17業種区分": "sector17",
            "規模区分": "size",
        }
    )
    universe = df[df["market"].isin(TARGET_MARKETS)].copy()
    universe["code"] = universe["code"].astype(str).str.strip()
    # 優先株式・社債型種類株式は5桁コードで収録されている。
    # 普通株式（4桁コード）のみを対象とする。
    universe = universe[universe["code"].str.len() == 4]
    universe = universe.sort_values("code").reset_index(drop=True)
    return universe[["code", "name", "market", "sector33", "sector17", "size"]]


def main() -> int:
    MASTER_DIR.mkdir(parents=True, exist_ok=True)

    df = fetch_jpx_list()
    print(f"JPX一覧: {len(df)}件 取得")

    found = set(df["市場・商品区分"].unique())
    missing = [m for m in TARGET_MARKETS if m not in found]
    if missing:
        # 市場区分の表記がJPX側で変更された場合に黙って0件にならないよう検知する
        print(f"ERROR: 想定した市場区分が見つかりません: {missing}", file=sys.stderr)
        print(f"実際の区分: {sorted(found)}", file=sys.stderr)
        return 1

    universe = build_universe(df)

    out = MASTER_DIR / "universe.csv"
    universe.to_csv(out, index=False, encoding="utf-8-sig")

    print(f"対象ユニバース: {len(universe)}件 -> {out}")
    print(universe["market"].value_counts().to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
