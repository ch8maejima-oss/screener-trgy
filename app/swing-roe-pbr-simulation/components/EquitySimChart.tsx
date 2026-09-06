"use client";

import { useState } from "react";
import type { EquitySimCurvePoint } from "@/lib/types";

interface Props {
  curve: EquitySimCurvePoint[];
}

const WIDTH = 800;
const HEIGHT = 320;
const PAD_LEFT = 56;
const PAD_RIGHT = 16;
const PAD_TOP = 20;
const PAD_BOTTOM = 32;

const STRATEGY_COLOR = "var(--navy-light)";

export default function EquitySimChart({ curve }: Props) {
  const [hoverIdx, setHoverIdx] = useState<number | null>(null);

  if (curve.length === 0) {
    return <p className="equity-sim__empty">まだデータがありません。</p>;
  }

  const strategyValues = curve.map((c) => c.avgReturnPct);
  const maxAbs = Math.max(1, ...strategyValues.map((v) => Math.abs(v)));
  const yMax = maxAbs * 1.15;
  const yMin = -yMax;

  const plotW = WIDTH - PAD_LEFT - PAD_RIGHT;
  const plotH = HEIGHT - PAD_TOP - PAD_BOTTOM;

  const xAt = (i: number) =>
    curve.length === 1 ? PAD_LEFT + plotW / 2 : PAD_LEFT + (plotW * i) / (curve.length - 1);
  const yAt = (v: number) => PAD_TOP + plotH * (1 - (v - yMin) / (yMax - yMin));

  const strategyPoints = strategyValues.map((v, i) => `${xAt(i)},${yAt(v)}`).join(" ");
  const zeroY = yAt(0);

  const hoverStrategy = hoverIdx !== null ? strategyValues[hoverIdx] : null;
  const hoverCurve = hoverIdx !== null ? curve[hoverIdx] : null;

  function handleMove(e: React.MouseEvent<SVGSVGElement>) {
    const rect = e.currentTarget.getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width) * WIDTH;
    const ratio = curve.length === 1 ? 0 : (x - PAD_LEFT) / plotW;
    const idx = Math.round(ratio * (curve.length - 1));
    setHoverIdx(Math.min(curve.length - 1, Math.max(0, idx)));
  }

  function fmt(v: number | null): string {
    if (v === null) return "—";
    return `${v >= 0 ? "+" : ""}${v.toFixed(2)}%`;
  }

  return (
    <div className="equity-sim__chart-wrap">
      <div className="equity-sim__chart-legend">
        <span className="equity-sim__legend-item">
          <i style={{ background: STRATEGY_COLOR }} />
          本シミュレーション（保有中の含み損益＋決済済みの確定損益、部分決済含む）
        </span>
      </div>
      <svg
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        className="equity-sim__chart"
        onMouseMove={handleMove}
        onMouseLeave={() => setHoverIdx(null)}
        role="img"
        aria-label="スイング用スクリーニング②フォワードシミュレーションの累積平均リターン推移"
      >
        {[yMin, yMin / 2, 0, yMax / 2, yMax].map((v) => (
          <g key={v}>
            <line
              x1={PAD_LEFT}
              x2={WIDTH - PAD_RIGHT}
              y1={yAt(v)}
              y2={yAt(v)}
              className="equity-sim__gridline"
            />
            <text x={PAD_LEFT - 8} y={yAt(v)} className="equity-sim__axis-label" textAnchor="end" dy="0.32em">
              {v.toFixed(0)}%
            </text>
          </g>
        ))}
        <line x1={PAD_LEFT} x2={WIDTH - PAD_RIGHT} y1={zeroY} y2={zeroY} className="equity-sim__zeroline" />

        <polyline points={strategyPoints} fill="none" stroke={STRATEGY_COLOR} strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round" />

        {hoverIdx !== null && (
          <>
            <line
              x1={xAt(hoverIdx)}
              x2={xAt(hoverIdx)}
              y1={PAD_TOP}
              y2={HEIGHT - PAD_BOTTOM}
              className="equity-sim__crosshair"
            />
            {hoverStrategy !== null && <circle cx={xAt(hoverIdx)} cy={yAt(hoverStrategy)} r={4} fill={STRATEGY_COLOR} />}
          </>
        )}

        <text x={PAD_LEFT} y={HEIGHT - 8} className="equity-sim__axis-label" textAnchor="start">
          {curve[0].date}
        </text>
        <text x={WIDTH - PAD_RIGHT} y={HEIGHT - 8} className="equity-sim__axis-label" textAnchor="end">
          {curve[curve.length - 1].date}
        </text>
      </svg>

      {hoverCurve && (
        <div className="equity-sim__tooltip">
          <strong>{hoverCurve.date}</strong>
          <span>本シミュレーション: {fmt(hoverStrategy)}</span>
          <span>
            保有中 {hoverCurve.openCount} / 決済済み {hoverCurve.closedCount}（勝ち{" "}
            {hoverCurve.winCount}・負け {hoverCurve.lossCount}）
          </span>
        </div>
      )}
    </div>
  );
}
