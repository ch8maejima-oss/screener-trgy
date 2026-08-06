import type { Metadata } from "next";
import "./globals.css";
import Footer from "./components/Footer";
import SiteNav from "./components/SiteNav";

export const metadata: Metadata = {
  title: "スクリーニング銘柄一覧 | 株式会社トリロジー",
  description:
    "配当利回り・ROE・自己資本比率・流動比率・売上高・営業利益率の6条件を、東証プライム市場およびスタンダード市場の全銘柄に機械的に適用した結果を表示します。株式会社トリロジー（近畿財務局長（金商）第372号）。",
  robots: "noindex", // 社内利用のため検索避け。外部公開時はコンプライアンスレビュー後に解除
};

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
              <a
                className="site-header__brandblock"
                href="https://www.trgy.co.jp"
                target="_blank"
                rel="noopener noreferrer"
              >
                <span className="site-header__brand">Trilogy</span>
                <span className="site-header__title">スクリーニング銘柄一覧</span>
              </a>
              <SiteNav />
            </div>
          </header>
          <main className="site-main">{children}</main>
          <Footer />
        </div>
      </body>
    </html>
  );
}
