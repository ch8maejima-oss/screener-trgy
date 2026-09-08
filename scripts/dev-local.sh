#!/bin/bash
# ローカル個人閲覧専用: `npm run dev` 実行時に、EA EXPO認証バイパス
# （lib/gate.ts、NODE_ENV==='development'時のみ有効）が使う非公開データ配信
# サーバー（127.0.0.1:8899、private-data/を配信）を自動起動してから next dev を
# 起動する。手動で `python3 -m http.server 8899` を都度起動する必要をなくすための
# もので、本番ビルド（next build / next start）には一切関与しない。
set -uo pipefail
cd "$(dirname "$0")/.."

(python3 scripts/dev_private_data_server.py > /dev/null 2>&1) &
PRIVATE_DATA_PID=$!

cleanup() {
  kill "$PRIVATE_DATA_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

next dev -p 3003
