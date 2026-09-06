import type { Metadata } from "next";
import data from "./data/latest.json";
import type { Swing2ScreeningData, Swing2Stock } from "@/lib/types";
import { DisclaimerBanner, DisclaimerFull } from "./components/Disclaimer";
import Methodology from "./components/Methodology";
import Coverage from "./components/Coverage";
import ResultTable from "./components/ResultTable";
import AdSenseUnit from "../components/AdSenseUnit";

export const metadata: Metadata = {
  title: "スイング用スクリーニング② ROE・PBR整合性チェッカー | スクリーニング銘柄一覧",
  description:
    "PBR＝ROE×PERの関係式から理論PBRを算出し、実績PBRとの下方乖離・ROEの質・安全性・テクニカル条件を機械的に適用した結果を表示します。株式会社トリロジー（近畿財務局長（金商）第372号）。",
};

type Swing2Data = Swing2ScreeningData & { stocks: Swing2Stock[] };
const screening = data as unknown as Swing2Data;

const ADSENSE_CLIENT_ID = process.env.NEXT_PUBLIC_ADSENSE_CLIENT_ID;
const ADSENSE_AD_SLOT = process.env.NEXT_PUBLIC_ADSENSE_AD_SLOT;
const ADSENSE_ENABLED = Boolean(ADSENSE_CLIENT_ID && ADSENSE_AD_SLOT);

export default function Home() {
  return (
    <div className="home">
      <section className="intro">
        <h1>スイング用スクリーニング② ROE・PBR整合性チェッカー</h1>
        <p className="intro__asof">
          基準日 <time dateTime={screening.as_of}>{screening.as_of}</time>
          <span className="intro__universe">{screening.universe_label}</span>
        </p>
        <p className="intro__lead">
          PBR＝ROE×PERという会計上の関係式から算出した「理論PBR」と、実際のPBRとの
          歪みを機械的に検知するスクリーニングです。理論PBRとの下方乖離・ROEの質・
          安全性・テクニカル条件の4条件をすべて満たした
          {screening.counts.listed.toLocaleString()}銘柄を掲載しています。
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
          <li>財務数値：金融庁 EDINET に提出された有価証券報告書（XBRL）</li>
          <li>対象銘柄：日本取引所グループ「東証上場銘柄一覧」</li>
          <li>株価・出来高・テクニカル指標：外部market data提供元</li>
        </ul>
      </section>

      {ADSENSE_ENABLED && (
        <div className="ad-slot">
          <span className="ad-slot__label">広告（第三者配信）</span>
          <AdSenseUnit client={ADSENSE_CLIENT_ID!} slot={ADSENSE_AD_SLOT!} />
        </div>
      )}

      <p className="equity-sim__notice-inline">
        本条件を機械的な売買ルールで仮想売買した場合の
        <a href="/swing-roe-pbr-simulation/" className="hero__method-link">
          フォワードシミュレーション
        </a>
        も別途公開しています。
      </p>

      <DisclaimerFull />
    </div>
  );
}
