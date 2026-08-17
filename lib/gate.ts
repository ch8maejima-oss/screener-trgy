// screener.trgy.co.jp の会員ゲート。EA EXPO（ea-exposition.com, Welcart）の
// 注文番号＋メールアドレスをWordPress側の検証エンドポイントに照会し、
// 通った場合のみ有料コンテンツ（銘柄データ）を受け取る。dividend.trgy.co.jpの
// lib/gate.ts と同じ設計だが、対象が「銘柄コード」ではなく「/dividend」
// 「/daytrade」等のページ単位のリソースキーである点が異なる。

const VALIDATE_ENDPOINT = "https://ea-exposition.com/wp-json/trilogy-screener/v1/validate";
const STORAGE_KEY = "trilogy-screener-credential";

export type GateErrorCode = "invalid" | "expired" | "rate_limited" | "network" | "not_found";

export interface Credential {
  orderNumber: string;
  email: string;
}

export interface GateResult<T> {
  ok: boolean;
  data?: T;
  error?: GateErrorCode;
}

export function loadStoredCredential(): Credential | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (typeof parsed?.orderNumber === "string" && typeof parsed?.email === "string") {
      return parsed;
    }
  } catch {
    // 壊れた保存値は無視する
  }
  return null;
}

export function storeCredential(cred: Credential): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(cred));
}

export function clearStoredCredential(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(STORAGE_KEY);
}

interface RawGateResult {
  ok: boolean;
  data?: unknown;
  error?: GateErrorCode;
}

async function postGate(cred: Credential, resource: string): Promise<RawGateResult> {
  try {
    const res = await fetch(VALIDATE_ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        orderNumber: cred.orderNumber.trim(),
        email: cred.email.trim(),
        resource,
      }),
    });

    if (res.status === 429) {
      return { ok: false, error: "rate_limited" };
    }
    if (res.status === 403) {
      const json = await res.json().catch(() => null);
      const error: GateErrorCode = json?.error === "expired" ? "expired" : "invalid";
      return { ok: false, error };
    }
    if (res.status === 404) {
      return { ok: false, error: "not_found" };
    }
    if (!res.ok) {
      return { ok: false, error: "network" };
    }

    const json = await res.json();
    if (!json.ok || json.data === undefined) {
      return { ok: false, error: "network" };
    }
    return { ok: true, data: json.data };
  } catch {
    return { ok: false, error: "network" };
  }
}

/**
 * 有料コンテンツ（銘柄データ）を取得する。認証情報は取得のたびにサーバー側で
 * 再検証される（期限切れ・注文状況の変化に追従するため、結果はキャッシュしない）。
 * resource は "dividend-stocks" 等の固定キー文字列（WordPress側の非公開
 * ディレクトリ内のファイル名に対応する）。
 */
export async function fetchGatedResource<T>(
  cred: Credential,
  resource: string,
): Promise<GateResult<T>> {
  const result = await postGate(cred, resource);
  if (!result.ok) return { ok: false, error: result.error };
  return { ok: true, data: result.data as T };
}

export function gateErrorMessage(error: GateErrorCode | undefined): string {
  switch (error) {
    case "invalid":
      return "注文番号またはメールアドレスが一致しませんでした。EA EXPOでのご購入情報をご確認ください。";
    case "expired":
      return "ご利用期間（ご購入いただいたプランの有効期間）が終了しています。引き続きご利用いただくには再度お申し込みください。";
    case "rate_limited":
      return "試行回数が多いため、しばらく時間をおいて再度お試しください。";
    case "not_found":
      return "データが見つかりませんでした。時間をおいて再度お試しください。";
    case "network":
    default:
      return "通信エラーが発生しました。時間をおいて再度お試しください。";
  }
}
