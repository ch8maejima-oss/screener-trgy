import type { CSSProperties } from "react";
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
  accent: string;
};

// カードにカーソルを乗せたときの枠色。条件が増えても隣り合う色が
// 見分けやすいよう固定順（validate_palette.jsで検証済みの8色）で
// 追加時は末尾に足していく。途中の色を入れ替えたり、既存カードの
// 色を使い回したりしない。
const ACCENT = {
  blue: "#2a78d6",
  orange: "#eb6834",
  aqua: "#1baf7a",
  yellow: "#eda100",
  magenta: "#e87ba4",
  green: "#008300",
  violet: "#4a3aa7",
  red: "#e34948",
} as const;

const STRATEGIES: Strategy[] = [
  {
    key: "dividend",
    title: "配当重視スクリーニング",
    description:
      "配当利回り・ROE・自己資本比率・流動比率・売上高・営業利益率の6条件を機械的に適用。",
    href: "/dividend/",
    accent: ACCENT.blue,
  },
  {
    key: "daytrade",
    title: "デイトレード用スクリーニング",
    description:
      "貸借銘柄・売買代金・前日/5日/20日騰落率・出来高増加傾向などの条件を、上昇/下落モメンタムそれぞれに機械的に適用。",
    href: "/daytrade/",
    accent: ACCENT.orange,
  },
  {
    key: "swing",
    title: "スイング用スクリーニング",
    description: "準備中です。",
    accent: ACCENT.aqua,
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
              <li
                key={s.key}
                className="hub__card"
                style={{ "--accent": s.accent } as CSSProperties}
              >
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
