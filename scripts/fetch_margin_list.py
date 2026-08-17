"""
JPXの「制度信用・貸借選定銘柄一覧」を取得し、貸借銘柄（空売り可能銘柄）を
data/master/margin_list.csv に出力する。

一覧ページ（index.html）から当月分のxlsxへのリンクをスクレイピングする。
ファイル名が毎月変わるため、data_j.xls（build_universe.py）のような固定URLは
使えない。JPXは毎月第1営業日16:00頃に更新する運用。

出力: data/master/margin_list.csv (code, name, market, credit_type)
"""

import io
import re
import sys
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
MASTER_DIR = ROOT / "data" / "master"

INDEX_URL = "https://www.jpx.co.jp/listing/others/margin/index.html"
MARGIN_TYPE_TARGET = "貸借銘柄"


def find_list_url() -> str:
    res = requests.get(INDEX_URL, timeout=60)
    res.raise_for_status()
    matches = re.findall(r'href="([^"]+_list\.xlsx)"', res.text)
    if not matches:
        raise SystemExit(
            f"ERROR: {INDEX_URL} 内に一覧xlsxへのリンクが見つかりません。"
            "JPX側でページ構成が変わった可能性があります。"
        )
    # 最初に出てくるものが最新（選定銘柄一覧）
    href = matches[0]
    return href if href.startswith("http") else f"https://www.jpx.co.jp{href}"


def fetch_margin_list(url: str) -> pd.DataFrame:
    res = requests.get(url, timeout=60)
    res.raise_for_status()
    df = pd.read_excel(io.BytesIO(res.content), sheet_name="一覧", header=1,
                       dtype={"銘柄コード": str})
    return df


def build_margin_list(df: pd.DataFrame) -> pd.DataFrame:
    df = df.rename(columns={
        "銘柄コード": "code",
        "銘柄名": "name",
        "市場区分/商品区分": "market",
        "信用区分": "credit_type",
    })
    df["code"] = df["code"].astype(str).str.strip()
    df = df[df["code"].str.len() == 4]
    df = df[df["credit_type"] == MARGIN_TYPE_TARGET]
    df = df.sort_values("code").reset_index(drop=True)
    return df[["code", "name", "market", "credit_type"]]


def main() -> int:
    print(f"一覧xlsxのURLを取得します... ({INDEX_URL})")
    list_url = find_list_url()
    print(f"  -> {list_url}")

    df = fetch_margin_list(list_url)
    print(f"JPX一覧: {len(df)}件 取得")

    margin = build_margin_list(df)
    if margin.empty:
        print(f"ERROR: 「{MARGIN_TYPE_TARGET}」が0件でした。列名や値の表記が"
              "変わった可能性があります。", file=sys.stderr)
        return 1

    MASTER_DIR.mkdir(parents=True, exist_ok=True)
    out = MASTER_DIR / "margin_list.csv"
    margin.to_csv(out, index=False, encoding="utf-8-sig")

    print(f"貸借銘柄: {len(margin)}件 -> {out}")
    print(margin["market"].value_counts().to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
