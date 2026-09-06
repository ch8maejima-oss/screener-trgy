"use client";

import { useMemo, useState } from "react";
import type { Swing1Stock } from "@/lib/types";
import { tradingViewUrl } from "@/lib/tradingview";

type SortKey = keyof Pick<
  Swing1Stock,
  "price" | "market_cap" | "wacc_pct" | "implied_growth_pct" | "projected_operating_income_10y"
>;

function fmt(v: number | null, digits = 2) {
  return v === null ? "—" : v.toLocaleString("ja-JP", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}
function fmtOku(v: number | null) {
  if (v === null) return "—";
  const sign = v < 0 ? "-" : "";
  return `${sign}${(Math.abs(v) / 1e8).toLocaleString("ja-JP", { minimumFractionDigits: 1, maximumFractionDigits: 1 })}億円`;
}

const COLUMNS: { key: SortKey; label: string; format: (v: number | null) => string }[] = [
  { key: "market_cap", label: "時価総額", format: fmtOku },
  { key: "wacc_pct", label: "期待資本コスト(WACC)", format: (v) => fmt(v, 2) + (v === null ? "" : "%") },
  { key: "implied_growth_pct", label: "FCF成長率（市場織込）", format: (v) => fmt(v, 1) + (v === null ? "" : "%") },
  { key: "projected_operating_income_10y", label: "10年後想定営業利益", format: fmtOku },
];

const ALL = "すべて";

export default function ResultTable({ stocks }: { stocks: Swing1Stock[] }) {
  const [sortKey, setSortKey] = useState<SortKey>("implied_growth_pct");
  const [asc, setAsc] = useState(false);
  const [market, setMarket] = useState(ALL);
  const [sector, setSector] = useState(ALL);

  const sectors = useMemo(
    () => [ALL, ...Array.from(new Set(stocks.map((s) => s.sector33))).sort()],
    [stocks],
  );

  const rows = useMemo(() => {
    const filtered = stocks.filter((s) => sector === ALL || s.sector33 === sector);
    return [...filtered].sort((a, b) => {
      const x = a[sortKey];
      const y = b[sortKey];
      if (x === null && y === null) return 0;
      if (x === null) return 1;
      if (y === null) return -1;
      return asc ? x - y : y - x;
    });
  }, [stocks, sortKey, asc, sector]);

  function toggleSort(key: SortKey) {
    if (key === sortKey) {
      setAsc(!asc);
    } else {
      setSortKey(key);
      setAsc(false);
    }
  }

  return (
    <section className="results" aria-label="市場織込み成長率の一覧">
      <div className="results__head">
        <h2>市場織込み成長率の一覧</h2>
        <p className="results__count">
          {rows.length.toLocaleString()} 件
          {rows.length !== stocks.length && (
            <span className="muted">（全 {stocks.length.toLocaleString()} 件中）</span>
          )}
        </p>
      </div>

      <div className="results__filters">
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
          絞り込みと並べ替えは表示上の操作です。掲載対象そのものは変わりません。
        </p>
      </div>

      <div className="table-scroll">
        <table className="results__table">
          <thead>
            <tr>
              <th scope="col">コード</th>
              <th scope="col">銘柄名</th>
              <th scope="col">業種</th>
              <th scope="col" className="num">
                現在株価
              </th>
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
              <th scope="col">決算期</th>
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
                </th>
                <td className="results__sector">{s.sector33}</td>
                <td className="num mono">{fmt(s.price, 1)}</td>
                {COLUMNS.map((c) => (
                  <td key={c.key} className="num mono">
                    {c.format(s[c.key] as number | null)}
                  </td>
                ))}
                <td className="results__period">{s.period_end ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="results__legend">
        「期待資本コスト(WACC)」はCAPMで銘柄ごとに算出した加重平均資本コストです。
        「FCF成長率（市場織込）」は、現在の株価が正当化されるために必要な年率成長率を
        2段階DCFで逆算した値です。「10年後想定営業利益」は、現在の営業利益を
        この成長率で10年複利成長させた参考値であり、当社の業績予想ではありません。
        並び順は表示上のものであり、銘柄の優劣を示すものではありません。
      </p>
    </section>
  );
}
