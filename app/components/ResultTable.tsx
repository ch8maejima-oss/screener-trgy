"use client";

import { useMemo, useState } from "react";
import type { Stock } from "@/lib/types";

type SortKey = keyof Pick<
  Stock,
  | "sec_code"
  | "dividend_yield_pct"
  | "roe_pct"
  | "equity_ratio_pct"
  | "current_ratio_pct"
  | "revenue_change_pct"
  | "operating_margin_pct"
>;

const COLUMNS: { key: SortKey; label: string; unit?: string }[] = [
  { key: "dividend_yield_pct", label: "配当利回り", unit: "%" },
  { key: "roe_pct", label: "ROE", unit: "%" },
  { key: "equity_ratio_pct", label: "自己資本比率", unit: "%" },
  { key: "current_ratio_pct", label: "流動比率", unit: "%" },
  { key: "revenue_change_pct", label: "売上高変化", unit: "%" },
  { key: "operating_margin_pct", label: "営業利益率", unit: "%" },
];

const ALL = "すべて";

function fmt(v: number | null, digits = 2) {
  return v === null ? "—" : v.toLocaleString("ja-JP", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

export default function ResultTable({ stocks }: { stocks: Stock[] }) {
  const [sortKey, setSortKey] = useState<SortKey>("dividend_yield_pct");
  const [asc, setAsc] = useState(false);
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
      const x = a[sortKey];
      const y = b[sortKey];
      // 数値が無い銘柄は並び順によらず末尾に置く
      if (x === null && y === null) return 0;
      if (x === null) return 1;
      if (y === null) return -1;
      if (typeof x === "string" || typeof y === "string") {
        return asc
          ? String(x).localeCompare(String(y))
          : String(y).localeCompare(String(x));
      }
      return asc ? x - y : y - x;
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

  return (
    <section className="results" aria-label="条件に合致した銘柄">
      <div className="results__head">
        <h2>条件に合致した銘柄</h2>
        <p className="results__count">
          {rows.length.toLocaleString()} 件
          {rows.length !== stocks.length && (
            <span className="muted">（全 {stocks.length.toLocaleString()} 件中）</span>
          )}
        </p>
      </div>

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
                株価
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
                  {s.name}
                </th>
                <td className="results__sector">{s.sector33}</td>
                <td className="num mono">{fmt(s.price, 1)}</td>
                {COLUMNS.map((c) => (
                  <td key={c.key} className="num mono">
                    {fmt(s[c.key] as number | null)}
                  </td>
                ))}
                <td className="results__period">{s.period_end ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="results__legend">
        「売上高変化」は【主要な経営指標等の推移】5期分のうち最も古い期から直近期までの
        変化率です。並び順は表示上のものであり、銘柄の優劣を示すものではありません。
      </p>
    </section>
  );
}
