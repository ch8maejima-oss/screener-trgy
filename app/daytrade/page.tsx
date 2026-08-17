import type { Metadata } from "next";
import Link from "next/link";
import data from "./data/latest.json";
import type { DaytradeScreeningData } from "@/lib/daytrade-types";
import { DisclaimerBanner, DisclaimerFull } from "./components/Disclaimer";
import Criteria from "./components/Criteria";
import Coverage from "./components/Coverage";
import MomentumTable from "./components/MomentumTable";
import AdSenseUnit from "../components/AdSenseUnit";

export const metadata: Metadata = {
  title: "デイトレード用スクリーニング | スクリーニング銘柄一覧",
  description:
    "貸借銘柄・売買代金・前日/5日/20日騰落率・出来高増加傾向などの条件を、東証プライム市場およびスタンダード市場の貸借銘柄に機械的に適用した結果を表示します。株式会社トリロジー（近畿財務局長（金商）第372号）。",
};

const screening = data as unknown as DaytradeScreeningData;

const ADSENSE_CLIENT_ID = process.env.NEXT_PUBLIC_ADSENSE_CLIENT_ID;
const ADSENSE_AD_SLOT = process.env.NEXT_PUBLIC_ADSENSE_AD_SLOT;
const ADSENSE_ENABLED = Boolean(ADSENSE_CLIENT_ID && ADSENSE_AD_SLOT);

export default function DaytradePage() {
  return (
    <div className="home">
      <section className="intro">
        <h1>デイトレード用スクリーニング</h1>
        <p className="intro__asof">
          基準日 <time dateTime={screening.as_of}>{screening.as_of}</time>
          <span className="intro__universe">{screening.universe_label}（貸借銘柄）</span>
        </p>
        <p className="intro__lead">
          流動性・貸借銘柄・株価水準・出来高の共通条件に加え、上昇/下落モメンタムの
          条件を対象市場の貸借銘柄に機械的に適用し、上昇モメンタム条件通過
          {screening.counts.buy_passed.toLocaleString()}銘柄・下落モメンタム条件通過
          {screening.counts.short_passed.toLocaleString()}銘柄を全件掲載しています。
          当社が有望と判断した銘柄を選び出したものではなく、売買を推奨・勧誘するものでもありません。
        </p>
        <p className="intro__lead">
          <Link href="/daytrade/archive/">過去の判定結果のアーカイブを見る →</Link>
        </p>
      </section>

      <DisclaimerBanner />

      {ADSENSE_ENABLED && (
        <div className="ad-slot">
          <span className="ad-slot__label">広告（第三者配信）</span>
          <AdSenseUnit client={ADSENSE_CLIENT_ID!} slot={ADSENSE_AD_SLOT!} />
        </div>
      )}

      <Criteria data={screening} />
      <MomentumTable stocks={screening.buy.stocks} direction="buy" />
      <MomentumTable stocks={screening.short.stocks} direction="short" />

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
          <li>対象銘柄：日本取引所グループ「東証上場銘柄一覧」</li>
          <li>貸借銘柄：日本取引所グループ「制度信用・貸借選定銘柄一覧」</li>
          <li>株価・出来高・時価総額：外部market data提供元、有価証券報告書の発行済株式数</li>
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
