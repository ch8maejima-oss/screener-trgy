#!/bin/bash
# launchd常駐用（co.trgy.screening-dev-server）。npm/nodeを直接launchdから起動すると
# macOSのTCC制限（uv_cwd EPERM）に当たるため、既に許可済みの/bin/bash経由で起動する。
cd "$(dirname "$0")/.." || exit 1
export PATH="/Users/maejimatakashi/.local/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
exec npm run dev -- -p 3003
