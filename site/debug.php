<?php
// Display all errors
ini_set('display_errors', 1);
ini_set('display_startup_errors', 1);
error_reporting(E_ALL);

echo "<h1>Railway Debug Info</h1>";

echo "<h2>Environment Variables:</h2>";
echo "<pre>";
echo "PORT: " . getenv('PORT') . "\n";
echo "MYSQL_URL: " . (getenv('MYSQL_URL') ? '[SET]' : '[NOT SET]') . "\n";
echo "DB_HOST: " . getenv('DB_HOST') . "\n";
echo "DB_NAME: " . getenv('DB_NAME') . "\n";
echo "DB_USER: " . getenv('DB_USER') . "\n";
echo "DB_PASSWORD: " . (getenv('DB_PASSWORD') ? '[SET]' : '[NOT SET]') . "\n";
echo "SOLR_URL: " . getenv('SOLR_URL') . "\n";

// Parse MySQL URL if present
if ($mysqlUrl = getenv('MYSQL_URL')) {
    echo "\nParsed MySQL URL:\n";
    $url = parse_url($mysqlUrl);
    echo "  Host: " . $url['host'] . "\n";
    echo "  Port: " . ($url['port'] ?? 3306) . "\n";
    echo "  Database: " . ltrim($url['path'], '/') . "\n";
    echo "  User: " . $url['user'] . "\n";
}
echo "</pre>";

echo "<h2>Database Connection Test:</h2>";
try {
    require_once 'config/database.php';
    $pdo = getDatabaseConnection();
    echo "<p style='color:green'>✓ Database connection successful!</p>";
    
    // Test query
    $stmt = $pdo->query("SELECT COUNT(*) as count FROM pacific_hansard_db");
    $result = $stmt->fetch(PDO::FETCH_ASSOC);
    echo "<p>Records in database: " . $result['count'] . "</p>";
} catch (Exception $e) {
    echo "<p style='color:red'>✗ Database connection failed: " . $e->getMessage() . "</p>";
}

echo "<h2>PHP Info:</h2>";
phpinfo();
?>