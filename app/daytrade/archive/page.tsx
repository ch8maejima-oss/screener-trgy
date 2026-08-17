import fs from "fs";
import path from "path";
import Link from "next/link";
import type { Metadata } from "next";
import type { DaytradeScreeningData } from "@/lib/daytrade-types";
import { DisclaimerBanner } from "../components/Disclaimer";

const ARCHIVE_DIR = path.join(process.cwd(), "app", "daytrade", "data", "archive");

export const metadata: Metadata = {
  title: "アーカイブ一覧 | デイトレード用スクリーニング",
  description:
    "デイトレード用スクリーニングの過去の結果を日付ごとに保存したアーカイブの一覧です。株式会社トリロジー（近畿財務局長（金商）第372号）。",
};

type Entry = {
  date: string;
  buy_passed: number;
  short_passed: number;
};

function loadEntries(): Entry[] {
  if (!fs.existsSync(ARCHIVE_DIR)) return [];
  const files = fs.readdirSync(ARCHIVE_DIR).filter((f) => f.endsWith(".json"));
  const entries = files.map((f) => {
    const data = JSON.parse(
      fs.readFileSync(path.join(ARCHIVE_DIR, f), "utf-8"),
    ) as DaytradeScreeningData;
    return {
      date: data.as_of,
      buy_passed: data.counts.buy_passed,
      short_passed: data.counts.short_passed,
    };
  });
  return entries.sort((a, b) => (a.date < b.date ? 1 : -1));
}

function groupByMonth(entries: Entry[]): { month: string; entries: Entry[] }[] {
  const groups = new Map<string, Entry[]>();
  for (const e of entries) {
    const month = e.date.slice(0, 7); // "YYYY-MM"
    if (!groups.has(month)) groups.set(month, []);
    groups.get(month)!.push(e);
  }
  return Array.from(groups.entries()).map(([month, entries]) => ({ month, entries }));
}

function monthLabel(month: string): string {
  const [y, m] = month.split("-");
  return `${y}年${Number(m)}月`;
}

export default function DaytradeArchiveIndexPage() {
  const entries = loadEntries();
  const groups = groupByMonth(entries);

  return (
    <div className="home">
      <p className="archive__back">
        <Link href="/daytrade/">← デイトレード用スクリーニングに戻る</Link>
      </p>

      <section className="intro">
        <h1>アーカイブ一覧</h1>
        <p className="intro__lead">
          デイトレード用スクリーニングの過去の判定結果を、日付ごとにそのまま保存しています。
          過去の抽出結果を振り返る用途を想定していますが、将来同様の値動きが再現されることを
          示すものではありません。投資判断の根拠や売買シグナルとして利用しないでください。
        </p>
      </section>

      <DisclaimerBanner />

      {groups.length === 0 && (
        <section className="archive__empty">
          <p>まだアーカイブがありません。日次バッチが実行されると翌日以降に蓄積されます。</p>
        </section>
      )}

      {groups.map((g) => (
        <section key={g.month} className="archive__month" aria-label={monthLabel(g.month)}>
          <h2>{monthLabel(g.month)}</h2>
          <ul className="archive__list">
            {g.entries.map((e) => (
              <li key={e.date} className="archive__item">
                <Link href={`/daytrade/archive/${e.date}/`} className="archive__item-link">
                  <span className="archive__item-date">{e.date}</span>
                  <span className="archive__item-counts">
                    上昇 {e.buy_passed.toLocaleString()}件 / 下落 {e.short_passed.toLocaleString()}件
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}
