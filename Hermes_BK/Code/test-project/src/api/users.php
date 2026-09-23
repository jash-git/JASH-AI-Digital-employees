<?php
declare(strict_types=1);

header('Content-Type: application/json; charset=utf-8');

// ── Helpers ──────────────────────────────────────────────────────────────────

function respond(int $code, string $msg, array $extra = []): void
{
    $payload = ['code' => $code, 'msg' => $msg];
    if (!empty($extra)) {
        $payload = array_merge($payload, $extra);
    }
    echo json_encode($payload, JSON_UNESCAPED_UNICODE);
    exit;
}

// ── Load DB config from .env ─────────────────────────────────────────────────

$configPath = dirname(__DIR__) . '/config/.env';
$config     = parse_ini_file($configPath, false, INI_SCANNER_RAW);

if ($config === false) {
    respond(500, 'config_load_failed');
}

$host = $config['DB_HOST'] ?? 'localhost';
$port = $config['DB_PORT'] ?? '3306';
$name = $config['DB_NAME'] ?? 'webapp_db';
$user = $config['DB_USER'] ?? 'webapp';
$pass = $config['DB_PASS'] ?? '';

// ── DB connection ────────────────────────────────────────────────────────────

try {
    $dsn = "mysql:host={$host};port={$port};dbname={$name};charset=utf8mb4";
    $pdo = new PDO($dsn, $user, $pass, [
        PDO::ATTR_ERRMODE            => PDO::ERRMODE_EXCEPTION,
        PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
        PDO::ATTR_EMULATE_PREPARES   => false,
    ]);
} catch (PDOException $e) {
    respond(500, 'database_error');
}

// ── Schema migration: ensure status column exists ────────────────────────────

try {
    $pdo->exec("
        ALTER TABLE users
        ADD COLUMN IF NOT EXISTS status TINYINT NOT NULL DEFAULT 1
    ");
} catch (PDOException $e) {
    // Table may not exist yet; ignore — will surface in endpoint handlers
}

// ── Session validation ───────────────────────────────────────────────────────

session_start();

if (!isset($_SESSION['is_logged_in']) || $_SESSION['is_logged_in'] !== true) {
    respond(1004, 'not_logged_in');
}

// ── Route ────────────────────────────────────────────────────────────────────

$method = $_GET['method'] ?? '';

switch ($_SERVER['REQUEST_METHOD']) {

    /* ── GET list ─────────────────────────────────────────────────────────── */

    case 'GET':
        if ($method !== 'list' && $method !== 'detail') {
            http_response_code(405);
            respond(1005, 'method_not_allowed');
        }

        if ($method === 'detail') {
            $id = filter_var($_GET['id'] ?? '', FILTER_VALIDATE_INT);
            if ($id === false || $id <= 0) {
                respond(1003, '無效的 ID');
            }

            $stmt = $pdo->prepare(
                'SELECT id, username, role, status, created_at
                 FROM users WHERE id = :id LIMIT 1'
            );
            $stmt->execute([':id' => $id]);
            $user = $stmt->fetch();

            if ($user === false) {
                respond(1001, '用戶不存在');
            }

            respond(0, 'success', ['data' => $user]);
        }

        /* ── GET list ─────────────────────────────────────────────────────── */

        $page    = max(1, intval($_GET['page'] ?? 1));
        $limit   = max(1, min(100, intval($_GET['limit'] ?? 10)));
        $offset  = ($page - 1) * $limit;

        $where   = [];
        $params  = [];

        if (isset($_GET['username']) && $_GET['username'] !== '') {
            $where[] = 'username LIKE :username';
            $params[':username'] = '%' . str_replace(['%', '_'], ['\\%', '\\_'], trim($_GET['username'])) . '%';
        }

        if (isset($_GET['role']) && $_GET['role'] !== '') {
            $role = trim($_GET['role']);
            if ($role === 'admin' || $role === 'user') {
                $where[] = 'role = :role';
                $params[':role'] = $role;
            }
        }

        $whereSql = $where ? 'WHERE ' . implode(' AND ', $where) : '';

        // Total count
        $countSql = "SELECT COUNT(*) FROM users {$whereSql}";
        $countStmt = $pdo->prepare($countSql);
        $countStmt->execute($params);
        $total = (int) $countStmt->fetchColumn();

        // Paginated data
        $dataSql = "SELECT id, username, role, status, created_at
                    FROM users {$whereSql}
                    ORDER BY id DESC
                    LIMIT :limit OFFSET :offset";
        $dataStmt = $pdo->prepare($dataSql);
        foreach ($params as $k => $v) {
            $dataStmt->bindValue($k, $v);
        }
        $dataStmt->bindValue(':limit', $limit, PDO::PARAM_INT);
        $dataStmt->bindValue(':offset', $offset, PDO::PARAM_INT);
        $dataStmt->execute();
        $rows = $dataStmt->fetchAll();

        respond(0, '', ['count' => $total, 'data' => $rows]);
        break;

    /* ── POST create / update / delete ────────────────────────────────────── */

    case 'POST':
        if ($method !== 'create' && $method !== 'update' && $method !== 'delete') {
            http_response_code(405);
            respond(1005, 'method_not_allowed');
        }

        $rawInput = file_get_contents('php://input');
        $input    = json_decode($rawInput, true);

        if ($input === null) {
            respond(1003, 'invalid_json');
        }

        if ($method === 'create') {
            $username = trim($input['username'] ?? '');
            $password = $input['password'] ?? '';
            $role     = trim($input['role'] ?? 'user');
            $status   = isset($input['status']) ? intval($input['status']) : 1;

            // Validation
            if ($username === '') {
                respond(1003, '帳號不可空白');
            }
            if ($password === '' || strlen($password) < 6) {
                respond(1003, '密碼長度至少 6 字元');
            }
            if ($role !== 'admin' && $role !== 'user') {
                respond(1003, '角色必須為 admin 或 user');
            }
            if ($status !== 0 && $status !== 1) {
                respond(1003, '狀態必須為 0 或 1');
            }

            // Check duplicate
            $stmt = $pdo->prepare('SELECT id FROM users WHERE username = :username LIMIT 1');
            $stmt->execute([':username' => $username]);
            if ($stmt->fetch()) {
                respond(1002, '帳號已存在');
            }

            $hash = password_hash($password, PASSWORD_DEFAULT);
            $stmt = $pdo->prepare(
                'INSERT INTO users (username, password_hash, role, status)
                 VALUES (:username, :password_hash, :role, :status)'
            );
            $stmt->execute([
                ':username'      => $username,
                ':password_hash' => $hash,
                ':role'          => $role,
                ':status'        => $status,
            ]);

            respond(0, '新增成功', ['data' => ['id' => (int) $pdo->lastInsertId()]]);
        }

        if ($method === 'update') {
            $id       = filter_var($input['id'] ?? '', FILTER_VALIDATE_INT);
            $username = trim($input['username'] ?? '');
            $password = $input['password'] ?? '';
            $role     = trim($input['role'] ?? 'user');
            $status   = isset($input['status']) ? intval($input['status']) : 1;

            if ($id === false || $id <= 0) {
                respond(1003, '無效的 ID');
            }
            if ($username === '') {
                respond(1003, '帳號不可空白');
            }
            if ($password !== '' && strlen($password) < 6) {
                respond(1003, '密碼長度至少 6 字元');
            }
            if ($role !== 'admin' && $role !== 'user') {
                respond(1003, '角色必須為 admin 或 user');
            }
            if ($status !== 0 && $status !== 1) {
                respond(1003, '狀態必須為 0 或 1');
            }

            // Check user exists
            $stmt = $pdo->prepare('SELECT id FROM users WHERE id = :id LIMIT 1');
            $stmt->execute([':id' => $id]);
            if (!$stmt->fetch()) {
                respond(1001, '用戶不存在');
            }

            // Check username duplicate (exclude self)
            $stmt = $pdo->prepare(
                'SELECT id FROM users WHERE username = :username AND id != :id LIMIT 1'
            );
            $stmt->execute([':username' => $username, ':id' => $id]);
            if ($stmt->fetch()) {
                respond(1002, '帳號已存在');
            }

            if ($password !== '') {
                $hash = password_hash($password, PASSWORD_DEFAULT);
                $stmt = $pdo->prepare(
                    'UPDATE users SET username = :username, password_hash = :password_hash,
                                     role = :role, status = :status WHERE id = :id'
                );
                $stmt->execute([
                    ':username'      => $username,
                    ':password_hash' => $hash,
                    ':role'          => $role,
                    ':status'        => $status,
                    ':id'            => $id,
                ]);
            } else {
                $stmt = $pdo->prepare(
                    'UPDATE users SET username = :username, role = :role,
                                     status = :status WHERE id = :id'
                );
                $stmt->execute([
                    ':username' => $username,
                    ':role'     => $role,
                    ':status'   => $status,
                    ':id'       => $id,
                ]);
            }

            respond(0, '修改成功');
        }

        if ($method === 'delete') {
            $id = filter_var($input['id'] ?? '', FILTER_VALIDATE_INT);

            if ($id === false || $id <= 0) {
                respond(1003, '無效的 ID');
            }
            if ($id === 1) {
                respond(1003, '不可刪除預設管理員帳號');
            }

            $stmt = $pdo->prepare('SELECT id FROM users WHERE id = :id LIMIT 1');
            $stmt->execute([':id' => $id]);
            if (!$stmt->fetch()) {
                respond(1001, '用戶不存在');
            }

            $stmt = $pdo->prepare('DELETE FROM users WHERE id = :id');
            $stmt->execute([':id' => $id]);

            respond(0, '刪除成功');
        }
        break;

    default:
        http_response_code(405);
        respond(1005, 'method_not_allowed');
}
