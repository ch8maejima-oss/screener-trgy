import { CONDITIONS, type ScreeningData } from "@/lib/types";

/**
 * 選定条件の明示。条件・閾値・データ出所と、条件ごとの充足件数を併記する。
 * 「どの条件で何件に絞られたか」を示すことで、抽出が機械的であることを担保する。
 */
export default function Criteria({ data }: { data: ScreeningData }) {
  return (
    <section className="criteria" aria-label="選定条件">
      <h2>選定条件</h2>
      <p className="criteria__note">
        以下6つの条件をすべて満たす銘柄を掲載しています。条件・閾値はあらかじめ定めたもので、
        結果を見てから変更していません。
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
            {CONDITIONS.map((c) => (
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
        条件ごとの件数です。合計が掲載件数と一致しないのは、掲載には6条件すべての充足が
        必要なためです。
      </p>
    </section>
  );
}
