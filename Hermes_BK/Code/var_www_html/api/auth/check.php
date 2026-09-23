<?php
declare(strict_types=1);

header('Content-Type: application/json; charset=utf-8');

// Start session to check login state
if (session_status() === PHP_SESSION_NONE) {
    session_start();
}

if (isset($_SESSION['is_logged_in']) && $_SESSION['is_logged_in'] === true) {
    echo json_encode([
        'code' => 0,
        'msg'  => 'logged_in',
        'data' => [
            'user_id'  => (int) ($_SESSION['user_id'] ?? 0),
            'username' => $_SESSION['username'] ?? '',
            'role'     => $_SESSION['role'] ?? '',
        ],
    ], JSON_UNESCAPED_UNICODE);
} else {
    echo json_encode(['code' => 1004, 'msg' => 'not_logged_in'], JSON_UNESCAPED_UNICODE);
}
