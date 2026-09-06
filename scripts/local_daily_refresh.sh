#!/bin/bash
# 個人ローカル閲覧専用の日次自動更新。
# dividend-site/scripts/local_daily_refresh.sh の末尾から呼び出される想定
# （Yahooへの同時アクセスを避けるため、dividend→valuation同期の完了後に実行する）。
# 対外公開・配信は行わない。
set -uo pipefail

DOW=$(date '+%u')  # 1=月 ... 7=日
if [ "$DOW" -ge 6 ]; then
  echo "===== $(date '+%Y-%m-%d %H:%M:%S') 土日のためスキップ（screening-site） ====="
  exit 0
fi

cd "$(dirname "$0")/.." || exit 1
source .venv/bin/activate

echo "===== $(date '+%Y-%m-%d %H:%M:%S') 開始（screening-site） ====="

# 1年分日次OHLCV+配当を全銘柄分まとめて1回だけ取得する（screen.py・screen_daytrade.py・
# screen_tenbagger.pyが独立に重複取得していた分を解消するための共有キャッシュ作成）。
python3 scripts/fetch_daily_prices.py

python3 scripts/screen.py
python3 scripts/build_site_data.py

python3 scripts/fetch_margin_list.py
python3 scripts/screen_daytrade.py
python3 scripts/build_daytrade_site_data.py

python3 scripts/screen_tenbagger.py
python3 scripts/build_tenbagger_site_data.py
python3 scripts/tenbagger_sim.py

echo "===== $(date '+%Y-%m-%d %H:%M:%S') 終了（screening-site） ====="

# track-siteは個別銘柄の株価をこのスクリプトが直前に更新した
# data/snapshot/daily_ohlcv_1y.csv.gz から流用するため、この直後に実行する
# （Yahooへの同時アクセスを避けるため、dividend→screening→trackの順で続けて実行する）。
TRACK_DIR="$(cd "$(dirname "$0")/../../track-site" && pwd)"
if [ -d "$TRACK_DIR/.venv" ]; then
  (cd "$TRACK_DIR" && bash scripts/local_daily_refresh.sh)
else
  echo "  警告: track-site/.venv が見つからないためtrack-siteの更新をスキップしました"
fi
