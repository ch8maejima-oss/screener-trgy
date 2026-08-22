"use client";

import { useMemo, useState } from "react";
import type { TenbaggerStock } from "@/lib/types";
import { tradingViewUrl } from "@/lib/tradingview";

type SortKey = keyof Pick<
  TenbaggerStock,
  | "sec_code"
  | "market_cap"
  | "avg_volume_3m"
  | "revenue_cagr_pct"
  | "profit_cagr_pct"
  | "equity_ratio_pct"
  | "listing_years"
  | "pbr"
  | "shares_growth_pct"
>;

function fmt(v: number | null, digits = 2) {
  return v === null ? "—" : v.toLocaleString("ja-JP", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}
function fmtOku(v: number | null) {
  return v === null
    ? "—"
    : `${(v / 1e8).toLocaleString("ja-JP", { minimumFractionDigits: 1, maximumFractionDigits: 1 })}億円`;
}
function fmtShares(v: number | null) {
  return v === null ? "—" : `${Math.round(v).toLocaleString("ja-JP")}株`;
}
function fmtYears(v: number | null) {
  return v === null ? "—" : `${fmt(v, 1)}年`;
}

const COLUMNS: { key: SortKey; label: string; format: (v: number | null) => string }[] = [
  { key: "market_cap", label: "時価総額", format: fmtOku },
  { key: "revenue_cagr_pct", label: "売上高成長率(年平均)", format: (v) => fmt(v, 1) + (v === null ? "" : "%") },
  { key: "profit_cagr_pct", label: "経常利益成長率(年平均)", format: (v) => fmt(v, 1) + (v === null ? "" : "%") },
  { key: "equity_ratio_pct", label: "自己資本比率", format: (v) => fmt(v) + (v === null ? "" : "%") },
  { key: "listing_years", label: "上場からの年数", format: fmtYears },
  { key: "avg_volume_3m", label: "平均出来高（3ヶ月）", format: fmtShares },
  { key: "pbr", label: "PBR", format: (v) => fmt(v) + (v === null ? "" : "倍") },
];

const ALL = "すべて";

export default function ResultTable({ stocks }: { stocks: TenbaggerStock[] }) {
  const [sortKey, setSortKey] = useState<SortKey>("market_cap");
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
              <th scope="col">判定</th>
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
                <td className="results__match">
                  {s.result === "全条件充足" ? (
                    <span className="results__badge results__badge--full">9/9条件充足</span>
                  ) : (
                    <span
                      className="results__badge results__badge--near"
                      title={`未達: ${s.unmet_conditions.join("、")}`}
                    >
                      8/9条件充足（{s.unmet_conditions.join("、")}が未達）
                    </span>
                  )}
                </td>
                <td className="num mono">{fmt(s.price, 1)}</td>
                {COLUMNS.map((c) => (
                  <td key={c.key} className="num mono">
                    {c.key === "profit_cagr_pct" && s.profit_turnaround
                      ? "黒字転換"
                      : c.format(s[c.key] as number | null)}
                  </td>
                ))}
                <td className="results__period">{s.period_end ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="results__legend">
        「売上高成長率」「経常利益成長率」は【主要な経営指標等の推移】5期分のうち最も古い期から
        直近期までの年平均成長率（CAGR）です。「経常利益成長率」欄の「黒字転換」は、5期前が
        赤字（0以下）で直近期が黒字だった銘柄を示します。「上場からの年数」は株価データが
        遡れる最古の月を近似値として算出しています。「平均出来高（3ヶ月）」は基準日時点から
        直近3ヶ月間の日次出来高の平均値です。並び順は表示上のものであり、銘柄の優劣を
        示すものではありません。
      </p>
    </section>
  );
}
