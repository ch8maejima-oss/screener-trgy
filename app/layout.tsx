import type { Metadata } from "next";
import Script from "next/script";
import "./globals.css";
import Footer from "./components/Footer";
import SiteNav from "./components/SiteNav";

export const metadata: Metadata = {
  title: "スクリーニング銘柄一覧 | 株式会社トリロジー",
  description:
    "投資家の資力・スタイルに応じたスクリーニング条件を、対象市場の全銘柄に機械的に適用した結果を一覧できるサイトです。株式会社トリロジー（近畿財務局長（金商）第372号）。",
  robots: "noindex", // 社内利用のため検索避け。外部公開時はコンプライアンスレビュー後に解除
};

const ADSENSE_CLIENT_ID = process.env.NEXT_PUBLIC_ADSENSE_CLIENT_ID;

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ja">
      <body>
        <div className="page-wrap">
          <header className="site-header">
            <div className="site-header__inner">
              <a className="site-header__brandblock" href="/">
                <img src="/logo.png" alt="Trilogy" className="site-header__logo" />
                <span className="site-header__title">スクリーニング銘柄一覧</span>
              </a>
              <SiteNav />
            </div>
          </header>
          <main className="site-main">{children}</main>
          <Footer />
        </div>
        {ADSENSE_CLIENT_ID && (
          <Script
            async
            src={`https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=${ADSENSE_CLIENT_ID}`}
            crossOrigin="anonymous"
            strategy="afterInteractive"
          />
        )}
      </body>
    </html>
  );
}
