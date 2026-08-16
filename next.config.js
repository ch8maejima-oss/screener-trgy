/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // 完全な静的サイト。結果JSONはビルド時に取り込むためAPIは持たない。
  output: "export",
  // /dividend のようなサブディレクトリのルートを dividend/index.html として書き出す。
  // trailingSlash: false のままだと dividend.html になり、Xserverでは
  // 拡張子なしの /dividend へのアクセスを解決できない（dividend-site と同じ対策）。
  trailingSlash: true,
};

module.exports = nextConfig;
