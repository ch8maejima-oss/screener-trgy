import fs from "fs";
import path from "path";
import type { Metadata } from "next";
import type { DaytradeSimPosition, DaytradeSimState } from "@/lib/types";
import EquitySimChart from "./components/EquitySimChart";
import { tradingViewUrl } from "@/lib/tradingview";

export const metadata: Metadata = {
  title: "デイトレード用スクリーニング① フォワードシミュレーション | スクリーニング銘柄一覧",
  description:
    "デイトレード用スクリーニング①（上昇モメンタム）の通過銘柄を、あらかじめ固定した機械的な売買ルールで仮想売買した場合の、本日以降の成績記録です。実際の売買は行っていません。",
};

const EXIT_REASON_LABEL: Record<string, string> = {
  target: "利食い（前日騰落率と同幅の上昇に到達）",
  stopLoss: "損切り（後場終値がエントリー株価より5%以上下落）",
  maxHold: "手仕舞い（保有上限＝翌営業日前場終値）",
};

function loadState(): DaytradeSimState | null {
  try {
    const p = path.join(process.cwd(), "data", "daytrade-sim-state.json");
    const raw = fs.readFileSync(p, "utf-8");
    return JSON.parse(raw) as DaytradeSimState;
  } catch {
    return null;
  }
}

function fmtPrice(v: number | null): string {
  return v !== null ? `¥${Math.round(v).toLocaleString("ja-JP")}` : "—";
}

function fmtReturn(v: number | null): string {
  if (v === null) return "—";
  return `${v >= 0 ? "+" : ""}${v.toFixed(1)}%`;
}

function PositionsTable({ positions, showExit }: { positions: DaytradeSimPosition[]; showExit: boolean }) {
  if (positions.length === 0) {
    return <p className="equity-sim__empty">該当するポジションはありません。</p>;
  }
  return (
    <div className="table-scroll">
      <table className="results__table">
        <thead>
          <tr>
            <th scope="col">コード</th>
            <th scope="col">銘柄名</th>
            <th scope="col">エントリー日</th>
            <th scope="col" className="num">エントリー価格（前場終値）</th>
            <th scope="col" className="num">利食い目標</th>
            {showExit && (
              <>
                <th scope="col">決済日</th>
                <th scope="col" className="num">決済価格</th>
                <th scope="col">理由</th>
              </>
            )}
            <th scope="col" className="num">リターン</th>
          </tr>
        </thead>
        <tbody>
          {positions.map((pos) => (
            <tr key={pos.id}>
              <td className="mono">{pos.code}</td>
              <th scope="row" className="results__name">
                <a
                  href={tradingViewUrl(pos.code)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="results__tv-link"
                  title="TradingViewでチャートを見る（外部サイト）"
                >
                  {pos.name}
                </a>
              </th>
              <td className="mono">{pos.entryDate}</td>
              <td className="num mono">{fmtPrice(pos.entryPrice)}</td>
              <td className="num mono">{fmtPrice(pos.targetPrice)}</td>
              {showExit && (
                <>
                  <td className="mono">{pos.exitDate ?? "—"}</td>
                  <td className="num mono">{fmtPrice(pos.exitPrice)}</td>
                  <td>{pos.exitReason ? EXIT_REASON_LABEL[pos.exitReason] : "—"}</td>
                </>
              )}
              <td className={`num mono ${pos.returnPct !== null && pos.returnPct < 0 ? "equity-sim__cell-negative" : "equity-sim__cell-positive"}`}>
                {fmtReturn(pos.returnPct)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function Home() {
  const state = loadState();

  if (!state || state.equityCurve.length === 0) {
    return (
      <div className="home">
        <section className="intro">
          <h1>デイトレード用スクリーニング① フォワードシミュレーション</h1>
          <p className="intro__lead">記録を準備中です。しばらくしてから改めてご確認ください。</p>
        </section>
      </div>
    );
  }

  const latest = state.equityCurve[state.equityCurve.length - 1];
  const closedPositions = [...state.positions]
    .filter((p) => p.status === "closed")
    .sort((a, b) => (b.exitDate ?? "").localeCompare(a.exitDate ?? ""));
  const openPositions = [...state.positions]
    .filter((p) => p.status === "open")
    .sort((a, b) => b.entryDate.localeCompare(a.entryDate));
  const winRate = latest.closedCount > 0 ? (latest.winCount / latest.closedCount) * 100 : null;

  function average(values: number[]): number | null {
    if (values.length === 0) return null;
    return values.reduce((sum, v) => sum + v, 0) / values.length;
  }
  const avgClosedReturn = average(
    closedPositions.map((p) => p.returnPct).filter((v): v is number => v !== null),
  );

  return (
    <div className="home equity-sim">
      <section className="intro">
        <h1>デイトレード用スクリーニング① フォワードシミュレーション</h1>
        <p className="intro__lead">
          デイトレード用スクリーニング①「上昇モメンタム」の通過銘柄を買った場合、
          このスクリーニング条件は実際に機能するのか。{state.startDate}から、
          あらかじめ固定した機械的な売買ルールでの仮想売買を、勝敗を問わず
          すべて記録・追跡しています。
        </p>
      </section>

      <div className="equity-sim__notice">
        <p className="equity-sim__notice-title">
          これは仮想シミュレーションです（実際の売買ではありません）
        </p>
        <ul>
          <li>実際の発注は一切行っていません。すべて計算上の記録です。</li>
          <li>手数料・税金・スリッページは考慮していません。</li>
          <li>資金制約は考慮していません（該当銘柄をすべて同時に購入できる前提です）。</li>
          <li>
            エントリー・利食い・損切り・保有上限の判定には、いずれも取引時間中の
            実勢株価（5分足）を用いています。
          </li>
          <li>{state.startDate}以降のデータのみを記録しており、過去に遡って算出したもの（バックテスト）ではありません。</li>
          <li>勝ちトレード・負けトレードの両方を、選別せずすべて記録・表示しています。</li>
          <li>
            売買ルールは{state.startDate}に固定したもので、その後の成績を見て有利になるよう
            変更することはありません。変更する場合は、変更日・変更内容・変更理由をこのページに
            記録します。
          </li>
          <li>
            買いの基準（上昇モメンタム）は、当社のデイトレード用スクリーニング①の出力を
            用いています。当該スクリーニング条件自体に前提や偏りがある場合、その影響は
            本シミュレーションの結果にも及びます。本記録はスクリーニング条件と実際の値動きの
            関係を検証する一つの試みであり、条件の正確性・優位性を保証するものではありません。
          </li>
          <li>将来の運用成果を示唆・保証するものではなく、特定銘柄の売買を推奨・勧誘するものでもありません。</li>
          <li>株式投資には元本割れを含む価格変動リスクがあります。</li>
        </ul>
      </div>

      <section className="equity-sim__rules">
        <h2>売買ルール</h2>
        <ol>
          <li>
            <b>エントリー</b>：当日デイトレード用スクリーニング①の上昇モメンタム条件を
            通過した銘柄を、前場終値（11:30時点の株価）で仮想的に成行エントリーします。
          </li>
          <li>
            <b>利食い</b>：後場中に、株価がエントリー時点の「前日騰落率」と同じ幅だけ
            上昇した水準に達したら、その水準で手仕舞います。
          </li>
          <li>
            <b>手仕舞い（損切り）</b>：利食いに該当せず、後場終値がエントリー株価より
            5%以上下落していたら、後場終値で手仕舞います。
          </li>
          <li>
            <b>手仕舞い（保有上限）</b>：利食い・損切りいずれにも該当しなかった場合、
            翌営業日の前場終値で強制的に手仕舞います（保有は最大1泊）。
          </li>
        </ol>
      </section>

      <section className="equity-sim__summary">
        <div className="equity-sim__stat">
          <span className="equity-sim__stat-label">平均リターン（保有中含む全ポジション）</span>
          <span className={`equity-sim__stat-value ${latest.avgReturnPct >= 0 ? "is-positive" : "is-negative"}`}>
            {fmtReturn(latest.avgReturnPct)}
          </span>
        </div>
        <div className="equity-sim__stat">
          <span className="equity-sim__stat-label">└ 決済済みの平均リターン</span>
          <span className={`equity-sim__stat-value ${avgClosedReturn !== null && avgClosedReturn >= 0 ? "is-positive" : "is-negative"}`}>
            {fmtReturn(avgClosedReturn)}
          </span>
        </div>
        <div className="equity-sim__stat">
          <span className="equity-sim__stat-label">決済済み（勝ち／負け）</span>
          <span className="equity-sim__stat-value">
            {latest.closedCount}件（{latest.winCount} / {latest.lossCount}）
          </span>
        </div>
        <div className="equity-sim__stat">
          <span className="equity-sim__stat-label">勝率</span>
          <span className="equity-sim__stat-value">{winRate !== null ? `${winRate.toFixed(1)}%` : "—"}</span>
        </div>
        <div className="equity-sim__stat">
          <span className="equity-sim__stat-label">保有中</span>
          <span className="equity-sim__stat-value">{latest.openCount}件</span>
        </div>
      </section>

      <EquitySimChart curve={state.equityCurve} nikkei={state.nikkei} topix={state.topix} />
      <p className="equity-sim__chart-caption">
        グラフの値は「保有中ポジションの含み損益＋決済済みポジションの確定損益」を全ポジションで単純平均した推移です（勝敗を問わず全件を含みます）。
        ベンチマークの日経225・TOPIX（TOPIX連動ETF・銘柄コード1306で代用）は、{state.startDate}の水準を0%として指数化しています。
        いずれも指数・ETFの価格変動のみを反映した参考値で、配当（分配金）は含みません。
      </p>
      <p className="equity-sim__notice-inline">
        ※このグラフは実際の売買を伴わない仮想シミュレーションの記録です。将来の運用成果を示唆・保証するものではありません。
      </p>

      <section className="equity-sim__positions">
        <h2>決済済みポジション（{closedPositions.length}件・勝敗を問わずすべて表示）</h2>
        <PositionsTable positions={closedPositions} showExit />

        <h2>保有中のポジション</h2>
        <PositionsTable positions={openPositions} showExit={false} />
      </section>

      <p className="equity-sim__updated">最終更新: {state.lastUpdated}</p>
    </div>
  );
}
