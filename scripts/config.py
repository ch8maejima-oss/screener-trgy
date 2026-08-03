"""共通設定。APIキーは環境変数または screening-site/.env から読み込む。"""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MASTER_DIR = ROOT / "data" / "master"
RAW_DIR = ROOT / "data" / "raw"
SNAPSHOT_DIR = ROOT / "data" / "snapshot"
OUTPUT_DIR = ROOT / "output"

EDINET_API_BASE = "https://api.edinet-fsa.go.jp/api/v2"

# 有価証券報告書の書類種別コード
DOC_TYPE_YUHO = "120"


def _load_dotenv() -> None:
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def get_api_key() -> str:
    _load_dotenv()
    key = os.environ.get("EDINET_API_KEY", "").strip()
    if not key:
        raise SystemExit(
            "EDINET_API_KEY が設定されていません。\n"
            f"  {ROOT / '.env'} に次の1行を書くか、環境変数で指定してください:\n"
            "  EDINET_API_KEY=取得したAPIキー"
        )
    return key
