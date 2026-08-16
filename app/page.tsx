import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "スクリーニング銘柄一覧 | 株式会社トリロジー",
  description:
    "投資家の資力・スタイルに応じたスクリーニング条件を、対象市場の全銘柄に機械的に適用した結果を一覧できるサイトです。株式会社トリロジー（近畿財務局長（金商）第372号）。",
};

type Strategy = {
  key: string;
  title: string;
  description: string;
  href?: string;
};

const STRATEGIES: Strategy[] = [
  {
    key: "dividend",
    title: "配当重視スクリーニング",
    description:
      "配当利回り・ROE・自己資本比率・流動比率・売上高・営業利益率の6条件を機械的に適用。",
    href: "/dividend/",
  },
  {
    key: "daytrade",
    title: "デイトレード用スクリーニング",
    description: "準備中です。",
  },
  {
    key: "swing",
    title: "スイング用スクリーニング",
    description: "準備中です。",
  },
];

export default function Home() {
  return (
    <div className="home">
      <section className="intro">
        <h1>スクリーニング銘柄一覧</h1>
        <p className="intro__lead">
          個別株のスクリーニング条件は、投資家の資力やスタイルによって適したものが異なります。
          本サイトでは、あらかじめ定めた条件を対象市場の全銘柄に機械的に適用した結果を、
          スクリーニング条件ごとに掲載しています。
        </p>
        <p className="intro__lead">
          いずれのページも、当社が有望と判断した銘柄を選び出したものではなく、
          定めた条件に合致した銘柄を全件掲載するものです。特定銘柄の売買を
          推奨・勧誘するものではありません。
        </p>
      </section>

      <section className="hub" aria-label="スクリーニング条件一覧">
        <h2>スクリーニング条件を選択</h2>
        <ul className="hub__cards">
          {STRATEGIES.map((s) =>
            s.href ? (
              <li key={s.key} className="hub__card">
                <a className="hub__card-link" href={s.href}>
                  <span className="hub__card-title">{s.title}</span>
                  <p className="hub__card-desc">{s.description}</p>
                  <span className="hub__card-cta">一覧を見る →</span>
                </a>
              </li>
            ) : (
              <li key={s.key} className="hub__card hub__card--soon">
                <span className="hub__card-title">{s.title}</span>
                <p className="hub__card-desc">{s.description}</p>
                <span className="hub__card-badge">近日公開</span>
              </li>
            )
          )}
        </ul>
      </section>
    </div>
  );
}
