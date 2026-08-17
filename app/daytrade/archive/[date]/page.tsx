import fs from "fs";
import path from "path";
import Link from "next/link";
import { notFound } from "next/navigation";
import type { Metadata } from "next";
import type { DaytradeScreeningData } from "@/lib/daytrade-types";
import { DisclaimerBanner, DisclaimerFull } from "../../components/Disclaimer";
import GatedMomentum from "../../components/GatedMomentum";

const ARCHIVE_DIR = path.join(process.cwd(), "app", "daytrade", "data", "archive");

// 静的出力のため、生成されなかった日付は常に404にする。
export const dynamicParams = false;

export function generateStaticParams() {
  const dates = listArchiveDates();
  if (dates.length === 0) {
    // output: "export" は generateStaticParams が空配列を返すとビルドが失敗するため、
    // アーカイブが1件もない間はダミーの日付を1つ返し、ページ側で確実に404にする。
    return [{ date: "_placeholder" }];
  }
  return dates.map((date) => ({ date }));
}

function listArchiveDates(): string[] {
  if (!fs.existsSync(ARCHIVE_DIR)) return [];
  return fs
    .readdirSync(ARCHIVE_DIR)
    .filter((f) => f.endsWith(".json"))
    .map((f) => f.replace(/\.json$/, ""));
}

function loadArchive(date: string): DaytradeScreeningData | null {
  const filePath = path.join(ARCHIVE_DIR, `${date}.json`);
  if (!fs.existsSync(filePath)) return null;
  return JSON.parse(fs.readFileSync(filePath, "utf-8")) as DaytradeScreeningData;
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ date: string }>;
}): Promise<Metadata> {
  const { date } = await params;
  return {
    title: `${date}のアーカイブ | デイトレード用スクリーニング`,
    description:
      "デイトレード用スクリーニングの過去の結果を、当時のデータのまま保存したアーカイブです。株式会社トリロジー（近畿財務局長（金商）第372号）。",
  };
}

export default async function DaytradeArchiveDatePage({
  params,
}: {
  params: Promise<{ date: string }>;
}) {
  const { date } = await params;
  const data = loadArchive(date);
  if (!data) notFound();

  return (
    <div className="home">
      <p className="archive__back">
        <Link href="/daytrade/archive/">← アーカイブ一覧に戻る</Link>
      </p>

      <section className="intro">
        <h1>
          デイトレード用スクリーニング アーカイブ
          <span className="intro__universe"> {data.as_of}</span>
        </h1>
        <p className="intro__lead">
          {data.as_of}時点の判定結果をそのまま保存したページです。上昇モメンタム条件通過
          {data.counts.buy_passed.toLocaleString()}銘柄・下落モメンタム条件通過
          {data.counts.short_passed.toLocaleString()}銘柄を掲載しています。
        </p>
      </section>

      <DisclaimerBanner />

      <p className="results__section-note">
        この一覧は過去のアーカイブです。当時の条件判定結果であり、将来同様の値動きが
        再現されることを示すものではありません。選定条件は取得当時のものであり、
        現行の「/daytrade」ページの条件と異なる場合があります。このアーカイブの銘柄選定
        結果を、投資判断の根拠や売買シグナルとして利用しないでください。過去に条件を
        満たしたことは、当該条件の有効性や将来の収益性を示すものでも保証するものでも
        ありません。
      </p>

      <GatedMomentum
        resource={`daytrade/archive/${date}-buy`}
        direction="buy"
        contentLabel={`${date}のアーカイブ（上昇モメンタム）`}
      />
      <GatedMomentum
        resource={`daytrade/archive/${date}-short`}
        direction="short"
        contentLabel={`${date}のアーカイブ（下落モメンタム）`}
      />

      <p className="archive__back">
        <Link href="/daytrade/archive/">← アーカイブ一覧に戻る</Link>
      </p>

      <DisclaimerFull />
    </div>
  );
}
