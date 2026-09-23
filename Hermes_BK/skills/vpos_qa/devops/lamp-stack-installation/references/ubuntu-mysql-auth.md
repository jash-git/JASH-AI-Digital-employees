# MySQL Authentication on Ubuntu 24.04+

## The Problem

Ubuntu 24.04 ships MySQL 8.0 with `auth_socket` (unix_socket) plugin as the default authentication method for the `root` user. This means:

- `sudo mysql` works (root OS user → MySQL root)
- `mysql -u root` fails: "Access denied for user 'root'@'localhost'"
- PHP/Python/any app connecting via TCP/socket as root fails

## Why This Matters

PHP runs under Apache's `www-data` user. Even if you know the MySQL root password, the unix_socket plugin ignores passwords entirely — it checks OS identity. Since `www-data` is not `root`, connection is denied.

## Solutions

### Option 1: Create a dedicated user (RECOMMENDED)

```sql
CREATE USER 'webapp'@'localhost' IDENTIFIED BY 'strong_password';
GRANT ALL PRIVILEGES ON mydb.* TO 'webapp'@'localhost';
FLUSH PRIVILEGES;
```

### Option 2: Switch root to mysql_native_password

```sql
ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY 'new_password';
FLUSH PRIVILEGES;
```

**Warning:** This weakens security. Option 1 is preferred.

### Option 3: Change MySQL auth globally

In `/etc/mysql/mysql.conf.d/mysqld.cnf`:
```
[mysqld]
default_authentication_plugin = mysql_native_password
```

Then restart MySQL. This affects ALL users.

## Verification

```bash
# Check auth method for a user
sudo mysql -u root -e "SELECT user, host, plugin FROM mysql.user WHERE user='root';"

# Expected output: root | localhost | auth_socket
```
