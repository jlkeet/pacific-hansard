<?php
// Check indexing status
header('Content-Type: text/plain');

echo "=== Indexing Status Check ===\n\n";

// Check if indexing log exists
$logFile = '/var/log/indexing.log';
if (file_exists($logFile)) {
    echo "Indexing log found. Last 100 lines:\n";
    echo "=====================================\n";
    $lines = explode("\n", file_get_contents($logFile));
    $lastLines = array_slice($lines, -100);
    echo implode("\n", $lastLines);
} else {
    echo "No indexing log found at: $logFile\n";
}

echo "\n\n=== Checking indexed_files table ===\n";
try {
    require_once 'config/database.php';
    $pdo = getDatabaseConnection();
    
    // Check if indexed_files table exists
    $stmt = $pdo->query("SHOW TABLES LIKE 'indexed_files'");
    if ($stmt->fetch()) {
        echo "indexed_files table exists\n";
        
        // Count indexed files
        $stmt = $pdo->query("SELECT COUNT(*) as count FROM indexed_files");
        $result = $stmt->fetch(PDO::FETCH_ASSOC);
        echo "Total indexed files: " . $result['count'] . "\n";
        
        // Show last 5 indexed files
        $stmt = $pdo->query("SELECT file_path, indexed_at FROM indexed_files ORDER BY indexed_at DESC LIMIT 5");
        echo "\nLast 5 indexed files:\n";
        while ($row = $stmt->fetch(PDO::FETCH_ASSOC)) {
            echo "- " . $row['file_path'] . " (indexed at: " . $row['indexed_at'] . ")\n";
        }
    } else {
        echo "indexed_files table does NOT exist\n";
    }
    
    // Check total documents in main table
    $stmt = $pdo->query("SELECT COUNT(*) as count FROM pacific_hansard_db");
    $result = $stmt->fetch(PDO::FETCH_ASSOC);
    echo "\nTotal documents in pacific_hansard_db: " . $result['count'] . "\n";
    
} catch (Exception $e) {
    echo "Database error: " . $e->getMessage() . "\n";
}

// Check if Python is running
echo "\n\n=== Python Process Check ===\n";
$output = shell_exec('ps aux | grep python');
echo $output;

// Check collections directory
echo "\n\n=== Collections Directory Check ===\n";
if (is_dir('/app/collections')) {
    echo "Collections directory exists at /app/collections\n";
    $count = shell_exec('find /app/collections -name "*.html" | wc -l');
    echo "Total HTML files: " . trim($count) . "\n";
} else {
    echo "Collections directory NOT found at /app/collections\n";
}

// Check Solr
echo "\n\n=== Solr Status ===\n";
$solrUrl = getenv('SOLR_URL') ?: 'http://localhost:8983/solr/hansard_core';
$ch = curl_init($solrUrl . '/select?q=*:*&rows=0');
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
curl_setopt($ch, CURLOPT_TIMEOUT, 5);
$response = curl_exec($ch);
$httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);

if ($httpCode == 200) {
    $data = json_decode($response, true);
    echo "Solr is accessible\n";
    echo "Documents in Solr: " . $data['response']['numFound'] . "\n";
} else {
    echo "Solr connection failed (HTTP $httpCode)\n";
}
curl_close($ch);
?>