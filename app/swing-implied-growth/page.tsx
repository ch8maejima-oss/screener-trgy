import type { Metadata } from "next";
import data from "./data/latest.json";
import type { Swing1ScreeningData, Swing1Stock } from "@/lib/types";
import { DisclaimerBanner, DisclaimerFull } from "./components/Disclaimer";
import Methodology from "./components/Methodology";
import Coverage from "./components/Coverage";
import ResultTable from "./components/ResultTable";
import AdSenseUnit from "../components/AdSenseUnit";

export const metadata: Metadata = {
  title: "スイング用スクリーニング① 期待リターン逆算 | スクリーニング銘柄一覧",
  description:
    "現在の株価から、2段階DCFモデルで市場が織り込んでいるFCF成長率を逆算し、東証プライム市場の全銘柄について一覧表示します。株式会社トリロジー（近畿財務局長（金商）第372号）。",
};

type Swing1Data = Swing1ScreeningData & { stocks: Swing1Stock[] };
const screening = data as unknown as Swing1Data;

const ADSENSE_CLIENT_ID = process.env.NEXT_PUBLIC_ADSENSE_CLIENT_ID;
const ADSENSE_AD_SLOT = process.env.NEXT_PUBLIC_ADSENSE_AD_SLOT;
const ADSENSE_ENABLED = Boolean(ADSENSE_CLIENT_ID && ADSENSE_AD_SLOT);

export default function Home() {
  return (
    <div className="home">
      <section className="intro">
        <h1>スイング用スクリーニング① 期待リターン逆算</h1>
        <p className="intro__asof">
          基準日 <time dateTime={screening.as_of}>{screening.as_of}</time>
          <span className="intro__universe">{screening.universe_label}</span>
        </p>
        <p className="intro__lead">
          現在の株価は、将来のフリーキャッシュフロー（FCF）成長についての市場の期待を
          織り込んでいます。本ページは、対象市場の全{screening.counts.population.toLocaleString()}
          銘柄について、現在の企業価値（時価総額＋有利子負債－現金同等物）と整合するために
          必要なFCF成長率を2段階DCFモデルで逆算し、
          {screening.counts.listed.toLocaleString()}銘柄を一覧掲載しています。
          買い候補・空売り候補を判定するものではなく、市場の期待値を可視化する参考情報です。
        </p>
      </section>

      <DisclaimerBanner />

      {ADSENSE_ENABLED && (
        <div className="ad-slot">
          <span className="ad-slot__label">広告（第三者配信）</span>
          <AdSenseUnit client={ADSENSE_CLIENT_ID!} slot={ADSENSE_AD_SLOT!} />
        </div>
      )}

      <Methodology data={screening} />
      <ResultTable stocks={screening.stocks} />

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
          <li>
            財務数値：金融庁 EDINET に提出された有価証券報告書（XBRL）
          </li>
          <li>
            対象銘柄：日本取引所グループ「東証上場銘柄一覧」
          </li>
          <li>株価・β算出用の株価履歴：外部market data提供元</li>
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
