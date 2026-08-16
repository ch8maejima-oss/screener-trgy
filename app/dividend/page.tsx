import type { Metadata } from "next";
import data from "./data/latest.json";
import type { ScreeningData } from "@/lib/types";
import { DisclaimerBanner, DisclaimerFull } from "./components/Disclaimer";
import Criteria from "./components/Criteria";
import Coverage from "./components/Coverage";
import ResultTable from "./components/ResultTable";
import AdSenseUnit from "../components/AdSenseUnit";

export const metadata: Metadata = {
  title: "配当重視スクリーニング | スクリーニング銘柄一覧",
  description:
    "配当利回り・ROE・自己資本比率・流動比率・売上高・営業利益率の6条件を、東証プライム市場およびスタンダード市場の全銘柄に機械的に適用した結果を表示します。株式会社トリロジー（近畿財務局長（金商）第372号）。",
};

// JSONから推論される型は各フィールドの実データに依存するため、
// 型定義側を正とみなして変換する。構造は build_site_data.py が保証する。
const screening = data as unknown as ScreeningData;

const ADSENSE_CLIENT_ID = process.env.NEXT_PUBLIC_ADSENSE_CLIENT_ID;
const ADSENSE_AD_SLOT = process.env.NEXT_PUBLIC_ADSENSE_AD_SLOT;
const ADSENSE_ENABLED = Boolean(ADSENSE_CLIENT_ID && ADSENSE_AD_SLOT);

export default function Home() {
  return (
    <div className="home">
      <section className="intro">
        <h1>スクリーニング銘柄一覧</h1>
        <p className="intro__asof">
          基準日 <time dateTime={screening.as_of}>{screening.as_of}</time>
          <span className="intro__universe">{screening.universe_label}</span>
        </p>
        <p className="intro__lead">
          あらかじめ定めた6つの財務条件を、対象市場の全
          {screening.counts.population.toLocaleString()}
          銘柄に機械的に適用し、すべてを満たした
          {screening.counts.passed.toLocaleString()}
          銘柄を全件掲載しています。
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
          <li>株価・配当：外部market data提供元</li>
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
