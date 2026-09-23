<?php
declare(strict_types=1);

header('Content-Type: application/json; charset=utf-8');

// Load DB config from .env
$configPath = dirname(__DIR__, 2) . '/config/.env';
$config     = parse_ini_file($configPath, false, INI_SCANNER_RAW);

if ($config === false) {
    http_response_code(500);
    echo json_encode(['code' => 500, 'msg' => 'config_load_failed'], JSON_UNESCAPED_UNICODE);
    exit;
}

$host = $config['DB_HOST'] ?? 'localhost';
$port = $config['DB_PORT'] ?? '3306';
$name = $config['DB_NAME'] ?? 'webapp_db';
$user = $config['DB_USER'] ?? 'webapp';
$pass = $config['DB_PASS'] ?? '';

// Only accept POST
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode(['code' => 1002, 'msg' => 'method_not_allowed'], JSON_UNESCAPED_UNICODE);
    exit;
}

// Read raw body and parse JSON
$rawInput = file_get_contents('php://input');
$input    = json_decode($rawInput, true);

if ($input === null) {
    http_response_code(400);
    echo json_encode(['code' => 1003, 'msg' => 'invalid_json'], JSON_UNESCAPED_UNICODE);
    exit;
}

$username = $input['username'] ?? '';
$password = $input['password'] ?? '';

if ($username === '' || $password === '') {
    echo json_encode(['code' => 1001, 'msg' => '帳密錯誤'], JSON_UNESCAPED_UNICODE);
    exit;
}

try {
    $dsn = "mysql:host={$host};port={$port};dbname={$name};charset=utf8mb4";
    $pdo = new PDO($dsn, $user, $pass, [
        PDO::ATTR_ERRMODE            => PDO::ERRMODE_EXCEPTION,
        PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
        PDO::ATTR_EMULATE_PREPARES   => false,
    ]);

    $stmt = $pdo->prepare('SELECT id, username, password_hash, role FROM users WHERE username = :username LIMIT 1');
    $stmt->execute([':username' => $username]);
    $user = $stmt->fetch();

    if ($user === false || !password_verify($password, $user['password_hash'])) {
        echo json_encode(['code' => 1001, 'msg' => '帳密錯誤'], JSON_UNESCAPED_UNICODE);
        exit;
    }

    // Start session and store user info
    session_start();
    $_SESSION['is_logged_in'] = true;
    $_SESSION['user_id']      = (int) $user['id'];
    $_SESSION['username']     = $user['username'];
    $_SESSION['role']         = $user['role'];

    echo json_encode([
        'code' => 0,
        'msg'  => 'login_success',
        'data' => [
            'user_id'  => (int) $user['id'],
            'username' => $user['username'],
            'role'     => $user['role'],
        ],
    ], JSON_UNESCAPED_UNICODE);

} catch (PDOException $e) {
    http_response_code(500);
    echo json_encode(['code' => 500, 'msg' => 'database_error'], JSON_UNESCAPED_UNICODE);
}
