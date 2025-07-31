<?php
// Re-index MySQL documents to Solr
set_time_limit(300); // 5 minutes
header('Content-Type: text/plain');

echo "Re-indexing MySQL documents to Solr\n";
echo "===================================\n\n";

require_once 'config/database.php';

try {
    // Connect to database
    $pdo = getDatabaseConnection();
    echo "✓ Connected to MySQL\n";
    
    // Get Solr URL
    $solrUrl = getenv('SOLR_URL') ?: 'http://localhost:8983/solr/hansard_core';
    echo "Solr URL: $solrUrl\n\n";
    
    // Test Solr connection
    $ch = curl_init($solrUrl . '/admin/ping');
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, 5);
    $response = curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);
    
    if ($httpCode != 200) {
        die("✗ Cannot connect to Solr (HTTP $httpCode)\n");
    }
    echo "✓ Solr is accessible\n\n";
    
    // Fetch all documents
    echo "Fetching documents from MySQL...\n";
    $stmt = $pdo->query("SELECT new_id, title, date, document_type, source, content, speaker, speaker2 FROM pacific_hansard_db");
    
    $documents = [];
    while ($row = $stmt->fetch(PDO::FETCH_ASSOC)) {
        $doc = [
            'id' => $row['new_id'],
            'new_id' => $row['new_id'],
            'title' => $row['title'],
            'date' => $row['date'] ? $row['date'] . 'T00:00:00Z' : '2010-01-01T00:00:00Z',
            'document_type' => $row['document_type'],
            'source' => $row['source'],
            'content' => $row['content'],
            'speaker' => $row['speaker'],
            'speaker2' => $row['speaker2']
        ];
        $documents[] = $doc;
    }
    
    echo "Found " . count($documents) . " documents\n\n";
    
    // Index in batches
    $batchSize = 50;
    $totalIndexed = 0;
    
    for ($i = 0; $i < count($documents); $i += $batchSize) {
        $batch = array_slice($documents, $i, $batchSize);
        
        // Prepare Solr update
        $updateData = json_encode($batch);
        
        // Send to Solr
        $ch = curl_init($solrUrl . '/update/json?commit=true');
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_POST, true);
        curl_setopt($ch, CURLOPT_POSTFIELDS, $updateData);
        curl_setopt($ch, CURLOPT_HTTPHEADER, ['Content-Type: application/json']);
        curl_setopt($ch, CURLOPT_TIMEOUT, 30);
        
        $response = curl_exec($ch);
        $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        $error = curl_error($ch);
        curl_close($ch);
        
        if ($error) {
            echo "Error in batch " . ($i/$batchSize + 1) . ": $error\n";
        } elseif ($httpCode != 200) {
            echo "Error in batch " . ($i/$batchSize + 1) . ": HTTP $httpCode\n";
            echo "Response: " . substr($response, 0, 500) . "\n";
        } else {
            $totalIndexed += count($batch);
            echo "Indexed $totalIndexed/" . count($documents) . " documents...\n";
        }
        
        // Small delay between batches
        usleep(100000); // 0.1 second
    }
    
    echo "\n✓ Indexing complete! $totalIndexed documents sent to Solr\n\n";
    
    // Verify
    echo "Verifying Solr index...\n";
    $ch = curl_init($solrUrl . '/select?q=*:*&rows=0&wt=json');
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    $response = curl_exec($ch);
    $data = json_decode($response, true);
    
    if (isset($data['response']['numFound'])) {
        echo "✓ Solr now contains " . $data['response']['numFound'] . " documents\n";
    } else {
        echo "Could not verify Solr document count\n";
    }
    
} catch (Exception $e) {
    echo "✗ Error: " . $e->getMessage() . "\n";
}
?>