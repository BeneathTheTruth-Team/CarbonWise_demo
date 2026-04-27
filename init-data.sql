-- 碳智评 - 示例数据初始化

USE carbonwise_db;

-- 插入示例企业用户
INSERT INTO users (username, email, password_hash, user_type, company_name, credit_code, is_active) VALUES
('lantian', 'lantian@example.com', 'pbkdf2:sha256:600000$example$hash', 'enterprise', '蓝天纺织有限公司', '91330600MA2D8XXXX', TRUE),
('hongxing', 'hongxing@example.com', 'pbkdf2:sha256:600000$example$hash', 'enterprise', '红星织造厂', '91330600MA2D8YYYY', TRUE),
('bank_user', 'bank@example.com', 'pbkdf2:sha256:600000$example$hash', 'bank', '工商银行绿色金融部', NULL, TRUE)
ON DUPLICATE KEY UPDATE id=id;

-- 插入示例设备数据
INSERT INTO equipments (user_id, name, model, quantity, rated_power, daily_hours, load_factor, years_used, process) VALUES
(1, '细纱机', 'FA506', 20, 45.0, 24.0, 0.85, 6, '纺纱'),
(1, '浆纱机', 'GA308', 2, 120.0, 18.0, 0.90, 4, '浆纱'),
(1, '喷气织机', 'ZAX9100', 80, 3.5, 24.0, 0.95, 3, '织造'),
(1, '溢流染色机', 'HTO-500', 6, 90.0, 16.0, 0.80, 5, '印染'),
(1, '空压机', 'GA75', 4, 75.0, 24.0, 0.60, 7, '辅助'),
(2, '环锭纺纱机', 'FA507', 15, 40.0, 22.0, 0.82, 4, '纺纱'),
(2, '剑杆织机', 'GA747', 50, 2.8, 20.0, 0.88, 5, '织造'),
(2, '染色机', 'HTO-300', 4, 75.0, 14.0, 0.75, 6, '印染')
ON DUPLICATE KEY UPDATE id=id;

-- 插入示例核算结果
INSERT INTO calculations (user_id, annual_emission, intensity, env_cost, uncertainty, credit_rating, benchmark, emission_factor_version, carbon_price, annual_output) VALUES
(1, 6826.0, 5.69, 546080.0, 0.34, 'BBB', 5.5, '2024-v1', 80.0, 1200.0),
(2, 4250.0, 4.25, 340000.0, 0.26, 'A', 5.5, '2024-v1', 80.0, 1000.0)
ON DUPLICATE KEY UPDATE id=id;
