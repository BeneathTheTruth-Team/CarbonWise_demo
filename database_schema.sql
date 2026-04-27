-- 碳智评 - 数据库初始化脚本
-- MySQL 8.0

CREATE DATABASE IF NOT EXISTS carbonwise_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE carbonwise_db;

-- 用户表
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(80) NOT NULL UNIQUE,
    email VARCHAR(120) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    user_type ENUM('enterprise', 'bank', 'admin') DEFAULT 'enterprise',
    company_name VARCHAR(200),
    credit_code VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_login DATETIME,
    INDEX idx_username (username),
    INDEX idx_credit_code (credit_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 设备参数表
CREATE TABLE IF NOT EXISTS equipments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    name VARCHAR(100) NOT NULL,
    model VARCHAR(100),
    quantity INT DEFAULT 1,
    rated_power FLOAT NOT NULL,
    daily_hours FLOAT DEFAULT 24.0,
    load_factor FLOAT DEFAULT 0.8,
    years_used INT DEFAULT 1,
    process VARCHAR(50),
    data_hash VARCHAR(64),
    is_anonymized BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_user_id (user_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 碳核算结果表
CREATE TABLE IF NOT EXISTS calculations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    annual_emission FLOAT NOT NULL,
    intensity FLOAT NOT NULL,
    env_cost FLOAT,
    uncertainty FLOAT,
    credit_rating VARCHAR(10),
    benchmark FLOAT DEFAULT 5.5,
    emission_factor_version VARCHAR(20),
    carbon_price FLOAT DEFAULT 80.0,
    annual_output FLOAT DEFAULT 1200.0,
    report_status ENUM('pending', 'generated', 'downloaded') DEFAULT 'pending',
    report_url VARCHAR(500),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_id (user_id),
    INDEX idx_created_at (created_at),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- API密钥表
CREATE TABLE IF NOT EXISTS api_keys (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    key_hash VARCHAR(255) NOT NULL UNIQUE,
    key_prefix VARCHAR(10) NOT NULL,
    name VARCHAR(100),
    permissions JSON DEFAULT '[]',
    is_active BOOLEAN DEFAULT TRUE,
    last_used_at DATETIME,
    expires_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 审计日志表
CREATE TABLE IF NOT EXISTS audit_logs (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    action VARCHAR(50) NOT NULL,
    resource_type VARCHAR(50),
    resource_id INT,
    ip_address VARCHAR(45),
    user_agent VARCHAR(500),
    details JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_id (user_id),
    INDEX idx_action (action),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 插入管理员账号 (密码: admin123)
INSERT INTO users (username, email, password_hash, user_type, company_name, is_active) 
VALUES ('admin', 'admin@carbonwise.com', 
        'pbkdf2:sha256:600000$example$hash_here_change_in_production', 
        'admin', '碳智评平台', TRUE)
ON DUPLICATE KEY UPDATE id=id;
