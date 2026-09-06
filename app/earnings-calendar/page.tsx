import type { Metadata } from "next";
import data from "./data/latest.json";
import type { EarningsCalendarData, EarningsCalendarStock } from "@/lib/types";
import { DisclaimerBanner, DisclaimerFull } from "./components/Disclaimer";
import Coverage from "./components/Coverage";
import CalendarTable from "./components/CalendarTable";
import AdSenseUnit from "../components/AdSenseUnit";

export const metadata: Metadata = {
  title: "デイトレード用スクリーニング② 決算発表カレンダー | スクリーニング銘柄一覧",
  description:
    "貸借銘柄について、今後の決算発表予定日と直近の営業利益・ROE・EPSを一覧表示します。株式会社トリロジー（近畿財務局長（金商）第372号）。",
};

type CalendarData = EarningsCalendarData & { stocks: EarningsCalendarStock[] };
const screening = data as unknown as CalendarData;

const ADSENSE_CLIENT_ID = process.env.NEXT_PUBLIC_ADSENSE_CLIENT_ID;
const ADSENSE_AD_SLOT = process.env.NEXT_PUBLIC_ADSENSE_AD_SLOT;
const ADSENSE_ENABLED = Boolean(ADSENSE_CLIENT_ID && ADSENSE_AD_SLOT);

export default function Home() {
  return (
    <div className="home">
      <section className="intro">
        <h1>デイトレード用スクリーニング② 決算発表カレンダー</h1>
        <p className="intro__asof">
          基準日 <time dateTime={screening.as_of}>{screening.as_of}</time>
          <span className="intro__universe">{screening.universe_label}</span>
        </p>
        <p className="intro__lead">
          貸借銘柄について、今後の決算発表予定日が近い順に、直近の有価証券報告書に
          基づく営業利益・ROE・EPSを一覧表示しています。「決算またぎ」でポジションを
          持つかどうかを判断する際の参考情報としてご利用ください。
        </p>
        <p className="intro__lead">
          業績予想の修正（上方修正・下方修正）を反映した分析は準備中です。
          現時点では決算発表予定日と直近実績の一覧のみを掲載しています。
        </p>
      </section>

      <DisclaimerBanner />

      {ADSENSE_ENABLED && (
        <div className="ad-slot">
          <span className="ad-slot__label">広告（第三者配信）</span>
          <AdSenseUnit client={ADSENSE_CLIENT_ID!} slot={ADSENSE_AD_SLOT!} />
        </div>
      )}

      <CalendarTable stocks={screening.stocks} />

      {ADSENSE_ENABLED && (
        <div className="ad-slot">
          <span className="ad-slot__label">広告（第三者配信）</span>
          <p className="ad-slot__note">
            以下は第三者配信の広告であり、上記の銘柄一覧や当社の見解とは一切関係ございません。
          </p>
          <AdSenseUnit client={ADSENSE_CLIENT_ID!} slot={ADSENSE_AD_SLOT!} />
        </div>
      )}

      <Coverage data={screening} />

      <section className="sources" aria-label="データの出所">
        <h2>データの出所</h2>
        <ul>
          <li>決算発表予定日：日本取引所グループ「決算発表予定日」公開情報</li>
          <li>貸借銘柄：日本取引所グループ「制度信用・貸借選定銘柄一覧」</li>
          <li>
            財務数値：金融庁 EDINET に提出された有価証券報告書（XBRL）
          </li>
        </ul>
      </section>

      {ADSENSE_ENABLED && (
        <div className="ad-slot">
          <span className="ad-slot__label">広告（第三者配信）</span>
          <AdSenseUnit client={ADSENSE_CLIENT_ID!} slot={ADSENSE_AD_SLOT!} />
        </div>
      )}

      <DisclaimerFull />
    </div>
  );
}
