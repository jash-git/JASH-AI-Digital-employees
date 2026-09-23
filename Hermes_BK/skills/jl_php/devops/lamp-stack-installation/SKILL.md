---
name: lamp-stack-installation
description: Install and configure Apache, PHP, and MySQL (LAMP stack) on Ubuntu/Debian systems.
---

# LAMP Stack Installation

Install and configure Apache, PHP, and MySQL (LAMP stack) on Ubuntu/Debian systems.

## Prerequisites

- Ubuntu 24.04+ or Debian-based system
- sudo privileges

## Steps

1. **Install packages**

   ```bash
   sudo DEBIAN_FRONTEND=noninteractive apt-get update -qq
   sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
     apache2 php libapache2-mod-php php-mysql \
     mysql-server php-mbstring php-xml php-curl php-gd php-zip
   ```

   Common PHP extensions to consider: `php-mbstring`, `php-xml`, `php-curl`, `php-gd`, `php-zip`, `php-intl`, `php-bcmath`.

2. **Start and enable services**

   ```bash
   sudo systemctl start apache2 && sudo systemctl enable apache2
   sudo systemctl start mysql && sudo systemctl enable mysql
   ```

3. **Verify installation**

   ```bash
   apache2 -v          # Apache version
   php -v              # PHP version
   sudo mysql -u root -e "SELECT 'OK' AS status;"  # MySQL (uses unix_socket auth)
   curl -s http://localhost/  # Apache default page
   ```

4. **Create MySQL user for PHP**

   **CRITICAL:** MySQL on Ubuntu 24.04+ uses `unix_socket` authentication by default. The `root` user can only connect via `sudo mysql` — PHP running as `www-data` CANNOT connect as root.

   ```bash
   sudo mysql -u root -e "
   CREATE USER IF NOT EXISTS 'webapp'@'localhost' IDENTIFIED BY '<password>';
   GRANT ALL PRIVILEGES ON <database>.* TO 'webapp'@'localhost';
   FLUSH PRIVILEGES;
   "
   ```

   Then in your PHP code, use the new user credentials instead of root.

5. **Test PHP-MySQL connection**

   Create `/var/www/html/info.php` with a mysqli test script and visit `http://localhost/info.php`.

## Pitfalls

- **MySQL unix_socket auth**: Never try to connect PHP as MySQL root. Create a dedicated user.
- **Permission denied on apt**: Always use `sudo` for apt operations. The lock file `/var/lib/apt/lists/lock` requires root.
- **mpm_prefork switch**: `libapache2-mod-php` automatically switches Apache from `mpm_event` to `mpm_prefork`. This is expected.
- **PHP extensions**: Install extensions (e.g., `php-mysqli`, `php-pdo`) at install time; they won't appear later without reinstalling the package.

## Reference Files

- `references/ubuntu-mysql-auth.md` — Details on MySQL authentication methods on Ubuntu
