import type { ScreeningData } from "@/lib/types";

/**
 * 母集団と内訳の開示。
 * 条件を母集団全体に網羅的に適用したこと、除外は機械的な基準によることを示す。
 */
export default function Coverage({ data }: { data: ScreeningData }) {
  const { counts } = data;
  const items = [
    { label: "母集団", value: counts.population, tone: "base" },
    { label: "全条件を充足（掲載）", value: counts.passed, tone: "accent" },
    { label: "条件を満たさず", value: counts.failed, tone: "base" },
    { label: "算出不能により対象外", value: counts.not_evaluable, tone: "muted" },
  ];

  return (
    <section className="coverage" aria-label="母集団と内訳">
      <h2>母集団と内訳</h2>
      <ul className="coverage__stats">
        {items.map((it) => (
          <li key={it.label} className={`coverage__stat coverage__stat--${it.tone}`}>
            <span className="coverage__value">{it.value.toLocaleString()}</span>
            <span className="coverage__label">{it.label}</span>
          </li>
        ))}
      </ul>

      <dl className="coverage__detail">
        <dt>対象</dt>
        <dd>
          {data.universe_label}。市場区分のみで機械的に定めており、
          個別銘柄を任意に加除することはしていません。優先株式・社債型種類株式は
          普通株式ではないため対象外です。
        </dd>

        <dt>算出不能により対象外とした銘柄</dt>
        <dd>
          条件の判定に必要な数値が開示から取得できない銘柄です。成績を理由に
          除外したものではありません。主に次の3つが該当します。
          <ul>
            <li>
              銀行業・保険業など、貸借対照表に流動／固定の区分を持たない業種
              （条件4を算出できません）
            </li>
            <li>
              米国会計基準の適用会社。連結財務諸表がXBRL形式で提供されないため
              条件4・6の数値を取得できません
            </li>
            <li>上場から日が浅く、5期分の売上高が開示されていない会社（条件5）</li>
          </ul>
        </dd>

        <dt>データの基準時点</dt>
        <dd>
          財務数値は各社が直近に提出した有価証券報告書に基づきます。
          有価証券報告書は年1回の提出であるため、決算期によっては
          最大で約1年前の数値となります。株価および配当は基準日時点のものです。
        </dd>
      </dl>
    </section>
  );
}
