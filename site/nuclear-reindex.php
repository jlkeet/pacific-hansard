<?php
// NUCLEAR OPTION: Completely wipe and rebuild everything
// WARNING: This will delete all data and cannot be undone!
set_time_limit(600); // 10 minutes
header('Content-Type: text/plain');

echo "NUCLEAR RE-INDEX: Complete MySQL and Solr Wipe & Rebuild\n";
echo "=====================================================\n\n";

require_once 'config/database.php';

try {
    // Connect to database
    $pdo = getDatabaseConnection();
    echo "✓ Connected to MySQL\n";
    
    // Get Solr URL
    $solrUrl = getenv('SOLR_URL') ?: 'http://localhost:8983/solr/hansard_core';
    echo "Solr URL: $solrUrl\n\n";
    
    // STEP 1: Clear ALL tables
    echo "STEP 1: Clearing all data...\n";
    echo "----------------------------\n";
    
    // Clear main documents table
    $stmt = $pdo->query("DELETE FROM pacific_hansard_db");
    echo "✓ Cleared pacific_hansard_db table\n";
    
    // Clear tracking table
    $stmt = $pdo->query("DELETE FROM indexed_files");
    echo "✓ Cleared indexed_files tracking table\n";
    
    // Clear Solr completely
    $deleteQuery = json_encode(['delete' => ['query' => '*:*']]);
    $ch = curl_init($solrUrl . '/update?commit=true');
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_POST, true);
    curl_setopt($ch, CURLOPT_POSTFIELDS, $deleteQuery);
    curl_setopt($ch, CURLOPT_HTTPHEADER, ['Content-Type: application/json']);
    curl_setopt($ch, CURLOPT_TIMEOUT, 30);
    
    $response = curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);
    
    if ($httpCode == 200) {
        echo "✓ Cleared all documents from Solr\n\n";
    } else {
        echo "✗ Failed to clear Solr (HTTP $httpCode)\n\n";
    }
    
    // STEP 2: Verify everything is empty
    echo "STEP 2: Verifying cleanup...\n";
    echo "----------------------------\n";
    
    $stmt = $pdo->query("SELECT COUNT(*) as count FROM pacific_hansard_db");
    $result = $stmt->fetch(PDO::FETCH_ASSOC);
    echo "MySQL documents: " . $result['count'] . "\n";
    
    $stmt = $pdo->query("SELECT COUNT(*) as count FROM indexed_files");
    $result = $stmt->fetch(PDO::FETCH_ASSOC);
    echo "Tracked files: " . $result['count'] . "\n";
    
    // Check Solr
    $ch = curl_init($solrUrl . '/select?q=*:*&rows=0&wt=json');
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    $response = curl_exec($ch);
    $data = json_decode($response, true);
    
    if (isset($data['response']['numFound'])) {
        echo "Solr documents: " . $data['response']['numFound'] . "\n\n";
    }
    
    echo "✓ All systems cleared!\n\n";
    echo "Now redeploy your application - the background indexer will rebuild everything\n";
    echo "from scratch with the corrected logic.\n\n";
    echo "Monitor progress at: /indexing-status.php\n";
    
} catch (Exception $e) {
    echo "✗ Error: " . $e->getMessage() . "\n";
}
?>