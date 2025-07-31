<?php
// Railway database configuration

// Check if we have a MySQL URL (Railway format)
$mysqlUrl = getenv('MYSQL_URL');

if ($mysqlUrl) {
    // Parse the MySQL URL
    // Format: mysql://user:password@host:port/database
    $url = parse_url($mysqlUrl);
    
    $DB_HOST = $url['host'];
    $DB_PORT = $url['port'] ?? 3306;
    $DB_NAME = ltrim($url['path'], '/');
    $DB_USER = $url['user'];
    $DB_PASSWORD = $url['pass'];
} else {
    // Fallback to individual environment variables
    $DB_HOST = getenv('DB_HOST') ?: getenv('MYSQLHOST') ?: 'mysql';
    $DB_PORT = getenv('DB_PORT') ?: getenv('MYSQLPORT') ?: 3306;
    $DB_NAME = getenv('DB_NAME') ?: getenv('MYSQLDATABASE') ?: 'pacific_hansard_db';
    $DB_USER = getenv('DB_USER') ?: getenv('MYSQLUSER') ?: 'hansard_user';
    $DB_PASSWORD = getenv('DB_PASSWORD') ?: getenv('MYSQLPASSWORD') ?: 'test_pass';
}

// Create PDO connection
function getDatabaseConnection() {
    global $DB_HOST, $DB_PORT, $DB_NAME, $DB_USER, $DB_PASSWORD;
    
    try {
        $dsn = "mysql:host=$DB_HOST;port=$DB_PORT;dbname=$DB_NAME;charset=utf8mb4";
        $pdo = new PDO($dsn, $DB_USER, $DB_PASSWORD);
        $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
        return $pdo;
    } catch (PDOException $e) {
        throw new Exception("Database connection failed: " . $e->getMessage());
    }
}
?>