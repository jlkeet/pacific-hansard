<?php
header('Content-Type: text/plain');

echo "Testing Database Connection\n";
echo "===========================\n\n";

// Database configuration
$host = getenv('DB_HOST') ?: 'mysql';
$dbname = getenv('DB_NAME') ?: 'pacific_hansard_db';
$username = getenv('DB_USER') ?: 'hansard_user';
$password = getenv('DB_PASSWORD') ?: 'test_pass';

echo "Configuration:\n";
echo "Host: $host\n";
echo "Database: $dbname\n";
echo "Username: $username\n\n";

try {
    $pdo = new PDO("mysql:host=$host;dbname=$dbname;charset=utf8", $username, $password);
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
    
    echo "✓ Connected successfully!\n\n";
    
    // Check tables
    echo "Tables in database:\n";
    $stmt = $pdo->query("SHOW TABLES");
    while ($row = $stmt->fetch(PDO::FETCH_NUM)) {
        echo "- " . $row[0] . "\n";
    }
    
    // Check pacific_hansard_db table structure
    echo "\nTable structure for pacific_hansard_db:\n";
    $stmt = $pdo->query("DESCRIBE pacific_hansard_db");
    while ($row = $stmt->fetch(PDO::FETCH_ASSOC)) {
        echo sprintf("- %-20s %s\n", $row['Field'], $row['Type']);
    }
    
    // Count records
    echo "\nRecord counts:\n";
    $stmt = $pdo->query("SELECT COUNT(*) as total FROM pacific_hansard_db");
    $total = $stmt->fetch(PDO::FETCH_ASSOC)['total'];
    echo "Total records: $total\n";
    
    // Count by source
    $stmt = $pdo->query("SELECT source, COUNT(*) as count FROM pacific_hansard_db GROUP BY source");
    echo "\nRecords by source:\n";
    while ($row = $stmt->fetch(PDO::FETCH_ASSOC)) {
        echo "- " . $row['source'] . ": " . $row['count'] . "\n";
    }
    
    // Sample speakers
    echo "\nSample speakers:\n";
    $stmt = $pdo->query("SELECT DISTINCT speaker FROM pacific_hansard_db WHERE speaker IS NOT NULL AND speaker != '' LIMIT 10");
    while ($row = $stmt->fetch(PDO::FETCH_NUM)) {
        echo "- " . $row[0] . "\n";
    }
    
} catch (PDOException $e) {
    echo "✗ Connection failed: " . $e->getMessage() . "\n";
}
?>