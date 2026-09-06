"use client";

import { useMemo, useState } from "react";
import type { EarningsCalendarStock } from "@/lib/types";
import { tradingViewUrl } from "@/lib/tradingview";

type SortKey = keyof Pick<
  EarningsCalendarStock,
  "announcement_date" | "operating_income" | "roe_pct" | "eps"
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

const COLUMNS: { key: SortKey; label: string; format: (v: string | number | null) => string }[] = [
  { key: "operating_income", label: "営業利益（直近実績）", format: (v) => fmtOku(v as number | null) },
  { key: "roe_pct", label: "ROE", format: (v) => fmt(v as number | null, 1) + (v === null ? "" : "%") },
  { key: "eps", label: "EPS（直近実績）", format: (v) => fmt(v as number | null, 2) + (v === null ? "" : "円") },
];

const ALL = "すべて";

export default function CalendarTable({ stocks }: { stocks: EarningsCalendarStock[] }) {
  const [sortKey, setSortKey] = useState<SortKey>("announcement_date");
  const [asc, setAsc] = useState(true);
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
      if (typeof x === "string" || typeof y === "string") {
        return asc ? String(x).localeCompare(String(y)) : String(y).localeCompare(String(x));
      }
      return asc ? x - y : y - x;
    });
  }, [stocks, sortKey, asc, sector]);

  function toggleSort(key: SortKey) {
    if (key === sortKey) {
      setAsc(!asc);
    } else {
      setSortKey(key);
      setAsc(key === "announcement_date");
    }
  }

  return (
    <section className="results" aria-label="決算発表カレンダー">
      <div className="results__head">
        <h2>決算発表カレンダー</h2>
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
              <th scope="col">
                <button
                  type="button"
                  onClick={() => toggleSort("announcement_date")}
                  className={sortKey === "announcement_date" ? "is-active" : ""}
                  aria-label="決算発表予定日で並べ替え"
                >
                  決算発表予定日
                  <span aria-hidden="true">
                    {sortKey === "announcement_date" ? (asc ? " ▲" : " ▼") : " ⇅"}
                  </span>
                </button>
              </th>
              <th scope="col">四半期</th>
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
                <td className="mono">{s.announcement_date}</td>
                <td>{s.quarter_type}</td>
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
                {COLUMNS.map((c) => (
                  <td key={c.key} className="num mono">
                    {c.format(s[c.key])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="results__legend">
        「営業利益（直近実績）」「ROE」「EPS（直近実績）」はいずれも直近の
        有価証券報告書に基づく実績値であり、業績予想の修正は反映していません。
        並び順は表示上のものであり、銘柄の優劣を示すものではありません。
      </p>
    </section>
  );
}
