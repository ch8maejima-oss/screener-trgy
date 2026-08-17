"""
ダウンロード済みの有報（EDINET CSV形式）を解析し、財務スナップショットを生成する。

EDINETのCSV形式は UTF-16 / タブ区切りで、次の列を持つ。
    要素ID / 項目名 / コンテキストID / 相対年度 / 連結・個別 / 期間・時点 / ユニットID / 単位 / 値

抽出方針
  条件2 ROE・条件3 自己資本比率・条件5 売上高5期分・配当は、有報の
  【主要な経営指標等の推移】に企業自身が開示した値をそのまま採用する（当方で再計算しない）。
  条件4 流動比率・条件6 営業利益率は、貸借対照表・損益計算書の科目から算出する。

実データ（44社）で検証した要素IDとコンテキストの実態
  - 自己資本比率・ROEは百分率ではなく「小数」で格納される（0.5727 = 57.27%）。
  - 自己資本比率は Instant（時点）、ROEは Duration（期間）のコンテキストを持つ。
  - 1株当たり配当額は連結側に存在せず、提出会社（_NonConsolidatedMember）側にのみある。
  - IFRS適用会社は要素IDが別系統。特に jpcrp_cor:EquityToAssetRatioIFRS... は
    要素IDに反して中身が「1株当たり親会社所有者帰属持分」（＝BPS）であり、
    自己資本比率ではない。使用してはならない。正しくは RatioOfOwnersEquityToGrossAssetsIFRS...。
  - IFRSの流動負債は CurrentLiabilitiesIFRS ではなく TotalCurrentLiabilitiesIFRS。

出力: data/snapshot/financials.csv

使い方:
    python3 scripts/parse_edinet.py
    python3 scripts/parse_edinet.py --inspect S100XXXX   # 単一書類のタグを一覧表示
"""

import argparse
import io
import sys
import zipfile
from pathlib import Path

import pandas as pd

from config import MASTER_DIR, RAW_DIR, SNAPSHOT_DIR

# --------------------------------------------------------------------------
# 【主要な経営指標等の推移】の要素ID候補（優先順）
# --------------------------------------------------------------------------

SUMMARY_REVENUE = [
    "jpcrp_cor:NetSalesSummaryOfBusinessResults",
    "jpcrp_cor:RevenueIFRSSummaryOfBusinessResults",
    "jpcrp_cor:OperatingRevenue1SummaryOfBusinessResults",
    "jpcrp_cor:NetSalesAndOperatingRevenuesSummaryOfBusinessResults",
    "jpcrp_cor:OperatingRevenuesSummaryOfBusinessResults",
    "jpcrp_cor:GrossOperatingRevenueSummaryOfBusinessResults",
    "jpcrp_cor:NetSalesUSGAAPSummaryOfBusinessResults",
    "jpcrp_cor:TotalRevenuesUSGAAPSummaryOfBusinessResults",
    "jpcrp_cor:RevenuesUSGAAPSummaryOfBusinessResults",
]
SUMMARY_ROE = [
    "jpcrp_cor:RateOfReturnOnEquitySummaryOfBusinessResults",
    "jpcrp_cor:RateOfReturnOnEquityIFRSSummaryOfBusinessResults",
    "jpcrp_cor:RateOfReturnOnEquityUSGAAPSummaryOfBusinessResults",
]
# 注: jpcrp_cor:EquityToAssetRatioIFRSSummaryOfBusinessResults は
#     要素IDに反して1株当たり親会社所有者帰属持分(BPS)が入るため候補に含めない。
SUMMARY_EQUITY_RATIO = [
    "jpcrp_cor:EquityToAssetRatioSummaryOfBusinessResults",
    "jpcrp_cor:RatioOfOwnersEquityToGrossAssetsIFRSSummaryOfBusinessResults",
    "jpcrp_cor:EquityToAssetRatioUSGAAPSummaryOfBusinessResults",
    "jpcrp_cor:RatioOfOwnersEquityToGrossAssetsUSGAAPSummaryOfBusinessResults",
]
SUMMARY_DPS = [
    "jpcrp_cor:DividendPaidPerShareSummaryOfBusinessResults",
]
# 発行済株式数（時価総額の算出に使う）。DPSと同じく提出会社側にのみ存在する。
SUMMARY_SHARES_ISSUED = [
    "jpcrp_cor:TotalNumberOfIssuedSharesSummaryOfBusinessResults",
]

# --------------------------------------------------------------------------
# 貸借対照表 / 損益計算書の要素ID候補
# --------------------------------------------------------------------------

BS_CURRENT_ASSETS = [
    "jppfs_cor:CurrentAssets",
    "jpigp_cor:CurrentAssetsIFRS",
]
BS_CURRENT_LIABILITIES = [
    "jppfs_cor:CurrentLiabilities",
    "jpigp_cor:TotalCurrentLiabilitiesIFRS",
]
PL_OPERATING_INCOME = [
    "jppfs_cor:OperatingIncome",
    "jpigp_cor:OperatingProfitLossIFRS",
]
# 営業利益率の分母は損益計算書ではなく【主要な経営指標等の推移】の売上高を用いる。
# 損益計算書側の売上高は、連結本表に計上されない会社（IFRS適用会社に多い）があり、
# 単体へフォールバックすると連結の営業利益と食い違うため。

# 5期分のコンテキスト接頭辞（古い順）
PERIODS = ["Prior4Year", "Prior3Year", "Prior2Year", "Prior1Year", "CurrentYear"]

# 連結を優先し、無ければ提出会社（単体）にフォールバックする
SCOPES = ["", "_NonConsolidatedMember"]


def read_doc(zip_path: Path) -> pd.DataFrame:
    """書類zip内の全CSVを1つのDataFrameに結合して返す。"""
    frames = []
    with zipfile.ZipFile(zip_path) as zf:
        for name in zf.namelist():
            if not name.lower().endswith(".csv"):
                continue
            raw = zf.read(name)
            for enc in ("utf-16", "cp932", "utf-8-sig"):
                try:
                    frames.append(
                        pd.read_csv(io.StringIO(raw.decode(enc)), sep="\t", dtype=str)
                    )
                    break
                except (UnicodeDecodeError, UnicodeError):
                    continue
    if not frames:
        raise ValueError(f"CSVを読み取れませんでした: {zip_path.name}")
    return pd.concat(frames, ignore_index=True)


def to_number(value):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    s = str(value).strip().replace(",", "")
    # 「－」等の非該当表記は数値として扱わない
    if s in ("", "-", "－", "―", "NA", "N/A", "×", "nan"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def build_lookup(df: pd.DataFrame) -> dict:
    """(要素ID, コンテキストID) -> 値 の辞書を作る。"""
    cols = {str(c).strip(): c for c in df.columns}
    col_id, col_ctx, col_val = cols.get("要素ID"), cols.get("コンテキストID"), cols.get("値")
    if not all([col_id, col_ctx, col_val]):
        raise ValueError(f"想定した列がありません: {list(df.columns)}")

    lookup = {}
    for eid, ctx, val in zip(df[col_id], df[col_ctx], df[col_val]):
        if not isinstance(eid, str) or not isinstance(ctx, str):
            continue
        lookup.setdefault((eid.strip(), ctx.strip()), val)
    return lookup


def pick(lookup: dict, candidates: list, context: str):
    """候補タグを優先順に探し、最初に見つかった数値を (値, 採用タグ) で返す。"""
    for tag in candidates:
        v = to_number(lookup.get((tag, context)))
        if v is not None:
            return v, tag
    return None, None


def pick_scoped(lookup: dict, candidates: list, period: str, kind: str):
    """連結→単体の順にコンテキストを試す。kind は 'Duration' または 'Instant'。"""
    for scope in SCOPES:
        v, tag = pick(lookup, candidates, f"{period}{kind}{scope}")
        if v is not None:
            return v, tag, scope_label(scope)
    return None, None, None


def scope_label(scope: str) -> str:
    return "連結" if scope == "" else "個別"


def detect_scope(lookup: dict) -> str:
    """
    その書類を連結ベースで読むか単体ベースで読むかを判定する。

    【主要な経営指標等の推移】に連結の指標が載っていれば連結財務諸表作成会社とみなす。
    連結作成会社の数値を単体で代用してはならない。例えば銀行持株会社は連結では
    流動/固定の区分を持たないが単体では持つため、単体で代用すると流動比率が
    実態とかけ離れた値になる。取得できない場合は算出不能として扱う。
    """
    probes = [
        (SUMMARY_EQUITY_RATIO, "CurrentYearInstant"),
        (SUMMARY_REVENUE, "CurrentYearDuration"),
        (SUMMARY_ROE, "CurrentYearDuration"),
    ]
    for candidates, ctx in probes:
        if pick(lookup, candidates, ctx)[0] is not None:
            return ""
    return "_NonConsolidatedMember"


def as_pct(value):
    """比率は小数で格納されるため百分率に直す。"""
    return None if value is None else value * 100


def extract(zip_path: Path) -> dict:
    lookup = build_lookup(read_doc(zip_path))

    # 全項目をこの1つのスコープでのみ取得する（混在を禁止）
    scope = detect_scope(lookup)
    rec: dict = {"doc_id": zip_path.stem, "scope": scope_label(scope)}

    # --- 条件5: 売上高5期分（y0が5期前、y4が直近）---
    # IFRS移行会社は期によって要素IDが変わるため、期ごとに候補を横断して探す
    for i, period in enumerate(PERIODS):
        v, tag = pick(lookup, SUMMARY_REVENUE, f"{period}Duration{scope}")
        rec[f"revenue_y{i}"] = v
        if i == len(PERIODS) - 1:
            rec["revenue_tag"] = tag

    # --- 条件2 ROE（期間）/ 条件3 自己資本比率（時点）---
    roe, roe_tag = pick(lookup, SUMMARY_ROE, f"CurrentYearDuration{scope}")
    rec["roe_pct"] = as_pct(roe)
    rec["roe_tag"] = roe_tag

    eq, eq_tag = pick(lookup, SUMMARY_EQUITY_RATIO, f"CurrentYearInstant{scope}")
    rec["equity_ratio_pct"] = as_pct(eq)
    rec["equity_ratio_tag"] = eq_tag

    # --- 条件1: 1株当たり配当額は連結側に存在せず、常に提出会社側にある ---
    rec["dps"], _ = pick(lookup, SUMMARY_DPS,
                         "CurrentYearDuration_NonConsolidatedMember")

    # --- 発行済株式数（時価総額用）。DPSと同じく常に提出会社側にある ---
    rec["shares_issued"], _ = pick(lookup, SUMMARY_SHARES_ISSUED,
                                   "CurrentYearInstant_NonConsolidatedMember")

    # --- 条件4: 流動資産・流動負債 ---
    rec["current_assets"], _ = pick(lookup, BS_CURRENT_ASSETS,
                                    f"CurrentYearInstant{scope}")
    rec["current_liabilities"], _ = pick(lookup, BS_CURRENT_LIABILITIES,
                                         f"CurrentYearInstant{scope}")

    # --- 条件6: 営業利益（分母は上の revenue_y4 を用いる）---
    rec["operating_income"], rec["operating_income_tag"] = pick(
        lookup, PL_OPERATING_INCOME, f"CurrentYearDuration{scope}")
    return rec


def cmd_inspect(doc_id: str) -> int:
    zip_path = RAW_DIR / f"{doc_id}.zip"
    if not zip_path.exists():
        print(f"ERROR: {zip_path} がありません。", file=sys.stderr)
        return 1
    df = read_doc(zip_path)
    cols = {str(c).strip(): c for c in df.columns}
    col_id = cols["要素ID"]
    keywords = ("SummaryOfBusinessResults", "CurrentAssets", "CurrentLiabilities",
                "OperatingIncome", "OperatingProfit", "NetSales", "Revenue")
    hit = df[df[col_id].astype(str).str.contains("|".join(keywords), na=False)]
    print(f"{doc_id}: 全{len(df)}行 / 該当{len(hit)}行")
    print(hit[[col_id, cols["項目名"], cols["コンテキストID"], cols["値"]]]
          .to_string(index=False, max_colwidth=45))
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--inspect", metavar="DOC_ID",
                   help="単一書類の関連タグを一覧表示して終了")
    p.add_argument("--limit", type=int, default=0)
    args = p.parse_args()

    if args.inspect:
        return cmd_inspect(args.inspect)

    zips = sorted(RAW_DIR.glob("*.zip"))
    if args.limit:
        zips = zips[: args.limit]
    if not zips:
        print("ERROR: data/raw/ に書類がありません。先に fetch_edinet.py を実行してください。",
              file=sys.stderr)
        return 1

    records, errors = [], []
    for i, z in enumerate(zips, 1):
        try:
            records.append(extract(z))
        except Exception as e:  # noqa: BLE001 - 1社の失敗で全体を止めない
            errors.append({"doc_id": z.stem, "error": str(e)})
        if i % 200 == 0:
            print(f"  [{i}/{len(zips)}] 解析中")

    snap = pd.DataFrame(records)

    docs = pd.read_csv(MASTER_DIR / "doc_index.csv", dtype=str)
    universe = pd.read_csv(MASTER_DIR / "universe.csv", dtype=str)
    snap = snap.merge(docs[["doc_id", "edinet_code", "sec_code", "period_end"]],
                      on="doc_id", how="left")
    snap = snap.merge(universe.rename(columns={"code": "sec_code"}),
                      on="sec_code", how="left")

    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    out = SNAPSHOT_DIR / "financials.csv"
    snap.to_csv(out, index=False, encoding="utf-8-sig")

    print(f"\n解析完了: {len(snap)}件 (失敗 {len(errors)}件) -> {out}")
    for col in ["revenue_y0", "revenue_y4", "roe_pct", "equity_ratio_pct", "dps",
                "shares_issued", "current_assets", "current_liabilities", "operating_income"]:
        if col in snap.columns:
            n = snap[col].notna().sum()
            print(f"  {col:22s} 取得率 {n:5d}/{len(snap)} ({n / len(snap):6.1%})")
    if errors:
        pd.DataFrame(errors).to_csv(SNAPSHOT_DIR / "parse_errors.csv",
                                    index=False, encoding="utf-8-sig")
        print(f"  失敗の詳細 -> {SNAPSHOT_DIR / 'parse_errors.csv'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
