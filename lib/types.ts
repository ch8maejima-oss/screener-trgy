/**
 * app/dividend/data/latest.json（集計値・公開）と private-data/dividend/stocks.json
 * （銘柄配列・EA EXPO購入者限定でゲート配信）の型。build_site_data.py の出力と対応する。
 */

export type Stock = {
  sec_code: string;
  name: string;
  market: string;
  sector33: string;
  period_end: string | null;
  scope: string | null;
  price: number | null;
  market_cap: number | null;
  avg_volume_3m: number | null;
  dividend_ttm: number | null;
  dividend_yield_pct: number | null;
  roe_pct: number | null;
  equity_ratio_pct: number | null;
  current_ratio_pct: number | null;
  revenue_change_pct: number | null;
  operating_margin_pct: number | null;
  dps_yuho: number | null;
  dps_diff_pct: number | null;
};

export type ConditionKey =
  | "c1_dividend"
  | "c2_roe"
  | "c3_equity_ratio"
  | "c4_current_ratio"
  | "c5_revenue"
  | "c6_op_margin";

export type ScreeningData = {
  as_of: string;
  universe_label: string;
  counts: {
    population: number;
    passed: number;
    failed: number;
    not_evaluable: number;
  };
  per_condition_passed: Record<ConditionKey, number>;
  per_condition_missing: Record<ConditionKey, number>;
  thresholds: Record<string, number>;
};

/** 画面表示用の条件定義。閾値は latest.json の thresholds と一致させること。 */
export const CONDITIONS: {
  key: ConditionKey;
  no: number;
  label: string;
  rule: string;
  source: string;
}[] = [
  {
    key: "c1_dividend",
    no: 1,
    label: "配当利回り",
    rule: "3.5% 以上",
    source: "直近12か月の実績配当合計（株式分割調整済み）÷ 直近終値",
  },
  {
    key: "c2_roe",
    no: 2,
    label: "ROE（自己資本利益率）",
    rule: "10% 以上",
    source: "有価証券報告書【主要な経営指標等の推移】の開示値",
  },
  {
    key: "c3_equity_ratio",
    no: 3,
    label: "自己資本比率",
    rule: "50% 以上",
    source: "有価証券報告書【主要な経営指標等の推移】の開示値",
  },
  {
    key: "c4_current_ratio",
    no: 4,
    label: "流動比率",
    rule: "200% 以上",
    source: "貸借対照表の流動資産 ÷ 流動負債",
  },
  {
    key: "c5_revenue",
    no: 5,
    label: "売上高",
    rule: "直近5期（4年間）で減収していないこと",
    source: "有価証券報告書【主要な経営指標等の推移】の売上高5期分",
  },
  {
    key: "c6_op_margin",
    no: 6,
    label: "売上高営業利益率",
    rule: "10% 以上",
    source: "損益計算書の営業利益 ÷ 上記売上高（直近期）",
  },
];
