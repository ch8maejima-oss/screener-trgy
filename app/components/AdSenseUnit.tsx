"use client";

import { useEffect, useRef } from "react";

interface AdSenseUnitProps {
  client: string;
  slot: string;
}

/**
 * AdSenseの表示広告ユニット（クリック・視聴の強制なし）。
 * 同一ページ内に複数配置しても、要素ごとに一度だけpushする。
 */
export default function AdSenseUnit({ client, slot }: AdSenseUnitProps) {
  const insRef = useRef<HTMLModElement>(null);
  const pushedRef = useRef(false);

  useEffect(() => {
    if (pushedRef.current) return;
    pushedRef.current = true;
    try {
      (window.adsbygoogle = window.adsbygoogle || []).push({});
    } catch {
      // 読み込み失敗時は広告枠が空のまま残るだけで、ページの他の機能には影響しない。
    }
  }, []);

  return (
    <ins
      ref={insRef}
      className="adsbygoogle ad-slot__unit"
      data-ad-client={client}
      data-ad-slot={slot}
      data-ad-format="auto"
      data-full-width-responsive="true"
    />
  );
}
