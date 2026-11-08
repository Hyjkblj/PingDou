CREATE DATABASE IF NOT EXISTS pingdou
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_0900_ai_ci;

CREATE USER IF NOT EXISTS 'pingdou'@'localhost' IDENTIFIED BY 'pingdou_dev';
ALTER USER 'pingdou'@'localhost' IDENTIFIED BY 'pingdou_dev';
GRANT ALL PRIVILEGES ON pingdou.* TO 'pingdou'@'localhost';

CREATE USER IF NOT EXISTS 'pingdou'@'%' IDENTIFIED BY 'pingdou_dev';
ALTER USER 'pingdou'@'%' IDENTIFIED BY 'pingdou_dev';
GRANT ALL PRIVILEGES ON pingdou.* TO 'pingdou'@'%';
