import {
  COMMON_CONDITIONS,
  BUY_CONDITIONS,
  SHORT_CONDITIONS,
  type DaytradeScreeningData,
} from "@/lib/daytrade-types";

/**
 * 選定条件の明示。共通条件と、上昇モメンタム・下落モメンタムそれぞれの固有条件を分けて示す。
 * 「前日+2〜10%」（上昇）と「前日-2〜-10%」（下落）は同時に成立しない対の条件のため、
 * 2つのリストに分けている。
 */
export default function Criteria({ data }: { data: DaytradeScreeningData }) {
  return (
    <section className="criteria" aria-label="選定条件">
      <h2>選定条件</h2>
      <p className="criteria__note">
        以下の共通条件に加え、上昇モメンタム・下落モメンタムいずれかの固有条件を
        すべて満たす銘柄を掲載しています。条件・閾値はあらかじめ定めたもので、
        結果を見てから変更していません。
      </p>

      <h3 className="criteria__subhead">共通条件</h3>
      <div className="table-scroll">
        <table className="criteria__table">
          <thead>
            <tr>
              <th scope="col">条件</th>
              <th scope="col">基準</th>
              <th scope="col">出所</th>
            </tr>
          </thead>
          <tbody>
            {COMMON_CONDITIONS.map((c) => (
              <tr key={c.label}>
                <th scope="row">{c.label}</th>
                <td className="criteria__rule">{c.rule}</td>
                <td className="criteria__source">{c.source}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="criteria__pair">
        <div>
          <h3 className="criteria__subhead">
            上昇モメンタム条件通過銘柄— {data.counts.buy_passed.toLocaleString()}件
          </h3>
          <table className="criteria__table">
            <thead>
              <tr>
                <th scope="col">条件</th>
                <th scope="col">基準</th>
              </tr>
            </thead>
            <tbody>
              {BUY_CONDITIONS.map((c) => (
                <tr key={c.label}>
                  <th scope="row">{c.label}</th>
                  <td className="criteria__rule">{c.rule}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div>
          <h3 className="criteria__subhead">
            下落モメンタム条件通過銘柄— {data.counts.short_passed.toLocaleString()}件
          </h3>
          <table className="criteria__table">
            <thead>
              <tr>
                <th scope="col">条件</th>
                <th scope="col">基準</th>
              </tr>
            </thead>
            <tbody>
              {SHORT_CONDITIONS.map((c) => (
                <tr key={c.label}>
                  <th scope="row">{c.label}</th>
                  <td className="criteria__rule">{c.rule}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <p className="criteria__footnote">
        時価総額500億円以上の銘柄は除外せず、流動性の目安として一覧の並び順で
        優先表示しています（除外条件ではなく、当社が有望と判断した順ではありません）。
      </p>
    </section>
  );
}
