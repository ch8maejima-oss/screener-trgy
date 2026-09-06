import type { Swing2ScreeningData } from "@/lib/types";

const CONDITIONS: { key: string; no: number; label: string; rule: string }[] = [
  { key: "c1_deviation", no: 1, label: "理論PBRとの下方乖離",
    rule: "理論PBR（調整後ROE×業種平均PER）に対する実績PBRの下方乖離率が20%以上" },
  { key: "c2_roe_quality", no: 2, label: "ROEの質",
    rule: "調整後ROE（経常利益ベース）が8%以上、かつ過去3年間で2期連続悪化していないこと" },
  { key: "c3_safety", no: 3, label: "安全性フィルター",
    rule: "PERが業種平均PER（中央値）より低い、かつ自己資本比率が40%以上" },
  { key: "c4_technical", no: 4, label: "テクニカル条件",
    rule: "ゴールデンクロス／25日移動平均線の反転／出来高急増（底値圏）のいずれか1つ以上" },
];

export default function Methodology({ data }: { data: Swing2ScreeningData }) {
  return (
    <section className="criteria" aria-label="選定条件">
      <h2>選定条件</h2>
      <p className="criteria__note">
        以下4つの条件をすべて満たした銘柄を掲載しています。「理論PBR」は
        PBR＝ROE×PERという会計上の関係式を用いて、実績ROE（特別損益を除いた
        経常利益ベース）に業種平均PER（中央値）を乗じた参考値です。低ROE銘柄の
        低PBRを「割安」と誤認しないよう、ROE水準・トレンドを別条件（②）で
        併せて要求しています。条件・閾値は結果を見てから変更していません。
      </p>
      <div className="table-scroll">
        <table className="criteria__table">
          <thead>
            <tr>
              <th scope="col">#</th>
              <th scope="col">条件</th>
              <th scope="col">ルール</th>
              <th scope="col" className="num">充足</th>
              <th scope="col" className="num">算出不能</th>
            </tr>
          </thead>
          <tbody>
            {CONDITIONS.map((c) => (
              <tr key={c.key}>
                <td className="num">{c.no}</td>
                <th scope="row">{c.label}</th>
                <td className="criteria__rule">{c.rule}</td>
                <td className="num">{(data.per_condition_passed[c.key] ?? 0).toLocaleString()}</td>
                <td className="num muted">{(data.per_condition_missing[c.key] ?? 0).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="criteria__footnote">
        対象は時価総額{(data.thresholds.market_cap_min / 1e8).toLocaleString()}億円以上・
        3ヶ月平均出来高{data.thresholds.avg_volume_min.toLocaleString()}株以上の
        中大型・流動性銘柄（{data.counts.size_liquidity_passed.toLocaleString()}銘柄）に
        限定しています。「充足」「算出不能」はこのフィルター通過銘柄に対する件数です。
      </p>
    </section>
  );
}
