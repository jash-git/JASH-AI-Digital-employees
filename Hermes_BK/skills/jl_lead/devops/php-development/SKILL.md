---
name: php-development
description: "PHP development environment setup, PHP built-in server configuration, and development workflow patterns."
---

# PHP Development

## PHP Built-in Development Server

For quick development and testing, use PHP's built-in server instead of full Apache setup.

### Basic Usage

```bash
cd /path/to/project/src
php -S localhost:8080
```

### Document Root Issue

When your static files (HTML/CSS/JS) are in `public/` and PHP API files are in `api/`, a simple document root won't work:

```bash
# WRONG - only serves public/, API returns 404
php -S localhost:8080 -t public/

# WRONG - only serves from current dir, HTML files not found
php -S localhost:8080
```

### Solution: Router Script

Create `router.php` in the project root:

```php
<?php
// PHP Router for Development Server
$uri = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH);
$uri = urldecode($uri);

// MIME type map by extension (more reliable than mime_content_type())
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

// Serve static files from public/
if (file_exists(__DIR__ . '/public' . $uri)) {
    $path = __DIR__ . '/public' . $uri;
    if (is_file($path)) {
        $ext = strtolower(pathinfo($path, PATHINFO_EXTENSION));
        $mimeType = $mimeTypes['.' . $ext] ?? 'application/octet-stream';
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
```

Then start with:
```bash
php -S localhost:8080 router.php
```

### Pitfalls

1. **Session handling**: PHP built-in server doesn't persist sessions across requests in all environments. For testing, ensure `session_start()` is called in every PHP file that uses sessions.

2. **No Apache features**: `.htaccess`, mod_rewrite, and Apache-specific configurations won't work. Test with Apache in production.

3. **Single-threaded**: The built-in server is single-threaded and not suitable for concurrent requests. Only use for development.

4. **Falsy-coercion default (`?:`) swallows legitimate `0`**: When supplying a default with the null-coalescing-or-fallback operator, e.g. `$hour = filter_var($_POST['hour'], FILTER_VALIDATE_INT) ?: 12;`, PHP treats `0` as falsy and replaces it with the default. A legitimately-submitted `0` (e.g. hour=0 for 子時 / midnight) silently becomes `12`. This is a silent data bug — no error, wrong result.
   - **Fix**: Use explicit null checks instead of `?:` for numeric defaults: `$h = $_POST['hour'] ?? null; $h = ($h === null || !is_int($h)) ? 12 : $h;` (or check `=== false` from filter_var). The same trap applies to any field where `0` is a valid value — booleans, counts, indices, flags.
   - **Reproduction recipe**: see `references/php-falsy-coercion-default.md`.

## Development Workflow

1. Start PHP server with router
2. Test API endpoints directly with curl
3. Test frontend with browser
4. Verify session handling and authentication flow

## Common Issues

- **404 on API endpoints**: Check document root configuration
- **404 on HTML files**: Verify router script handles static files correctly
- **Session not persisting**: Ensure `session_start()` is called before any output
- **CORS issues**: When testing frontend and API on different ports, configure CORS headers
