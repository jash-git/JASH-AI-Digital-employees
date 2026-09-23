-- Users table for authentication
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('admin','user') DEFAULT 'user',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Default admin account (password: admin123)
INSERT INTO users (username, password_hash, role) VALUES ('admin', '$2y$10$q98u7Tkm3PdNGlRVItOs7.N854f9JygSHe9n0qke5GHiKdH3Jj4ry', 'admin');
