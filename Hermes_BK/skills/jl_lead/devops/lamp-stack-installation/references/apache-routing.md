# Apache Routing for Static + API Projects

When deploying a PHP project with static frontend files (in `public/`) and API PHP files (in `api/`) to Apache, you need TWO files:

## 1. .htaccess (in project root)

```apache
RewriteEngine On
DirectoryIndex index.php

# If the requested file or directory exists, serve it directly
RewriteCond %{REQUEST_FILENAME} -f [OR]
RewriteCond %{REQUEST_FILENAME} -d
RewriteRule ^ - [L]

# Otherwise, route to index.php
RewriteRule ^(.*)$ index.php [L]
```

## 2. index.php (in project root)

```php
<?php
// PHP Router for Apache Deployment
$uri = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH);
$uri = urldecode($uri);

// Redirect root to login page
if ($uri === '/' || $uri === '') {
    header('Location: /login.html', true, 302);
    exit;
}

// Serve static files from public/
if (file_exists(__DIR__ . '/public' . $uri)) {
    $path = __DIR__ . '/public' . $uri;
    if (is_file($path)) {
        $mimeType = mime_content_type($path);
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
exit;
```

## Key Differences from PHP Built-in Router

| Aspect | PHP Built-in (`router.php`) | Apache Deployment |
|---|---|---|
| File name | `router.php` (passed to `-S`) | `index.php` (DirectoryIndex) |
| Routing | `php -S localhost:8080 router.php` | `.htaccess` → `index.php` |
| Root redirect | Handled in router.php | Handled in index.php |
| Static files | Served automatically from cwd | Must be routed via index.php |
| API files | Must be routed via index.php | Must be routed via index.php |

## Apache Configuration Required

1. Enable mod_rewrite: `sudo a2enmod rewrite`
2. Allow .htaccess overrides:
   ```bash
   sudo tee /etc/apache2/conf-available/allow-override.conf > /dev/null << 'EOF'
   <Directory /var/www/html>
       AllowOverride All
       Require all granted
   </Directory>
   EOF
   sudo a2enconf allow-override
   ```
3. Restart: `sudo systemctl restart apache2`

## Common Pitfalls

- **Just copying `router.php` is NOT enough**: Apache doesn't use `php -S router.php`. It needs `.htaccess` + `index.php` as DirectoryIndex.
- **Missing `.htaccess`**: Without it, Apache serves files directly and API requests hit 404.
- **Missing `AllowOverride All`**: Without it, `.htaccess` is ignored and rewrite rules don't work.
- **Missing `exit` after `return true`**: In PHP built-in router, `return true` works. In Apache via `include`, you MUST use `exit` to prevent further execution.
- **Router.php in root vs index.php**: The `router.php` in `src/` is for PHP built-in server only. The `index.php` in `/var/www/html/` is for Apache production.
