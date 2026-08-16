// TradingViewのチャートへのディープリンク。東証銘柄は "TSE:<コード>" 形式。
export function tradingViewUrl(code: string): string {
  return `https://www.tradingview.com/chart/?symbol=TSE%3A${encodeURIComponent(code)}`;
}
