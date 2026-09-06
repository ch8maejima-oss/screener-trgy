import type { Swing2ScreeningData } from "@/lib/types";

export default function Coverage({ data }: { data: Swing2ScreeningData }) {
  const { counts } = data;
  const items = [
    { label: "母集団", value: counts.population, tone: "base" },
    { label: "規模・流動性フィルター通過", value: counts.size_liquidity_passed, tone: "base" },
    { label: "全条件充足（掲載）", value: counts.listed, tone: "accent" },
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
        <dd>{data.universe_label}。市場区分・規模・流動性のみで機械的に定めています。</dd>

        <dt>算出不能により対象外とした銘柄</dt>
        <dd>
          条件の判定に必要な数値（財務データ・株価履歴等）が取得できない銘柄です。
          成績を理由に除外したものではありません。上場から日が浅く25日分の株価
          データがそろわない銘柄、赤字等でPER・ROEが算出できない銘柄等が該当します。
        </dd>

        <dt>データの基準時点</dt>
        <dd>
          財務数値は各社が直近に提出した有価証券報告書に基づきます。
          株価・テクニカル指標は基準日時点のものです。
        </dd>
      </dl>
    </section>
  );
}
