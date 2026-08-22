import type { TenbaggerScreeningData } from "@/lib/types";

/**
 * 母集団と内訳の開示。
 * 条件を母集団全体に網羅的に適用したこと、除外は機械的な基準によることを示す。
 */
export default function Coverage({ data }: { data: TenbaggerScreeningData }) {
  const { counts } = data;
  const items = [
    { label: "母集団", value: counts.population, tone: "base" },
    { label: "9/9条件充足（掲載）", value: counts.full_match, tone: "accent" },
    { label: "8/9条件充足（掲載）", value: counts.near_match, tone: "accent" },
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

        <dt>「8/9条件充足」の扱いについて</dt>
        <dd>
          9条件すべてを同時に満たす銘柄は市場全体でもごく僅少（0～数銘柄程度）であるため、
          9条件のうち8条件以上（未達は最大1条件まで）を満たす銘柄を、あらかじめ定めた
          機械的な基準として掲載しています。掲載銘柄には未達の条件を明示しており、
          恣意的に基準を緩めて特定銘柄を選んだものではありません。
        </dd>

        <dt>算出不能により対象外とした銘柄</dt>
        <dd>
          条件の判定に必要な数値が開示から取得できない銘柄です。成績を理由に
          除外したものではありません。主に次のようなケースが該当します。
          <ul>
            <li>上場から日が浅く、5期分の売上高・経常利益が開示されていない会社</li>
            <li>純資産がマイナス（債務超過）等でPBRを算出できない会社</li>
            <li>
              株価データの取得可能期間の制約で、上場からの年数を近似できない会社
            </li>
            <li>米国会計基準の適用会社等、開示体系の違いで一部数値が取得できない会社</li>
          </ul>
        </dd>

        <dt>「上場からの年数」について</dt>
        <dd>
          JPX・EDINETのいずれにも上場年月日そのものが機械的に取得できる形では
          含まれていないため、株価データが遡れる最も古い月を近似値として使っています。
          長期上場銘柄（データ取得可能期間の制約でこの近似値が実際の上場日より
          新しくなる会社）についても、いずれにせよ「8年以内」の条件には該当しないため、
          判定結果への影響はありません。
        </dd>

        <dt>データの基準時点</dt>
        <dd>
          財務数値は各社が直近に提出した有価証券報告書に基づきます。
          有価証券報告書は年1回の提出であるため、決算期によっては
          最大で約1年前の数値となります。株価・出来高は基準日時点のものです。
        </dd>
      </dl>
    </section>
  );
}
