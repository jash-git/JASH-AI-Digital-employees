<?php
declare(strict_types=1);

header('Content-Type: application/json; charset=utf-8');

// Only accept POST
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode(['code' => 1002, 'msg' => 'method_not_allowed'], JSON_UNESCAPED_UNICODE);
    exit;
}

// Destroy session
if (session_status() === PHP_SESSION_NONE) {
    session_start();
}

$_SESSION = [];

if (ini_get('session.use_cookies')) {
    $params = session_get_cookie_params();
    setcookie(
        session_name(),
        '',
        time() - 42000,
        $params['path'],
        $params['domain'],
        $params['secure'],
        $params['httponly']
    );
}

session_destroy();

echo json_encode(['code' => 0, 'msg' => 'logout_success'], JSON_UNESCAPED_UNICODE);
