"use client";

import { useMemo, useState } from "react";
import type { DaytradeStock } from "@/lib/daytrade-types";
import { tradingViewUrl } from "@/lib/tradingview";

type SortKey = keyof Pick<
  DaytradeStock,
  | "sec_code"
  | "price"
  | "change_1d_pct"
  | "change_5d_pct"
  | "change_20d_pct"
  | "volume"
  | "turnover_yen"
  | "market_cap"
>;

const COLUMNS: { key: SortKey; label: string }[] = [
  { key: "price", label: "株価" },
  { key: "change_1d_pct", label: "前日騰落率" },
  { key: "change_5d_pct", label: "5日騰落率" },
  { key: "change_20d_pct", label: "20日騰落率" },
  { key: "volume", label: "出来高" },
  { key: "turnover_yen", label: "売買代金" },
  { key: "market_cap", label: "時価総額" },
];

const ALL = "すべて";

function fmtNum(v: number | null, digits = 2) {
  return v === null
    ? "—"
    : v.toLocaleString("ja-JP", { minimumFractionDigits: digits, maximumFractionDigits: digits });
}
function fmtOku(v: number | null) {
  return v === null
    ? "—"
    : `${(v / 1e8).toLocaleString("ja-JP", { minimumFractionDigits: 1, maximumFractionDigits: 1 })}億円`;
}
function fmtShares(v: number | null) {
  return v === null ? "—" : `${Math.round(v).toLocaleString("ja-JP")}株`;
}

/**
 * 上昇モメンタム・下落モメンタムで共用するテーブル。時価総額500億円以上の銘柄を
 * 常に上位に優先表示し（除外ではない）、その中で選択中の列で並べ替える。
 */
export default function MomentumTable({
  stocks,
  direction,
}: {
  stocks: DaytradeStock[];
  direction: "buy" | "short";
}) {
  // 初期表示は銘柄コード順（中立）。値動きの大小で並べるかはユーザーの操作に委ねる。
  const [sortKey, setSortKey] = useState<SortKey>("sec_code");
  const [asc, setAsc] = useState(true);
  const [market, setMarket] = useState(ALL);
  const [sector, setSector] = useState(ALL);

  const markets = useMemo(
    () => [ALL, ...Array.from(new Set(stocks.map((s) => s.market))).sort()],
    [stocks],
  );
  const sectors = useMemo(
    () => [ALL, ...Array.from(new Set(stocks.map((s) => s.sector33))).sort()],
    [stocks],
  );

  const rows = useMemo(() => {
    const filtered = stocks.filter(
      (s) =>
        (market === ALL || s.market === market) &&
        (sector === ALL || s.sector33 === sector),
    );
    return [...filtered].sort((a, b) => {
      if (a.is_large_cap !== b.is_large_cap) return a.is_large_cap ? -1 : 1;
      const x = a[sortKey];
      const y = b[sortKey];
      if (x === null && y === null) return 0;
      if (x === null) return 1;
      if (y === null) return -1;
      if (typeof x === "string" || typeof y === "string") {
        return asc
          ? String(x).localeCompare(String(y))
          : String(y).localeCompare(String(x));
      }
      return asc ? (x as number) - (y as number) : (y as number) - (x as number);
    });
  }, [stocks, sortKey, asc, market, sector]);

  function toggleSort(key: SortKey) {
    if (key === sortKey) {
      setAsc(!asc);
    } else {
      setSortKey(key);
      setAsc(false);
    }
  }

  const title =
    direction === "buy" ? "上昇モメンタム条件通過銘柄" : "下落モメンタム条件通過銘柄";

  return (
    <section className="results" aria-label={title}>
      <div className="results__head">
        <h2>{title}</h2>
        <p className="results__count">
          {rows.length.toLocaleString()} 件
          {rows.length !== stocks.length && (
            <span className="muted">（全 {stocks.length.toLocaleString()} 件中）</span>
          )}
        </p>
      </div>

      <p className="results__section-note">
        条件に合致した銘柄を機械的に全件掲載したものであり、売買を推奨・勧誘するものではありません。
        {direction === "short" &&
          "信用取引（空売り）は元本を超える損失が生じる可能性があります。"}
      </p>

      <div className="results__filters">
        <label>
          市場
          <select value={market} onChange={(e) => setMarket(e.target.value)}>
            {markets.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
        </label>
        <label>
          業種
          <select value={sector} onChange={(e) => setSector(e.target.value)}>
            {sectors.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </label>
        <p className="results__filter-note">
          時価総額500億円以上の銘柄（大型バッジ）を優先して上位に表示しています。
          絞り込みと並べ替えは表示上の操作です。
        </p>
      </div>

      <div className="table-scroll">
        <table className="results__table">
          <thead>
            <tr>
              <th scope="col">コード</th>
              <th scope="col">銘柄名</th>
              <th scope="col">業種</th>
              {COLUMNS.map((c) => (
                <th key={c.key} scope="col" className="num">
                  <button
                    type="button"
                    onClick={() => toggleSort(c.key)}
                    className={sortKey === c.key ? "is-active" : ""}
                    aria-label={`${c.label}で並べ替え`}
                  >
                    {c.label}
                    <span aria-hidden="true">
                      {sortKey === c.key ? (asc ? " ▲" : " ▼") : " ⇅"}
                    </span>
                  </button>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((s) => (
              <tr key={s.sec_code}>
                <td className="mono">{s.sec_code}</td>
                <th scope="row" className="results__name">
                  <a
                    href={tradingViewUrl(s.sec_code)}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="results__tv-link"
                    title="TradingViewでチャートを見る（外部サイト）"
                  >
                    {s.name}
                  </a>
                  {s.is_large_cap && <span className="results__badge">大型</span>}
                </th>
                <td className="results__sector">{s.sector33}</td>
                <td className="num mono">{fmtNum(s.price, 1)}</td>
                <td className="num mono">{fmtNum(s.change_1d_pct)}</td>
                <td className="num mono">{fmtNum(s.change_5d_pct)}</td>
                <td className="num mono">{fmtNum(s.change_20d_pct)}</td>
                <td className="num mono">{fmtShares(s.volume)}</td>
                <td className="num mono">{fmtOku(s.turnover_yen)}</td>
                <td className="num mono">{fmtOku(s.market_cap)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="results__legend">
        並び順は表示上のものであり、銘柄の優劣や将来の値動きを示すものではありません。
      </p>
    </section>
  );
}
