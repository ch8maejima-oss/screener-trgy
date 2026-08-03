"""
EDINETから有価証券報告書を取得する。

処理は2段階。
  1. index : 書類一覧APIを日付ごとに叩き、ユニバース各社の「最新の有価証券報告書」の
             docIDを data/master/doc_index.csv に記録する。
  2. fetch : docIDごとにCSV形式(type=5)のzipを data/raw/ にダウンロードする。

どちらも再開可能。取得済みの日付・ファイルはスキップする。

使い方:
    python3 scripts/fetch_edinet.py index          # 過去1年分の書類一覧を走査
    python3 scripts/fetch_edinet.py index --days 400
    python3 scripts/fetch_edinet.py fetch          # XBRL(CSV形式)を一括DL
    python3 scripts/fetch_edinet.py fetch --limit 5   # 動作確認用に5件だけ
"""

import argparse
import datetime as dt
import json
import sys
import time

import pandas as pd
import requests

from config import (
    DOC_TYPE_YUHO,
    EDINET_API_BASE,
    MASTER_DIR,
    RAW_DIR,
    get_api_key,
)

DOC_INDEX = MASTER_DIR / "doc_index.csv"
SCANNED_DATES = MASTER_DIR / "scanned_dates.json"


def _get(url: str, params: dict, api_key: str, **kwargs) -> requests.Response:
    params = dict(params, **{"Subscription-Key": api_key})
    return requests.get(url, params=params, timeout=60, **kwargs)


# --------------------------------------------------------------------------
# 1. 書類一覧の走査
# --------------------------------------------------------------------------

def cmd_index(args: argparse.Namespace) -> int:
    api_key = get_api_key()

    map_path = MASTER_DIR / "edinet_map.csv"
    if not map_path.exists():
        print("ERROR: edinet_map.csv がありません。先に build_edinet_map.py を実行してください。",
              file=sys.stderr)
        return 1
    universe = pd.read_csv(map_path, dtype=str)
    target_codes = set(universe["edinet_code"].dropna())
    print(f"対象EDINETコード: {len(target_codes)}件")

    scanned = set(json.loads(SCANNED_DATES.read_text())) if SCANNED_DATES.exists() else set()

    rows = []
    if DOC_INDEX.exists():
        rows = pd.read_csv(DOC_INDEX, dtype=str).to_dict("records")

    today = dt.date.today()
    dates = [today - dt.timedelta(days=i) for i in range(args.days)]
    todo = [d for d in dates if d.isoformat() not in scanned]
    print(f"走査対象: {len(todo)}日分（うち取得済み {len(dates) - len(todo)}日はスキップ）")

    for i, d in enumerate(todo, 1):
        ds = d.isoformat()
        try:
            res = _get(f"{EDINET_API_BASE}/documents.json",
                       {"date": ds, "type": "2"}, api_key)
            data = res.json()
        except Exception as e:  # noqa: BLE001 - 1日失敗しても走査全体は継続する
            print(f"  {ds} 取得失敗: {e}", file=sys.stderr)
            continue

        status = str(data.get("metadata", {}).get("status", ""))
        if status != "200":
            msg = data.get("metadata", {}).get("message") or data.get("message")
            print(f"  {ds} APIエラー status={status} {msg}", file=sys.stderr)
            if status == "401":
                return 1
            continue

        hits = 0
        for doc in data.get("results") or []:
            if doc.get("docTypeCode") != DOC_TYPE_YUHO:
                continue
            if doc.get("edinetCode") not in target_codes:
                continue
            if doc.get("csvFlag") != "1":
                continue
            rows.append({
                "edinet_code": doc.get("edinetCode"),
                "sec_code": (doc.get("secCode") or "")[:4],
                "doc_id": doc.get("docID"),
                "filer_name": doc.get("filerName"),
                "period_end": doc.get("periodEnd"),
                "submit_date": ds,
                "doc_description": doc.get("docDescription"),
            })
            hits += 1

        scanned.add(ds)
        if hits or i % 30 == 0:
            print(f"  [{i}/{len(todo)}] {ds}: 有報 {hits}件 (累計 {len(rows)}件)")

        if i % 20 == 0:
            _save_index(rows, scanned)
        time.sleep(args.sleep)

    _save_index(rows, scanned)
    return 0


def _save_index(rows: list, scanned: set) -> None:
    MASTER_DIR.mkdir(parents=True, exist_ok=True)
    if rows:
        df = pd.DataFrame(rows)
        # 同一企業に複数の有報がある場合は提出日が最新のものを残す
        df = df.sort_values("submit_date").drop_duplicates(
            subset="edinet_code", keep="last")
        df.to_csv(DOC_INDEX, index=False, encoding="utf-8-sig")
    SCANNED_DATES.write_text(json.dumps(sorted(scanned)))


# --------------------------------------------------------------------------
# 2. 書類本体（CSV形式）のダウンロード
# --------------------------------------------------------------------------

def cmd_fetch(args: argparse.Namespace) -> int:
    api_key = get_api_key()

    if not DOC_INDEX.exists():
        print("ERROR: doc_index.csv がありません。先に `index` を実行してください。",
              file=sys.stderr)
        return 1

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    docs = pd.read_csv(DOC_INDEX, dtype=str)

    todo = [r for r in docs.to_dict("records")
            if not (RAW_DIR / f"{r['doc_id']}.zip").exists()]
    if args.limit:
        todo = todo[: args.limit]

    print(f"DL対象: {len(todo)}件（取得済み {len(docs) - len(todo)}件はスキップ）")

    ok = fail = 0
    for i, r in enumerate(todo, 1):
        doc_id = r["doc_id"]
        dest = RAW_DIR / f"{doc_id}.zip"
        try:
            res = _get(f"{EDINET_API_BASE}/documents/{doc_id}",
                       {"type": "5"}, api_key)
            # エラー時はJSONが返るためContent-Typeで判定する
            if "application/json" in res.headers.get("Content-Type", ""):
                print(f"  {doc_id} エラー: {res.text[:200]}", file=sys.stderr)
                fail += 1
            else:
                dest.write_bytes(res.content)
                ok += 1
        except Exception as e:  # noqa: BLE001
            print(f"  {doc_id} 取得失敗: {e}", file=sys.stderr)
            fail += 1

        if i % 50 == 0 or i == len(todo):
            print(f"  [{i}/{len(todo)}] 成功{ok} 失敗{fail}")
        time.sleep(args.sleep)

    print(f"完了: 成功{ok} 失敗{fail} -> {RAW_DIR}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    pi = sub.add_parser("index", help="書類一覧を走査してdocIDを収集")
    pi.add_argument("--days", type=int, default=400,
                    help="今日から遡る日数（既定400日＝直近1年の有報を網羅）")
    pi.add_argument("--sleep", type=float, default=0.5)
    pi.set_defaults(func=cmd_index)

    pf = sub.add_parser("fetch", help="XBRL(CSV形式)をダウンロード")
    pf.add_argument("--limit", type=int, default=0, help="先頭N件のみ取得（動作確認用）")
    pf.add_argument("--sleep", type=float, default=0.5)
    pf.set_defaults(func=cmd_fetch)

    args = p.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
