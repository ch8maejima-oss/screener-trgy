import type { DaytradeScreeningData } from "@/lib/daytrade-types";

/**
 * 母集団と内訳の開示。
 * 条件を母集団全体に網羅的に適用したこと、除外は機械的な基準によることを示す。
 */
export default function Coverage({ data }: { data: DaytradeScreeningData }) {
  const { counts } = data;
  const items = [
    { label: "母集団", value: counts.population, tone: "base" },
    { label: "貸借銘柄", value: counts.margin_eligible, tone: "base" },
    { label: "上昇モメンタム条件通過", value: counts.buy_passed, tone: "accent" },
    { label: "下落モメンタム条件通過", value: counts.short_passed, tone: "accent" },
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
          個別銘柄を任意に加除することはしていません。
        </dd>

        <dt>貸借銘柄に絞る理由</dt>
        <dd>
          下落モメンタム条件の通過には信用売りができることが前提となるため、
          上昇モメンタム条件も含めて貸借銘柄（制度信用取引で貸借取引ができる
          銘柄）に統一しています。
        </dd>

        <dt>算出不能により対象外とした銘柄</dt>
        <dd>
          直近の株価・出来高履歴が20営業日分に満たない銘柄（新規上場間もない
          銘柄等）です。成績を理由に除外したものではありません。
        </dd>

        <dt>データの基準時点</dt>
        <dd>
          前営業日の大引け時点の株価・出来高に基づきます。
          翌営業日の値動きを保証するものではありません。
        </dd>
      </dl>
    </section>
  );
}
