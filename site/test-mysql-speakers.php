<?php
header('Content-Type: text/plain');

// Database configuration
$host = getenv('DB_HOST') ?: 'mysql';
$dbname = getenv('DB_NAME') ?: 'pacific_hansard_db';
$username = getenv('DB_USER') ?: 'hansard_user';
$password = getenv('DB_PASSWORD') ?: 'test_pass';

try {
    $pdo = new PDO("mysql:host=$host;dbname=$dbname;charset=utf8", $username, $password);
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
    
    echo "Connected to database successfully\n\n";
    
    // Check total documents
    $stmt = $pdo->query("SELECT COUNT(*) as total FROM pacific_hansard_db");
    $total = $stmt->fetch(PDO::FETCH_ASSOC);
    echo "Total documents in MySQL: " . $total['total'] . "\n\n";
    
    // Check documents with speakers
    $stmt = $pdo->query("SELECT COUNT(*) as with_speakers FROM pacific_hansard_db WHERE speaker IS NOT NULL AND speaker != '' AND speaker != 'No speakers identified'");
    $withSpeakers = $stmt->fetch(PDO::FETCH_ASSOC);
    echo "Documents with speakers: " . $withSpeakers['with_speakers'] . "\n\n";
    
    // Get sample speakers
    $stmt = $pdo->query("SELECT DISTINCT speaker FROM pacific_hansard_db WHERE speaker IS NOT NULL AND speaker != '' AND speaker != 'No speakers identified' LIMIT 10");
    $sampleSpeakers = $stmt->fetchAll(PDO::FETCH_COLUMN);
    echo "Sample speakers:\n";
    foreach ($sampleSpeakers as $speaker) {
        echo "  - $speaker\n";
    }
    
    // Get a sample document with speaker
    echo "\nSample document with speaker:\n";
    $stmt = $pdo->query("SELECT title, speaker, speaker2, date FROM pacific_hansard_db WHERE speaker IS NOT NULL AND speaker != '' AND speaker != 'No speakers identified' LIMIT 1");
    $sample = $stmt->fetch(PDO::FETCH_ASSOC);
    print_r($sample);
    
} catch (PDOException $e) {
    echo "Database error: " . $e->getMessage();
}
?>