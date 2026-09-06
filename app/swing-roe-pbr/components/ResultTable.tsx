"use client";

import { useMemo, useState } from "react";
import type { Swing2Stock } from "@/lib/types";
import { tradingViewUrl } from "@/lib/tradingview";

type SortKey = keyof Pick<
  Swing2Stock,
  "market_cap" | "lower_deviation_pct" | "adjusted_roe_pct" | "per" | "equity_ratio_pct"
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

const TECHNICAL_LABEL: Record<string, string> = {
  goldenCross: "ゴールデンクロス",
  ma25Reversal: "25日線の反転",
  volumeSpike: "出来高急増",
};

const COLUMNS: { key: SortKey; label: string; format: (v: number | null) => string }[] = [
  { key: "market_cap", label: "時価総額", format: fmtOku },
  { key: "lower_deviation_pct", label: "理論PBRとの下方乖離", format: (v) => fmt(v, 1) + (v === null ? "" : "%") },
  { key: "adjusted_roe_pct", label: "調整後ROE", format: (v) => fmt(v, 1) + (v === null ? "" : "%") },
  { key: "per", label: "PER", format: (v) => fmt(v) + (v === null ? "" : "倍") },
  { key: "equity_ratio_pct", label: "自己資本比率", format: (v) => fmt(v, 1) + (v === null ? "" : "%") },
];

const ALL = "すべて";

export default function ResultTable({ stocks }: { stocks: Swing2Stock[] }) {
  const [sortKey, setSortKey] = useState<SortKey>("lower_deviation_pct");
  const [asc, setAsc] = useState(false);
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
              <th scope="col" className="num">株価</th>
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
              <th scope="col">テクニカル条件</th>
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
                <td>{s.technical_signal ? TECHNICAL_LABEL[s.technical_signal] : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="results__legend">
        「理論PBRとの下方乖離」は、実績PBRが理論PBR（調整後ROE×業種平均PER）に対して
        どれだけ低い水準にあるかを示す参考値です。「調整後ROE」は特別損益を除いた
        経常利益ベースの実績値です。並び順は表示上のものであり、銘柄の優劣を
        示すものではありません。
      </p>
    </section>
  );
}
