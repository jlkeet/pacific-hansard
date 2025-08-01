<?php
// Check Solr indexing status
header('Content-Type: text/plain');

echo "=== Solr Indexing Diagnostic ===\n\n";

// Check environment variables
echo "Environment Variables:\n";
echo "SOLR_URL: " . getenv('SOLR_URL') . "\n";
echo "DB_HOST: " . getenv('DB_HOST') . "\n\n";

// Check MySQL connection and documents
require_once 'config/database.php';
try {
    $pdo = getDatabaseConnection();
    
    // Count documents in MySQL
    $stmt = $pdo->query("SELECT COUNT(*) as count FROM pacific_hansard_db");
    $result = $stmt->fetch(PDO::FETCH_ASSOC);
    echo "Documents in MySQL: " . $result['count'] . "\n\n";
    
    // Check indexed_files table
    $stmt = $pdo->query("SHOW TABLES LIKE 'indexed_files'");
    if ($stmt->fetch()) {
        $stmt = $pdo->query("SELECT COUNT(*) as count FROM indexed_files");
        $result = $stmt->fetch(PDO::FETCH_ASSOC);
        echo "Files tracked in indexed_files: " . $result['count'] . "\n";
        
        // Show last 5 indexed files
        $stmt = $pdo->query("SELECT file_path, indexed_at FROM indexed_files ORDER BY indexed_at DESC LIMIT 5");
        echo "\nLast 5 indexed files:\n";
        while ($row = $stmt->fetch(PDO::FETCH_ASSOC)) {
            echo "- " . basename($row['file_path']) . " at " . $row['indexed_at'] . "\n";
        }
    } else {
        echo "indexed_files table does NOT exist\n";
    }
} catch (Exception $e) {
    echo "Database error: " . $e->getMessage() . "\n";
}

// Check Solr connection and documents
echo "\n=== Solr Status ===\n";
$solrUrl = getenv('SOLR_URL') ?: 'http://localhost:8983/solr/hansard_core';
echo "Solr URL: " . $solrUrl . "\n";

// Test Solr connection
$ch = curl_init($solrUrl . '/admin/ping');
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
curl_setopt($ch, CURLOPT_TIMEOUT, 5);
$response = curl_exec($ch);
$httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
curl_close($ch);

if ($httpCode == 200) {
    echo "Solr connection: OK\n";
    
    // Count documents in Solr
    $ch = curl_init($solrUrl . '/select?q=*:*&rows=0&wt=json');
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    $response = curl_exec($ch);
    $data = json_decode($response, true);
    
    if (isset($data['response']['numFound'])) {
        echo "Documents in Solr: " . $data['response']['numFound'] . "\n";
        
        if ($data['response']['numFound'] == 0) {
            echo "\n⚠️  WARNING: Solr has 0 documents but MySQL has documents!\n";
            echo "This suggests the Solr indexing is failing.\n";
        }
    }
} else {
    echo "Solr connection: FAILED (HTTP $httpCode)\n";
}

// Check indexing log
echo "\n=== Indexing Log ===\n";
$logFile = '/var/log/indexing.log';
if (file_exists($logFile)) {
    echo "Last 50 lines of indexing log:\n";
    echo "=====================================\n";
    $lines = explode("\n", file_get_contents($logFile));
    $lastLines = array_slice($lines, -50);
    echo implode("\n", $lastLines);
} else {
    echo "No indexing log found at: $logFile\n";
    echo "This suggests the indexing script hasn't run yet.\n";
}
?>