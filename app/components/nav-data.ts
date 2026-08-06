/**
 * ヘッダーのプルダウンメニュー定義。
 * 出典: www.trgy.co.jp のグローバルナビゲーション（2026-08-06時点）。
 * メニュー項目名・リンク先は同一のものを移植し、デザインのみ本サイト向けに調整している。
 */
export type NavItem = {
  label: string;
  href: string;
  children?: NavItem[];
};

export const navItems: NavItem[] = [
  {
    label: "Home",
    href: "https://www.trgy.co.jp",
  },
  {
    label: "Service",
    href: "https://www.trgy.co.jp/service/",
    children: [
      {
        label: "法人会員",
        href: "https://ea-exposition.com/category/item/corporate",
        children: [
          { label: "法人向け資産運用支援", href: "https://mae.trgy.co.jp/" },
          { label: "Webサイト導入支援", href: "https://ea-exposition.com/web-site_55" },
          { label: "不動産会社向けWeb導入支援LP", href: "https://lp.trgy.co.jp/real-estate/" },
          { label: "AI導入支援", href: "https://ea-exposition.com/ai-introduction-4" },
          { label: "AI導入支援LP", href: "https://ai.trgy.co.jp/" },
        ],
      },
      {
        label: "一般会員",
        href: "https://ea-exposition.com/category/item/lesson",
        children: [
          { label: "トライアル", href: "https://ea-exposition.com/investment-advisor-001" },
          { label: "ライト", href: "https://ea-exposition.com/investment-advisor-002" },
          { label: "スタンダード（個人）", href: "https://ea-exposition.com/investment-advisor-003" },
          { label: "スタンダード（法人）", href: "https://ea-exposition.com/investment-advisor-004" },
        ],
      },
      { label: "売買シグナル配信会員", href: "https://best-amma.jp/?tag=185238&tag2=185238tag3" },
      { label: "自動売買ソフト会員", href: "https://ea-exposition.com/category/item/ea-mt4-mt5" },
    ],
  },
  {
    label: "Tools",
    href: "https://www.trgy.co.jp/tools/",
    children: [
      {
        label: "Blog",
        href: "https://www.trgy.co.jp/blog/",
        children: [
          { label: "Headlines News", href: "https://www.trgy.co.jp/category/headlines/" },
          { label: "外国為替（FX）", href: "https://www.trgy.co.jp/category/fx/" },
          { label: "株式投資", href: "https://www.trgy.co.jp/category/stocks/" },
          { label: "投資信託・ETF", href: "https://www.trgy.co.jp/category/fund/" },
          { label: "先物・CFD・債権", href: "https://www.trgy.co.jp/category/futures/" },
          { label: "暗号資産（仮想通貨）", href: "https://www.trgy.co.jp/category/crypto/" },
          { label: "不動産・REIT", href: "https://www.trgy.co.jp/category/realestate/" },
          { label: "オプション", href: "https://www.trgy.co.jp/category/option/" },
          { label: "コラム", href: "https://www.trgy.co.jp/category/%e3%82%b3%e3%83%a9%e3%83%a0/" },
        ],
      },
      { label: "公式LINEアカウント", href: "https://lin.ee/ZQvBsgD" },
      {
        label: "LINEオープンチャット",
        href: "https://line.me/ti/g2/mp8G8QqV5DogLwHLFfUWfTOMhDdXWD3HDQtHiQ?utm_source=invitation&utm_medium=link_copy&utm_campaign=default",
      },
      { label: "交流会・セミナー", href: "https://ea-exposition.com/media/osaka-investor-party/" },
      {
        label: "facebook",
        href: "https://www.facebook.com/p/%E6%A0%AA%E5%BC%8F%E4%BC%9A%E7%A4%BE%E3%83%88%E3%83%AA%E3%83%AD%E3%82%B8%E3%83%BC-100063767089332/",
      },
      { label: "note", href: "https://note.com/trilogy" },
      { label: "Discord", href: "https://discord.gg/pw9zXcc" },
      {
        label: "レベル診断",
        href: "#",
        children: [
          { label: "投資家経験値レベル診断ツール", href: "https://www.trgy.co.jp/judgement/" },
          { label: "FXトレーダー経験値レベル診断ツール", href: "https://www.trgy.co.jp/judgement2/" },
        ],
      },
      { label: "メールマガジン", href: "https://www.trgy.co.jp/tools/mailmag/" },
      { label: "Youtube", href: "https://www.youtube.com/feed/subscriptions/UCZAQ_tImZSzRquCqHV9EiBg" },
    ],
  },
  {
    label: "Contact",
    href: "https://www.trgy.co.jp/contact/",
    children: [
      { label: "プライバシーポリシー", href: "https://www.trgy.co.jp/about-us/privatepolicy/" },
      { label: "特定商取引法に基づく表記", href: "https://www.trgy.co.jp/about-us/law/" },
      { label: "コンプライアンス", href: "https://www.trgy.co.jp/about-us/compliance/" },
      { label: "免責事項", href: "https://www.trgy.co.jp/about-us/particular/" },
      { label: "使用条件", href: "https://www.trgy.co.jp/about-us/conditions/" },
    ],
  },
  {
    label: "About-us",
    href: "https://www.trgy.co.jp/about-us/",
    children: [
      { label: "会社概要", href: "https://www.trgy.co.jp/about-us/company/" },
      { label: "契約締結前交付書面", href: "https://www.trgy.co.jp/about-us/contact-2/" },
      { label: "契約締結時交付書面", href: "https://www.trgy.co.jp/about-us/contact2/" },
      { label: "お客様本位の業務運営に関する原則・方針", href: "https://www.trgy.co.jp/about-us/fiduciary/" },
      { label: "反社会的勢力との関係遮断に関する基本方針", href: "https://www.trgy.co.jp/about-us/antisocial/" },
    ],
  },
  {
    label: "Link",
    href: "https://www.trgy.co.jp",
    children: [
      { label: "EA EXPO", href: "https://ea-exposition.com/" },
      { label: "FX blog エフログ24", href: "https://kawase.trgy.co.jp" },
      { label: "資産運用スクール [TrilogyONE]", href: "https://school.trgy.co.jp/" },
      { label: "トレ株 ｜ 株式投資情報サイト", href: "https://stock.trgy.co.jp/" },
      { label: "crypto3.0 暗号資産／仮想通貨", href: "https://crypto.trgy.co.jp/" },
      { label: "なりたひろゆきオフィシャル", href: "https://narita.trgy.co.jp/" },
      { label: "FXを学ぶ　〜エフマナ〜", href: "https://fx.trgy.co.jp" },
      { label: "ウィンスクエアクラブ (W2C)", href: "https://w2c.trgy.co.jp/" },
      { label: "投資の相談窓口", href: "https://angc.trgy.co.jp/" },
      { label: "ラクマネ+", href: "https://trgy.co.jp/money/" },
      { label: "MQLメディア", href: "https://finance.trgy.co.jp/" },
      { label: "Markets Guide", href: "https://markets.trgy.co.jp/" },
    ],
  },
];
