"""
ローカル開発専用: EA EXPO認証バイパス（lib/gate.ts、NODE_ENV==='development'時のみ有効）
が使う非公開データ配信サーバー。private-data/配下を127.0.0.1:8899で配信する。

標準の `python3 -m http.server` はAccess-Control-Allow-Originヘッダを送らないため、
next dev（別オリジンのhttp://localhost:3003）からのfetch()がブラウザのCORSポリシーで
ブロックされる（curlではオリジンチェックが無いため再現せず気づきにくい）。
このスクリプトは全レスポンスにCORSヘッダを付与するだけの最小限のカスタムハンドラ。

本番ビルド（next build / next start）・screener.trgy.co.jp本番のWordPress側ゲートには
一切関与しない。scripts/dev-local.sh から起動される。
"""

import http.server
import os
import socketserver

PORT = 8899
DIRECTORY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "private-data")


class CORSRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    def log_message(self, format, *args):  # noqa: A002 - http.serverのシグネチャに合わせる
        pass  # 常駐ログ(.dev-server.log)が肥大化しないよう、アクセスログは出さない


class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True  # launchdの再起動直後でもポート競合しないようにする


if __name__ == "__main__":
    with ReusableTCPServer(("127.0.0.1", PORT), CORSRequestHandler) as httpd:
        print(f"private-data/ を http://127.0.0.1:{PORT} で配信中 (Ctrl+Cで終了)")
        httpd.serve_forever()
