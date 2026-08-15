// Google AdSense の adsbygoogle.js が使うグローバル変数の最小限の型宣言。

export {};

declare global {
  interface Window {
    adsbygoogle?: Record<string, unknown>[];
  }
}
