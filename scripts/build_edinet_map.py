"""
証券コード ⇔ EDINETコードの対応表を構築する。

EDINET公開の「EDINETコードリスト」(Edinetcode.zip) を取得し、
universe.csv の各銘柄にEDINETコードを紐付けて
data/master/edinet_map.csv に出力する。

EDINETコードリストの証券コードは5桁（末尾に0が付く）表記のため、先頭4桁で突合する。
"""

import io
import sys
import zipfile
from pathlib import Path

import pandas as pd
import requests

CODELIST_URL = (
    "https://disclosure2dl.edinet-fsa.go.jp/searchdocument/codelist/Edinetcode.zip"
)

ROOT = Path(__file__).resolve().parent.parent
MASTER_DIR = ROOT / "data" / "master"


def fetch_codelist() -> pd.DataFrame:
    res = requests.get(CODELIST_URL, timeout=60)
    res.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(res.content)) as zf:
        name = zf.namelist()[0]
        with zf.open(name) as f:
            # 1行目はダウンロード日時の見出し行なので読み飛ばす
            return pd.read_csv(f, encoding="cp932", skiprows=1, dtype=str)


def main() -> int:
    universe_path = MASTER_DIR / "universe.csv"
    if not universe_path.exists():
        print("ERROR: universe.csv がありません。先に build_universe.py を実行してください。",
              file=sys.stderr)
        return 1

    universe = pd.read_csv(universe_path, dtype=str)

    codelist = fetch_codelist().rename(
        columns={
            "ＥＤＩＮＥＴコード": "edinet_code",
            "証券コード": "sec_code",
            "提出者名": "edinet_name",
            "決算日": "fiscal_end",
            "連結の有無": "has_consolidated",
            "上場区分": "listing",
        }
    )
    codelist = codelist[codelist["sec_code"].notna()].copy()
    codelist["code"] = codelist["sec_code"].str.strip().str[:4]
    # 同一証券コードに複数のEDINETコードが割り当てられている場合は先頭を採用する
    codelist = codelist.drop_duplicates(subset="code", keep="first")

    merged = universe.merge(
        codelist[["code", "edinet_code", "edinet_name", "fiscal_end", "has_consolidated"]],
        on="code",
        how="left",
    )

    matched = merged["edinet_code"].notna().sum()
    print(f"ユニバース {len(merged)}件 / EDINETコード紐付け成功 {matched}件 "
          f"({matched / len(merged):.1%})")

    unmatched = merged[merged["edinet_code"].isna()]
    if len(unmatched):
        print(f"\n未紐付け {len(unmatched)}件（先頭20件）:")
        print(unmatched[["code", "name", "market"]].head(20).to_string(index=False))
        unmatched.to_csv(MASTER_DIR / "edinet_unmatched.csv",
                         index=False, encoding="utf-8-sig")

    out = MASTER_DIR / "edinet_map.csv"
    merged.to_csv(out, index=False, encoding="utf-8-sig")
    print(f"\n-> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
