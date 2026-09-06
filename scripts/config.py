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

# スイング①（期待リターン逆算）用のCAPM/DCF前提。ユーザー確認済み(2026-08-31)。
# 無リスク金利は10年国債利回りの目安を固定値として置き、相場が大きく動いたら
# 手動で更新する運用（日次で自動取得はしない）。
SWING1_RISK_FREE_RATE_PCT = 2.8   # 2026-08時点の新発10年国債利回り目安
SWING1_EQUITY_RISK_PREMIUM_PCT = 6.0
SWING1_TAX_RATE_PCT = 30.0        # 負債コスト(税引後)算出用の実効税率の目安
SWING1_TERMINAL_GROWTH_PCT = 1.0  # 11年目以降の永久成長率


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
