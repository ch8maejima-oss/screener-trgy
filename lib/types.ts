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

/**
 * テンバガー候補スクリーニング（build_tenbagger_site_data.py の出力と対応）。
 * app/dividend 用の型とは対象銘柄・条件が異なるため独立させている。
 */
export type TenbaggerStock = {
  sec_code: string;
  name: string;
  market: string;
  sector33: string;
  period_end: string | null;
  scope: string | null;
  result: "全条件充足" | "8/9条件充足";
  /** 「8/9条件充足」の銘柄について、満たしていない条件のラベル（通常1件）。全条件充足なら空配列。 */
  unmet_conditions: string[];
  price: number | null;
  market_cap: number | null;
  avg_volume_3m: number | null;
  revenue_cagr_pct: number | null;
  profit_cagr_pct: number | null;
  profit_turnaround: boolean;
  equity_ratio_pct: number | null;
  listing_years: number | null;
  pbr: number | null;
  sector_avg_pbr: number | null;
  shares_growth_pct: number | null;
};

export type TenbaggerConditionKey =
  | "c1_market_cap"
  | "c2_revenue_growth"
  | "c3_profit_growth"
  | "c4_equity_ratio"
  | "c5_listing_years"
  | "c6_price"
  | "c7_volume"
  | "c8_pbr"
  | "c9_no_dilution";

export type TenbaggerScreeningData = {
  as_of: string;
  universe_label: string;
  counts: {
    population: number;
    /** 9条件すべて充足 */
    full_match: number;
    /** 9条件中8条件充足（未達1条件） */
    near_match: number;
    /** full_match + near_match（掲載件数） */
    passed: number;
    failed: number;
    not_evaluable: number;
  };
  per_condition_passed: Record<TenbaggerConditionKey, number>;
  per_condition_missing: Record<TenbaggerConditionKey, number>;
  thresholds: Record<string, number>;
};

export const CONDITIONS_TENBAGGER: {
  key: TenbaggerConditionKey;
  no: number;
  label: string;
  rule: string;
  source: string;
}[] = [
  {
    key: "c1_market_cap",
    no: 1,
    label: "時価総額",
    rule: "100億円以下",
    source: "直近終値 × 発行済株式数",
  },
  {
    key: "c2_revenue_growth",
    no: 2,
    label: "売上高成長率",
    rule: "5期（4年間）の年平均成長率 15%以上",
    source: "有価証券報告書【主要な経営指標等の推移】の売上高5期分から算出",
  },
  {
    key: "c3_profit_growth",
    no: 3,
    label: "経常利益成長率",
    rule: "5期（4年間）の年平均成長率 15%以上（5期前が赤字からの黒字転換は合格扱い）",
    source: "有価証券報告書【主要な経営指標等の推移】の経常利益5期分から算出",
  },
  {
    key: "c4_equity_ratio",
    no: 4,
    label: "自己資本比率",
    rule: "50%以上",
    source: "有価証券報告書【主要な経営指標等の推移】の開示値",
  },
  {
    key: "c5_listing_years",
    no: 5,
    label: "上場からの年数",
    rule: "8年以内",
    source: "株価データが遡れる最古の月（上場月の近似値）から算出",
  },
  {
    key: "c6_price",
    no: 6,
    label: "株価",
    rule: "600円以下",
    source: "直近終値",
  },
  {
    key: "c7_volume",
    no: 7,
    label: "出来高（流動性）",
    rule: "3ヶ月平均出来高が1日あたり3万株以上",
    source: "直近3ヶ月間の日次出来高の平均値",
  },
  {
    key: "c8_pbr",
    no: 8,
    label: "PBR",
    rule: "同一業種（33業種区分）平均以下",
    source: "時価総額 ÷ 純資産（有価証券報告書開示値）。業種平均は対象ユニバース内で算出",
  },
  {
    key: "c9_no_dilution",
    no: 9,
    label: "増資の有無",
    rule: "発行済株式数が前期比20%を超えて増加していないこと",
    source: "有価証券報告書【主要な経営指標等の推移】の発行済株式数（当期・前期）",
  },
];

/**
 * スイング用スクリーニング①「期待リターン逆算」（build_swing1_site_data.py の出力と対応）。
 * 合否判定のスクリーニングではなく、現在の株価から2段階DCFで逆算した
 * 市場織込みFCF成長率を一覧表示する（ソートは表示上の操作）。
 */
export type Swing1Stock = {
  sec_code: string;
  name: string;
  market: string;
  sector33: string;
  period_end: string | null;
  scope: string | null;
  price: number | null;
  market_cap: number | null;
  beta: number | null;
  cost_of_equity_pct: number | null;
  interest_bearing_debt: number | null;
  cost_of_debt_after_tax_pct: number | null;
  wacc_pct: number | null;
  fcf0: number | null;
  ev: number | null;
  implied_growth_pct: number | null;
  operating_income: number | null;
  projected_operating_income_10y: number | null;
};

export type Swing1ScreeningData = {
  as_of: string;
  universe_label: string;
  counts: {
    population: number;
    listed: number;
    not_evaluable: number;
  };
  exclusion_reasons: Record<string, number>;
  assumptions: {
    risk_free_rate_pct: number;
    equity_risk_premium_pct: number;
    tax_rate_pct: number;
    terminal_growth_pct: number;
    forecast_years: number;
  };
};

/**
 * デイトレード用スクリーニング②「決算発表カレンダー」（build_daytrade2_site_data.py の出力と対応）。
 * 合否判定ではなく、貸借銘柄を決算発表予定日が近い順に一覧表示する。
 */
export type EarningsCalendarStock = {
  announcement_date: string;
  sec_code: string;
  name: string;
  market: string;
  sector33: string;
  quarter_type: string;
  fiscal_year_end: string | null;
  period_end: string | null;
  operating_income: number | null;
  roe_pct: number | null;
  eps: number | null;
};

export type EarningsCalendarData = {
  as_of: string;
  universe_label: string;
  counts: {
    calendar_total: number;
    listed: number;
    not_evaluable: number;
  };
  date_range: { 開始: string | null; 終了: string | null };
};

/**
 * デイトレード用スクリーニング①（上昇モメンタム）のフォワードシミュレーション
 * （daytrade_sim.py の出力・data/daytrade-sim-state.json と対応）。
 */
export type DaytradeSimPosition = {
  id: string;
  code: string;
  name: string;
  sector: string;
  entryDate: string;
  entryPrice: number;
  targetPrice: number;
  changeOnEntryDay1dPct: number;
  status: "open" | "closed";
  exitDate: string | null;
  exitPrice: number | null;
  exitReason: "target" | "stopLoss" | "maxHold" | null;
  returnPct: number | null;
};

export type EquitySimCurvePoint = {
  date: string;
  avgReturnPct: number;
  openCount: number;
  closedCount: number;
  winCount: number;
  lossCount: number;
};

export type PricePoint = { date: string; price: number };

export type DaytradeSimState = {
  startDate: string;
  lastUpdated: string;
  positions: DaytradeSimPosition[];
  equityCurve: EquitySimCurvePoint[];
  nikkei: PricePoint[];
  topix: PricePoint[];
};

/**
 * スイング用スクリーニング②「ROE・PBR整合性チェッカー」
 * （screen_swing2.py の出力・output/swing2_buy_*.csv と対応）。
 */
export type Swing2Stock = {
  sec_code: string;
  name: string;
  market: string;
  sector33: string;
  period_end: string | null;
  scope: string | null;
  price: number | null;
  market_cap: number | null;
  avg_volume_3m: number | null;
  pbr: number | null;
  theoretical_pbr: number | null;
  lower_deviation_pct: number | null;
  adjusted_roe_pct: number | null;
  per: number | null;
  sector_avg_per: number | null;
  equity_ratio_pct: number | null;
  technical_signal: "goldenCross" | "ma25Reversal" | "volumeSpike" | null;
};

export type Swing2ScreeningData = {
  as_of: string;
  universe_label: string;
  counts: {
    population: number;
    size_liquidity_passed: number;
    listed: number;
    not_evaluable: number;
  };
  per_condition_passed: Record<string, number>;
  per_condition_missing: Record<string, number>;
  thresholds: Record<string, number>;
};

/**
 * スイング②のフォワードシミュレーション（swing2_sim.py の出力・
 * data/swing2-sim-state.json と対応）。部分決済（半分利確）に対応するため
 * daytrade_sim.pyのPositionより項目が多い。
 */
export type Swing2SimPosition = {
  id: string;
  code: string;
  name: string;
  sector: string;
  entryDate: string;
  entryPrice: number;
  entryPbr: number;
  theoreticalPbr: number;
  lowerDeviationPctAtEntry: number;
  status: "open" | "closed";
  partialExitDate: string | null;
  partialExitPrice: number | null;
  partialExitReason: "deviationNarrowed" | "technical" | null;
  exitDate: string | null;
  exitPrice: number | null;
  exitReason: "target" | "stopLoss" | "maxHold" | null;
  returnPct: number | null;
};

export type Swing2SimState = {
  startDate: string;
  lastUpdated: string;
  positions: Swing2SimPosition[];
  equityCurve: EquitySimCurvePoint[];
};

/**
 * テンバガー候補のフォワードシミュレーション（tenbagger_sim.py の出力・
 * data/tenbagger-sim-state.json と対応）。3倍で1/3・6倍で1/3・10倍で残り全量という
 * 2段階の部分利確に対応するため、Swing2SimPositionより項目が多い。
 */
export type TenbaggerSimPosition = {
  id: string;
  code: string;
  name: string;
  sector: string;
  entryDate: string;
  entryPrice: number;
  status: "open" | "closed";
  partial1ExitDate: string | null;
  partial1ExitPrice: number | null;
  partial2ExitDate: string | null;
  partial2ExitPrice: number | null;
  exitDate: string | null;
  exitPrice: number | null;
  exitReason: "target" | "stopLoss" | "maxHold" | null;
  returnPct: number | null;
};

export type TenbaggerSimState = {
  startDate: string;
  lastUpdated: string;
  positions: TenbaggerSimPosition[];
  equityCurve: EquitySimCurvePoint[];
};
