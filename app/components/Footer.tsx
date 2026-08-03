/**
 * フッター。金商法上の表示義務事項（商号・登録番号・加入協会名）を明記。
 * 出典: www.trgy.co.jp
 */
export default function Footer() {
  return (
    <footer className="site-footer">
      <div className="site-footer__inner">
        <p className="site-footer__company">株式会社トリロジー（Trilogy Inc.）</p>
        <ul className="site-footer__reg">
          <li>金融商品取引業 投資助言・代理業</li>
          <li>登録番号：近畿財務局長（金商）第372号</li>
          <li>加入協会：一般社団法人資産運用業協会（022-00269）</li>
          <li>所在地：大阪市北区天満2-1-27</li>
          <li>連絡先：info@trgy.co.jp／080-4496-3951</li>
        </ul>
        <ul className="site-footer__links">
          <li>
            <a href="https://www.trgy.co.jp/about-us/particular/" target="_blank" rel="noopener noreferrer">
              免責事項
            </a>
          </li>
          <li>
            <a href="https://www.trgy.co.jp/about-us/privatepolicy/" target="_blank" rel="noopener noreferrer">
              プライバシーポリシー
            </a>
          </li>
          <li>
            <a href="https://www.trgy.co.jp/about-us/compliance/" target="_blank" rel="noopener noreferrer">
              コンプライアンス
            </a>
          </li>
          <li>
            <a href="https://www.trgy.co.jp/about-us/fiduciary/" target="_blank" rel="noopener noreferrer">
              顧客本位の業務運営方針
            </a>
          </li>
          <li>
            <a href="https://www.trgy.co.jp/" target="_blank" rel="noopener noreferrer">
              公式サイト
            </a>
          </li>
        </ul>
        <p className="site-footer__copy">
          © {new Date().getFullYear()} Trilogy Inc. All rights reserved.
        </p>
      </div>
    </footer>
  );
}
