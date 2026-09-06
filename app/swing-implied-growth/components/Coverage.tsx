import type { Swing1ScreeningData } from "@/lib/types";

/**
 * 母集団と内訳の開示。
 * 全銘柄に計算モデルを網羅的に適用したこと、除外は機械的な基準によることを示す。
 */
export default function Coverage({ data }: { data: Swing1ScreeningData }) {
  const { counts } = data;
  const items = [
    { label: "母集団", value: counts.population, tone: "base" },
    { label: "掲載", value: counts.listed, tone: "accent" },
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

        <dt>算出不能により対象外とした銘柄の内訳</dt>
        <dd>
          計算に必要な数値が開示から取得できない、または現在の株価とWACC・FCFの
          関係上、現実的な範囲（年率−50%〜+200%）でEVと一致する成長率が
          存在しない銘柄です。成績を理由に除外したものではありません。
          <ul>
            {Object.entries(data.exclusion_reasons).map(([reason, count]) => (
              <li key={reason}>
                {reason}: {count.toLocaleString()}銘柄
              </li>
            ))}
          </ul>
        </dd>

        <dt>データの基準時点</dt>
        <dd>
          財務数値は各社が直近に提出した有価証券報告書に基づきます。
          有価証券報告書は年1回の提出であるため、決算期によっては
          最大で約1年前の数値となります。株価は基準日時点のものです。
          β（5年月次リターン）は月次で再計算する運用のため、直近の
          株価変動を即座には反映しません。
        </dd>
      </dl>
    </section>
  );
}
