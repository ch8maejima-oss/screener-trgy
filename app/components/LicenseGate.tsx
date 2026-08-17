"use client";

// EA EXPO購入者向けの認証フォーム。dividend-siteのLicenseGate.tsx（検索アクション時に
// 出るポップアップモーダル）とは違い、こちらはページ内の銘柄一覧が表示されるはずの
// 場所にそのまま埋め込むカード形式（ページ全体を覆うオーバーレイにはしない）。
// /dividend・/daytrade・/daytrade/archive/[date] で共用する。

import { useState } from "react";
import type { Credential } from "@/lib/gate";

interface LicenseGateProps {
  /** 検証中に表示する対象コンテンツ名（例: "デイトレード用スクリーニング"） */
  contentLabel: string;
  /** 直前の試行で発生したエラーメッセージ（あれば） */
  initialError?: string | null;
  onSubmit: (cred: Credential) => void;
  submitting: boolean;
}

export default function LicenseGate({
  contentLabel,
  initialError,
  onSubmit,
  submitting,
}: LicenseGateProps) {
  const [orderNumber, setOrderNumber] = useState("");
  const [email, setEmail] = useState("");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!orderNumber.trim() || !email.trim() || submitting) return;
    onSubmit({ orderNumber: orderNumber.trim(), email: email.trim() });
  }

  return (
    <section className="gate-card" aria-label={`${contentLabel}の閲覧にはご購入が必要です`}>
      <h2 className="gate-card__title">EA EXPOご購入者様専用</h2>

      <form className="gate-card__body" onSubmit={handleSubmit}>
        <p className="gate-card__disclosure">
          「{contentLabel}」の銘柄一覧は、EA EXPOでスクリーニング銘柄一覧の閲覧をご購入
          いただいた方限定でご覧いただけます。ご購入時の<strong>注文番号</strong>と
          <strong>メールアドレス</strong>をご入力ください。ご利用期間中は、配当重視・
          デイトレード用などすべてのスクリーニング結果をご覧いただけます。
        </p>

        <label className="gate-field">
          <span className="gate-field__label">注文番号</span>
          <input
            type="text"
            inputMode="numeric"
            className="gate-field__input"
            placeholder="例: 00000014"
            value={orderNumber}
            onChange={(e) => setOrderNumber(e.target.value)}
            autoComplete="off"
            disabled={submitting}
          />
        </label>

        <label className="gate-field">
          <span className="gate-field__label">メールアドレス</span>
          <input
            type="email"
            className="gate-field__input"
            placeholder="ご購入時にご登録のメールアドレス"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="email"
            disabled={submitting}
          />
        </label>

        {initialError && (
          <p className="gate-field__error" role="alert">
            {initialError}
          </p>
        )}

        <p className="gate-card__disclosure--sub">
          注文番号はEA EXPOのご注文完了メールに記載されています。
          ご利用期間は、ご購入いただいたプラン（30日間／半年／1年）により異なります。
          入力いただいた注文番号・メールアドレスは、次回以降の自動認証のためこの端末
          （ブラウザ）にのみ保存されます。共有端末でのご利用にはご注意ください。
        </p>

        <div className="gate-card__actions">
          <button
            type="submit"
            className="gate-card__btn"
            disabled={submitting || !orderNumber.trim() || !email.trim()}
          >
            {submitting ? "確認中…" : "銘柄一覧を見る"}
          </button>
        </div>

        <p className="gate-card__disclosure--sub">
          未購入の方は
          <a
            href="https://ea-exposition.com/category/item/indicator-tool"
            target="_blank"
            rel="noopener noreferrer"
            className="gate-field__link"
          >
            EA EXPOのご購入ページ
          </a>
          からお申し込みいただけます。
        </p>
      </form>
    </section>
  );
}
