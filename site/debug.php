<?php
// Display all errors
ini_set('display_errors', 1);
ini_set('display_startup_errors', 1);
error_reporting(E_ALL);

echo "<h1>Railway Debug Info</h1>";

echo "<h2>Environment Variables:</h2>";
echo "<pre>";
echo "PORT: " . getenv('PORT') . "\n";
echo "DB_HOST: " . getenv('DB_HOST') . "\n";
echo "DB_NAME: " . getenv('DB_NAME') . "\n";
echo "DB_USER: " . getenv('DB_USER') . "\n";
echo "DB_PASSWORD: " . (getenv('DB_PASSWORD') ? '[SET]' : '[NOT SET]') . "\n";
echo "SOLR_URL: " . getenv('SOLR_URL') . "\n";
echo "</pre>";

echo "<h2>Database Connection Test:</h2>";
try {
    $host = getenv('DB_HOST') ?: 'mysql';
    $dbname = getenv('DB_NAME') ?: 'pacific_hansard_db';
    $username = getenv('DB_USER') ?: 'hansard_user';
    $password = getenv('DB_PASSWORD') ?: 'test_pass';
    
    $pdo = new PDO("mysql:host=$host;dbname=$dbname;charset=utf8", $username, $password);
    echo "<p style='color:green'>✓ Database connection successful!</p>";
} catch (PDOException $e) {
    echo "<p style='color:red'>✗ Database connection failed: " . $e->getMessage() . "</p>";
}

echo "<h2>PHP Info:</h2>";
phpinfo();
?>