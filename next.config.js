/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // 完全な静的サイト。結果JSONはビルド時に取り込むためAPIは持たない。
  output: "export",
};

module.exports = nextConfig;
