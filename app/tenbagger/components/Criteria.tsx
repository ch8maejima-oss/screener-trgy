import { CONDITIONS_TENBAGGER, type TenbaggerScreeningData } from "@/lib/types";

/**
 * 選定条件の明示。条件・閾値・データ出所と、条件ごとの充足件数を併記する。
 * 「どの条件で何件に絞られたか」を示すことで、抽出が機械的であることを担保する。
 */
export default function Criteria({ data }: { data: TenbaggerScreeningData }) {
  return (
    <section className="criteria" aria-label="選定条件">
      <h2>選定条件</h2>
      <p className="criteria__note">
        以下9つの条件のうち、<strong>8条件以上（未達は最大1条件まで）</strong>を満たす銘柄を掲載しています。
        9条件すべてを同時に満たす銘柄は市場全体でもごく僅少（0～数銘柄程度）であるため、
        「あと1条件」の銘柄も、どの条件が未達かを明示した上であわせて掲載する方式としています。
        条件・閾値はあらかじめ定めたもので、結果を見てから変更していません。過去10年間の
        日本株の株価上昇事例（10倍株・7倍株）の傾向調査をもとに設定しています。
      </p>
      <div className="table-scroll">
        <table className="criteria__table">
          <thead>
            <tr>
              <th scope="col">#</th>
              <th scope="col">条件</th>
              <th scope="col">閾値</th>
              <th scope="col">算出方法・出所</th>
              <th scope="col" className="num">
                充足
              </th>
              <th scope="col" className="num">
                算出不能
              </th>
            </tr>
          </thead>
          <tbody>
            {CONDITIONS_TENBAGGER.map((c) => (
              <tr key={c.key}>
                <td className="num">{c.no}</td>
                <th scope="row">{c.label}</th>
                <td className="criteria__rule">{c.rule}</td>
                <td className="criteria__source">{c.source}</td>
                <td className="num">
                  {data.per_condition_passed[c.key].toLocaleString()}
                </td>
                <td className="num muted">
                  {data.per_condition_missing[c.key].toLocaleString()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="criteria__footnote">
        「充足」「算出不能」は母集団 {data.counts.population.toLocaleString()} 銘柄に対する
        条件ごとの件数です。合計が掲載件数と一致しないのは、掲載には9条件中8条件以上の充足が
        必要なためです（内訳: 9/9条件充足 {data.counts.full_match.toLocaleString()} 銘柄、
        8/9条件充足 {data.counts.near_match.toLocaleString()} 銘柄）。
      </p>
    </section>
  );
}
