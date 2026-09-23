<?php
// PHP Router for Apache
// Serves static files from public/ and routes API requests to api/

$uri = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH);
$uri = urldecode($uri);

// MIME type map by extension
$mimeTypes = [
    '.css'  => 'text/css',
    '.js'   => 'application/javascript',
    '.html' => 'text/html',
    '.htm'  => 'text/html',
    '.json' => 'application/json',
    '.png'  => 'image/png',
    '.jpg'  => 'image/jpeg',
    '.jpeg' => 'image/jpeg',
    '.gif'  => 'image/gif',
    '.svg'  => 'image/svg+xml',
    '.ico'  => 'image/x-icon',
    '.woff' => 'font/woff',
    '.woff2'=> 'font/woff2',
    '.ttf'  => 'font/ttf',
    '.eot'  => 'application/vnd.ms-fontobject',
    '.otf'  => 'font/otf',
    '.map'  => 'application/json',
];

// Redirect root to login page
if ($uri === '/' || $uri === '') {
    header('Location: /login.html', true, 302);
    exit;
}

// Serve static files from public/
if (file_exists(__DIR__ . '/public' . $uri)) {
    $path = __DIR__ . '/public' . $uri;
    if (is_file($path)) {
        $ext = strtolower(pathinfo($path, PATHINFO_EXTENSION));
        $mimeType = $mimeTypes['.' . $ext] ?? 'application/octet-stream';
        header("Content-Type: $mimeType");
        readfile($path);
        exit;
    }
}

// Route API requests
if (strpos($uri, '/api/') === 0) {
    $apiFile = __DIR__ . $uri;
    if (file_exists($apiFile) && is_file($apiFile)) {
        include $apiFile;
        exit;
    }
}

// 404
http_response_code(404);
echo "Not Found";
