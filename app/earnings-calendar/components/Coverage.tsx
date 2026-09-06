import type { EarningsCalendarData } from "@/lib/types";

/**
 * 対象範囲の開示。決算発表予定日一覧の中から、貸借銘柄・財務データの両方が
 * そろっている銘柄のみを掲載していることを示す。
 */
export default function Coverage({ data }: { data: EarningsCalendarData }) {
  const { counts, date_range } = data;
  const items = [
    { label: "決算発表予定日 判明銘柄（貸借銘柄）", value: counts.calendar_total, tone: "base" },
    { label: "掲載（財務データあり）", value: counts.listed, tone: "accent" },
    { label: "算出不能により対象外", value: counts.not_evaluable, tone: "muted" },
  ];

  return (
    <section className="coverage" aria-label="対象範囲">
      <h2>対象範囲</h2>
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
        <dd>{data.universe_label}。市場区分・信用区分のみで機械的に定めています。</dd>

        <dt>決算発表予定日のデータ範囲</dt>
        <dd>
          {date_range.開始 ?? "―"} 〜 {date_range.終了 ?? "―"}
          。日本取引所グループが決算期末を迎えたコホートごとに順次公開する一覧を
          結合したもので、より先の期間はまだ対象企業が確定・公開されていません。
        </dd>

        <dt>算出不能により対象外とした銘柄</dt>
        <dd>
          決算発表予定日は判明しているものの、有価証券報告書の営業利益・ROE・EPSの
          いずれも取得できなかった銘柄です。新規上場銘柄等が該当します。
        </dd>
      </dl>
    </section>
  );
}
