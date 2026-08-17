/** app/daytrade/data/latest.json の型。build_daytrade_site_data.py の出力と対応する。 */

export type DaytradeStock = {
  sec_code: string;
  name: string;
  market: string;
  sector33: string;
  price: number | null;
  change_1d_pct: number | null;
  change_5d_pct: number | null;
  change_20d_pct: number | null;
  volume: number | null;
  turnover_yen: number | null;
  market_cap: number | null;
  volume_rising: boolean | null;
  is_large_cap: boolean;
};

export type DaytradeScreeningData = {
  as_of: string;
  universe_label: string;
  counts: {
    population: number;
    margin_eligible: number;
    buy_passed: number;
    short_passed: number;
    not_evaluable: number;
  };
  common_thresholds: Record<string, number>;
  buy: {
    thresholds: Record<string, number>;
    stocks: DaytradeStock[];
  };
  short: {
    thresholds: Record<string, number>;
    stocks: DaytradeStock[];
  };
};

/** 画面表示用の条件定義。閾値は latest.json の thresholds と一致させること。 */
export const COMMON_CONDITIONS: { label: string; rule: string; source: string }[] = [
  {
    label: "対象市場",
    rule: "東証プライム・スタンダード",
    source: "JPX「東証上場銘柄一覧」の市場区分",
  },
  {
    label: "信用区分",
    rule: "貸借銘柄（空売り可能）",
    source: "JPX「制度信用・貸借選定銘柄一覧」",
  },
  {
    label: "株価",
    rule: "500円以上",
    source: "直近終値",
  },
  {
    label: "売買代金",
    rule: "50億円以上",
    source: "直近終値 × 直近出来高",
  },
  {
    label: "出来高",
    rule: "増加傾向（直近5日平均 > 直近20日平均）",
    source: "直近の日次出来高",
  },
];

export const BUY_CONDITIONS: { label: string; rule: string }[] = [
  { label: "前日騰落率", rule: "+2% 〜 +10%" },
  { label: "20日騰落率", rule: "+10%以上" },
  { label: "5日騰落率", rule: "+5%以上" },
];

export const SHORT_CONDITIONS: { label: string; rule: string }[] = [
  { label: "前日騰落率", rule: "-10% 〜 -2%" },
  { label: "20日騰落率", rule: "-10%以下" },
  { label: "5日騰落率", rule: "-5%以下" },
];
