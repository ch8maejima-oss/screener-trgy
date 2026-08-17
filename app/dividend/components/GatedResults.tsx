"use client";

// 銘柄一覧（stocks）はEA EXPO購入者限定のゲート配信データのため、ビルド時に
// 埋め込まれた公開JSONではなく、注文番号・メールアドレスの検証を通った場合のみ
// 実行時に取得する。取得できるまでは ResultTable の代わりに LicenseGate を表示する。

import { useEffect, useState } from "react";
import type { Stock } from "@/lib/types";
import ResultTable from "./ResultTable";
import LicenseGate from "../../components/LicenseGate";
import {
  clearStoredCredential,
  fetchGatedResource,
  gateErrorMessage,
  loadStoredCredential,
  storeCredential,
  type Credential,
} from "@/lib/gate";

const RESOURCE = "dividend/stocks";

export default function GatedResults() {
  const [stocks, setStocks] = useState<Stock[] | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const cred = loadStoredCredential();
    if (!cred) return;
    let cancelled = false;
    setSubmitting(true);
    fetchGatedResource<Stock[]>(cred, RESOURCE).then((result) => {
      if (cancelled) return;
      setSubmitting(false);
      if (result.ok && result.data) {
        setStocks(result.data);
      } else {
        setError(gateErrorMessage(result.error));
      }
    });
    return () => {
      cancelled = true;
    };
  }, []);

  async function handleSubmit(cred: Credential) {
    setSubmitting(true);
    setError(null);
    const result = await fetchGatedResource<Stock[]>(cred, RESOURCE);
    setSubmitting(false);
    if (result.ok && result.data) {
      storeCredential(cred);
      setStocks(result.data);
    } else {
      setError(gateErrorMessage(result.error));
    }
  }

  if (stocks) {
    return (
      <>
        <ResultTable stocks={stocks} />
        <p className="gate-clear-link">
          <button
            type="button"
            className="gate-field__link gate-field__link--button"
            onClick={() => {
              // このページ内に複数のゲート化コンポーネントが存在しうるため、
              // 自分のstateだけでなく全体をリロードして整合性を保つ。
              clearStoredCredential();
              window.location.reload();
            }}
          >
            この端末に保存した注文番号・メールアドレスを削除する
          </button>
        </p>
      </>
    );
  }

  return (
    <LicenseGate
      contentLabel="配当重視スクリーニング"
      initialError={error}
      onSubmit={handleSubmit}
      submitting={submitting}
    />
  );
}
