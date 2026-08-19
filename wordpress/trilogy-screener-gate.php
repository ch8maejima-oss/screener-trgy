<?php
/**
 * Plugin Name: Trilogy Screener Gate
 * Description: screener.trgy.co.jp の有料コンテンツ配信。Welcartの注文（注文番号＋メールアドレス）
 *              を検証し、有効な購入者にのみスクリーニング銘柄データを返す。
 * Version: 1.0.0
 * Author: Trilogy Inc.
 *
 * 配置先: wp-content/mu-plugins/trilogy-screener-gate.php
 *（mu-pluginsはWordPress管理画面から無効化できない＝決済に関わる常時稼働コードとして適切）
 *
 * dividend.trgy.co.jp用の trilogy-dividend-gate.php と同じ設計だが、以下が異なる：
 * - 「銘柄コード」ではなく「/dividend」「/daytrade」等のページ単位のリソースキーで配信する
 * - 1つのサブスクリプション（30日/半年/1年）で screener.trgy.co.jp の全サブディレクトリを
 *   閲覧できる（プランによって見られるページが変わることはない）
 * - 既存の trilogy-dividend-gate.php とは別ファイル・別REST route・別データディレクトリ
 *   なので、互いの商品・注文検証ロジックには影響しない
 * ---------------------------------------------------------------------------
 */

if (!defined('ABSPATH')) {
    exit;
}

// ==============================================================
// 設定
// ==============================================================

// screener.trgy.co.jp用商品: 投稿ID => 購入後の有効期間（日数）。自動更新なし、
// 期限切れ後は再購入。2026-08-19、EA EXPOでの商品作成完了に伴い実際の投稿IDに差し替え済み。
// - post=3115: スクリーニング銘柄一覧／30日間プラン
// - post=3118: スクリーニング銘柄一覧／半年プラン（180日間）
// - post=3121: スクリーニング銘柄一覧／1年プラン（365日間）
define('TRILOGY_SCREENER_PRODUCTS', [
    3115 => 30,
    3118 => 180,
    3121 => 365,
]);

// 期限切れチェックを免除する管理者（開発側）メールアドレス。
// 支払い済みチェック（order_statusが空文字）は通常どおり適用される。
define('TRILOGY_SCREENER_ADMIN_EMAILS', ['ch8.maejima@gmail.com']);

// screener.trgy.co.jp からのアクセスのみ許可
define('TRILOGY_SCREENER_ALLOWED_ORIGIN', 'https://screener.trgy.co.jp');

// スクリーニング銘柄データ（<resource>.json）が置かれる非公開ディレクトリ。
// GitHub Actionsの日次バッチがFTPでここに配置する。
define('TRILOGY_SCREENER_DATA_DIR', WP_CONTENT_DIR . '/private/screener-data');

// レート制限: 同一IPからの検証試行を一定時間内に制限する（注文番号は連番のため総当たり対策）。
define('TRILOGY_SCREENER_RATE_LIMIT_MAX', 20);       // 制限時間内の最大試行回数
define('TRILOGY_SCREENER_RATE_LIMIT_WINDOW', 600);   // 制限時間（秒）＝10分

// ==============================================================
// REST APIルート登録
// ==============================================================

add_action('rest_api_init', function () {
    register_rest_route('trilogy-screener/v1', '/validate', [
        'methods'  => 'POST',
        'callback' => 'trilogy_screener_handle_validate',
        'permission_callback' => '__return_true', // 認証はorder_number+emailで行うためWP側の権限チェックは不要
        'args' => [
            'orderNumber' => ['required' => true, 'type' => 'string'],
            'email'       => ['required' => true, 'type' => 'string'],
            'resource'    => ['required' => true, 'type' => 'string'],
        ],
    ]);
});

// CORS: screener.trgy.co.jp からのみ許可し、他オリジンやクッキー送信は許可しない
add_action('rest_api_init', function () {
    remove_filter('rest_pre_serve_request', 'rest_send_cors_headers');
    add_filter('rest_pre_serve_request', function ($served, $result, $request) {
        if (strpos($request->get_route(), '/trilogy-screener/v1/') === 0) {
            $origin = get_http_origin();
            if ($origin === TRILOGY_SCREENER_ALLOWED_ORIGIN) {
                header('Access-Control-Allow-Origin: ' . TRILOGY_SCREENER_ALLOWED_ORIGIN);
                header('Access-Control-Allow-Methods: POST, OPTIONS');
                header('Access-Control-Allow-Headers: Content-Type');
                header('Vary: Origin');
            }
        }
        return $served;
    }, 10, 3);
}, 20);

// ==============================================================
// レート制限
// ==============================================================

function trilogy_screener_rate_limited(): bool
{
    $ip = $_SERVER['REMOTE_ADDR'] ?? 'unknown';
    $key = 'trilogy_scr_rl_' . md5($ip);
    $count = (int) get_transient($key);
    if ($count >= TRILOGY_SCREENER_RATE_LIMIT_MAX) {
        return true;
    }
    set_transient($key, $count + 1, TRILOGY_SCREENER_RATE_LIMIT_WINDOW);
    return false;
}

// ==============================================================
// 注文検証
// ==============================================================

/**
 * 注文番号＋メールアドレスから、対象商品の有効な注文を1件探す。
 * 見つからない・支払い未確定・期限切れ・対象商品を含まない場合は null。
 *
 * @return array{status: string, order?: object}
 */
function trilogy_screener_find_order(string $order_number, string $email): array
{
    global $wpdb;

    $id = intval(preg_replace('/\D/', '', $order_number));
    if ($id <= 0) {
        return ['status' => 'not_found'];
    }

    $table = $wpdb->prefix . 'usces_order';
    $order = $wpdb->get_row($wpdb->prepare(
        "SELECT ID, order_email, order_status, order_date, order_cart
         FROM {$table} WHERE ID = %d",
        $id
    ));

    if (!$order) {
        return ['status' => 'not_found'];
    }

    if (strcasecmp(trim($order->order_email), trim($email)) !== 0) {
        return ['status' => 'not_found'];
    }

    // 許可リスト方式: 決済確定を示す状態のみ有効。
    // Welcartのorder_statusは支払い方法・処理経路により形式が異なる。
    // - 空文字（一部の決済方法で自動確定した場合）
    // - "completion,receipted,"（銀行振込等、管理画面で対応状況=対応完了・
    //   入金状況=入金済みに手動更新した場合のカンマ区切りフラグ文字列）
    // 2026-08-19、実際のテスト注文（銀行振込）で確認・修正。他の未知の
    // ステータス値は無効として扱う。
    $order_status = trim((string) $order->order_status);
    $is_paid = $order_status === ''
        || (strpos($order_status, 'completion') !== false && strpos($order_status, 'receipted') !== false);
    if (!$is_paid) {
        return ['status' => 'unpaid'];
    }

    $product_id = trilogy_screener_find_cart_product($order->order_cart, array_keys(TRILOGY_SCREENER_PRODUCTS));
    if ($product_id === null) {
        return ['status' => 'wrong_product'];
    }
    $valid_days = TRILOGY_SCREENER_PRODUCTS[$product_id];

    $is_admin = in_array(strtolower(trim($email)), array_map('strtolower', TRILOGY_SCREENER_ADMIN_EMAILS), true);
    if (!$is_admin) {
        $order_time = strtotime($order->order_date);
        $expires_at = $order_time + $valid_days * DAY_IN_SECONDS;
        if (time() > $expires_at) {
            return ['status' => 'expired'];
        }
    }

    return ['status' => 'ok', 'order' => $order];
}

/**
 * order_cart（シリアライズ済み配列）に、対象商品（複数プラン）のいずれかの投稿IDが
 * 含まれるか調べ、最初に見つかった投稿IDを返す（無ければnull）。
 * Welcartのバージョンにより cart item のキー名が異なる可能性があるため、
 * 想定される複数のキー名を試す。実際のテスト注文で確認・調整すること。
 */
function trilogy_screener_find_cart_product($serialized_cart, array $product_ids): ?int
{
    if (empty($serialized_cart) || empty($product_ids)) {
        return null;
    }
    $cart = @unserialize($serialized_cart, ['allowed_classes' => false]);
    if (!is_array($cart)) {
        return null;
    }
    $candidate_keys = ['post_id', 'product_id', 'ID', 'item_id'];
    foreach ($cart as $item) {
        if (!is_array($item)) {
            continue;
        }
        foreach ($candidate_keys as $key) {
            if (!isset($item[$key])) {
                continue;
            }
            $found = intval($item[$key]);
            if (in_array($found, $product_ids, true)) {
                return $found;
            }
        }
    }
    return null;
}

// ==============================================================
// リクエストハンドラ
// ==============================================================

function trilogy_screener_handle_validate(WP_REST_Request $request)
{
    if (trilogy_screener_rate_limited()) {
        return new WP_REST_Response(['ok' => false, 'error' => 'rate_limited'], 429);
    }

    $order_number = sanitize_text_field($request->get_param('orderNumber'));
    $email        = sanitize_email($request->get_param('email'));
    // resourceは private-data/ 配下のファイルパスに対応するキー
    // （例: "dividend/stocks", "daytrade/archive/2026-08-17-buy"）。
    // 英数字・ハイフン・アンダースコア・スラッシュのみを許可し、".."は除去する
    // （パストラバーサル対策。realpathでの内包チェックと合わせた二重の防御）。
    $resource_raw = (string) $request->get_param('resource');
    $resource = preg_replace('/[^A-Za-z0-9\/_\-]/', '', str_replace('..', '', $resource_raw));

    if (!$order_number || !$email || !$resource) {
        return new WP_REST_Response(['ok' => false, 'error' => 'invalid_request'], 400);
    }

    $result = trilogy_screener_find_order($order_number, $email);

    if ($result['status'] !== 'ok') {
        // not_found / unpaid / wrong_product はすべて「無効な組み合わせ」として同じ扱いにし、
        // どの条件で弾かれたかを外部から推測されないようにする（unpaid/wrong_productは内部ログのみ）。
        $public_error = $result['status'] === 'expired' ? 'expired' : 'invalid';
        error_log(sprintf(
            '[trilogy-screener] validate failed: order=%s reason=%s ip=%s',
            $order_number, $result['status'], $_SERVER['REMOTE_ADDR'] ?? ''
        ));
        return new WP_REST_Response(['ok' => false, 'error' => $public_error], 403);
    }

    $path = TRILOGY_SCREENER_DATA_DIR . '/' . $resource . '.json';
    $real = realpath($path);
    $data_dir_real = realpath(TRILOGY_SCREENER_DATA_DIR);

    // パストラバーサル対策: 解決後のパスが必ずデータディレクトリの内側にあることを確認
    if (!$real || !$data_dir_real || strpos($real, $data_dir_real) !== 0) {
        return new WP_REST_Response(['ok' => false, 'error' => 'not_found'], 404);
    }

    $json = file_get_contents($real);
    $decoded = json_decode($json, true);
    if ($decoded === null) {
        return new WP_REST_Response(['ok' => false, 'error' => 'not_found'], 404);
    }

    return new WP_REST_Response(['ok' => true, 'data' => $decoded], 200);
}
