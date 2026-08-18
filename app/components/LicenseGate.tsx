"use client";

// EA EXPO購入者向けの認証モーダル。dividend-siteのLicenseGate.tsx
// （検索アクション時にポップアップするオーバーレイモーダル）と同じ表示構造
// （オーバーレイ・ARIA・Escキー・スクロールロック）に合わせている。
// ページ内に埋め込むカード形式だと目立たないというフィードバックを受けて変更した。
// /dividend・/daytrade・/daytrade/archive/[date] で共用する。呼び出し側は
// 「銘柄一覧を見る」ボタン等でこのモーダルを開き、cancelで閉じる導線を持つこと。

import { useEffect, useState } from "react";
import type { Credential } from "@/lib/gate";

interface LicenseGateProps {
  /** 検証中に表示する対象コンテンツ名（例: "デイトレード用スクリーニング"） */
  contentLabel: string;
  /** 直前の試行で発生したエラーメッセージ（あれば） */
  initialError?: string | null;
  onSubmit: (cred: Credential) => void;
  onCancel: () => void;
  submitting: boolean;
}

export default function LicenseGate({
  contentLabel,
  initialError,
  onSubmit,
  onCancel,
  submitting,
}: LicenseGateProps) {
  const [orderNumber, setOrderNumber] = useState("");
  const [email, setEmail] = useState("");

  useEffect(() => {
    document.body.classList.add("no-scroll");
    return () => document.body.classList.remove("no-scroll");
  }, []);

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape" && !submitting) {
        onCancel();
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [submitting, onCancel]);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!orderNumber.trim() || !email.trim() || submitting) return;
    onSubmit({ orderNumber: orderNumber.trim(), email: email.trim() });
  }

  return (
    <div
      className="gate-modal"
      role="dialog"
      aria-modal="true"
      aria-labelledby="license-gate-title"
    >
      <div className="gate-modal__overlay" aria-hidden="true" />
      <div className="gate-modal__panel">
        <h2 id="license-gate-title" className="gate-modal__title">
          EA EXPOご購入者様専用
        </h2>

        <form className="gate-modal__body" onSubmit={handleSubmit}>
          <p className="gate-modal__disclosure">
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
              autoFocus
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

          <p className="gate-modal__disclosure--sub">
            注文番号はEA EXPOのご注文完了メールに記載されています。
            ご利用期間は、ご購入いただいたプラン（30日間／半年／1年）により異なります。
            入力いただいた注文番号・メールアドレスは、次回以降の自動認証のためこの端末
            （ブラウザ）にのみ保存されます。共有端末でのご利用にはご注意ください。
          </p>

          <div className="gate-modal__actions">
            <button
              type="submit"
              className="gate-modal__btn gate-modal__btn--primary"
              disabled={submitting || !orderNumber.trim() || !email.trim()}
            >
              {submitting ? "確認中…" : "銘柄一覧を見る"}
            </button>
            <button
              type="button"
              className="gate-modal__btn gate-modal__btn--secondary"
              onClick={onCancel}
              disabled={submitting}
            >
              キャンセル
            </button>
          </div>

          <p className="gate-modal__disclosure--sub">
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
      </div>
    </div>
  );
}
