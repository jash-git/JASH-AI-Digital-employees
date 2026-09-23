<?php
// PHP Router for Development Server
// Serves static files from public/ and routes API requests to api/
// Usage: php -S localhost:8080 router.php

$uri = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH);
$uri = urldecode($uri);

// Serve static files from public/
if (file_exists(__DIR__ . '/public' . $uri)) {
    $path = __DIR__ . '/public' . $uri;
    if (is_file($path)) {
        $mimeType = mime_content_type($path);
        header("Content-Type: $mimeType");
        readfile($path);
        return true;
    }
}

// Route API requests
if (strpos($uri, '/api/') === 0) {
    $apiFile = __DIR__ . $uri;
    if (file_exists($apiFile) && is_file($apiFile)) {
        include $apiFile;
        return true;
    }
}

// 404
http_response_code(404);
echo "Not Found";
return false;
