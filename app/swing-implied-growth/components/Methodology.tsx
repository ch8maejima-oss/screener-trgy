import type { Swing1ScreeningData } from "@/lib/types";

/**
 * 計算モデル・前提の明示。合否条件ではなく計算式そのものが対象のため、
 * tenbagger等のCriteriaとは異なり「何を・どういう前提で計算したか」を示す。
 */
export default function Methodology({ data }: { data: Swing1ScreeningData }) {
  const a = data.assumptions;
  return (
    <section className="criteria" aria-label="計算の前提">
      <h2>計算の前提</h2>
      <p className="criteria__note">
        企業価値(EV) = 時価総額 + 有利子負債 − 現金同等物 が、「フリーキャッシュフロー(FCF)が
        今後{a.forecast_years}年間は年率gで成長し、{a.forecast_years + 1}年目以降は永久成長率
        {a.terminal_growth_pct}%で成長し続ける」と仮定した場合の割引現在価値と一致するよう、
        年率成長率g（＝市場織込み成長率）を逆算しています。前提は結果を見てから
        調整していません。
      </p>
      <div className="table-scroll">
        <table className="criteria__table">
          <thead>
            <tr>
              <th scope="col">項目</th>
              <th scope="col">前提・算出方法</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <th scope="row">FCF（ベース値）</th>
              <td className="criteria__rule">
                有価証券報告書開示の営業活動によるキャッシュ・フロー − 設備投資額
                （【設備投資等の概要】の開示値）。投資活動によるキャッシュ・フローを
                そのまま用いると、現金潤沢な企業ほど財務目的の預入・有価証券売買で
                数値が歪むため、実際の設備投資額のみを控除しています。
              </td>
            </tr>
            <tr>
              <th scope="row">割引率（WACC）</th>
              <td className="criteria__rule">
                CAPMで銘柄ごとに算出。株主資本コスト = 無リスク金利（{a.risk_free_rate_pct}%）
                ＋ β × 株式リスクプレミアム（{a.equity_risk_premium_pct}%）。
                βは過去5年間の月次株価騰落率を、TOPIX連動ETF（1306）に対して回帰した値。
                負債コスト（税引後）= 支払利息 ÷ 有利子負債 ×（1 − 実効税率
                {a.tax_rate_pct}%）。株主資本コストと負債コストを、時価総額と
                有利子負債の比率で加重平均。
              </td>
            </tr>
            <tr>
              <th scope="row">予測期間・永久成長率</th>
              <td className="criteria__rule">
                {a.forecast_years}年間の明示的な予測期間の後、{a.terminal_growth_pct}%の
                永久成長率で継続すると仮定（2段階DCFモデル）。
              </td>
            </tr>
            <tr>
              <th scope="row">10年後想定営業利益（参考値）</th>
              <td className="criteria__rule">
                現在の営業利益を、逆算した市場織込み成長率gで{a.forecast_years}年間
                複利成長させた参考値（FCFと営業利益が同率で成長するという単純化した仮定）。
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <p className="criteria__footnote">
        無リスク金利・株式リスクプレミアム・実効税率・永久成長率は全銘柄共通の
        固定値としており、相場水準が大きく変わった場合に見直します。
        β・WACC・市場織込み成長率は銘柄ごとに個別に算出しています。
      </p>
    </section>
  );
}
