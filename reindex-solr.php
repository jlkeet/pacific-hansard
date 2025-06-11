<?php
// Re-index MySQL data to Solr with speaker fields

$host = getenv('DB_HOST') ?: 'mysql';
$dbname = getenv('DB_NAME') ?: 'pacific_hansard_db';
$username = getenv('DB_USER') ?: 'hansard_user';
$password = getenv('DB_PASSWORD') ?: 'test_pass';
$solr_url = getenv('SOLR_URL') ?: 'http://solr:8983/solr/hansard_core';

echo "Starting re-indexing process...\n";

try {
    // Connect to MySQL
    $pdo = new PDO("mysql:host=$host;dbname=$dbname;charset=utf8", $username, $password);
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
    
    // Get all documents
    $stmt = $pdo->query("SELECT * FROM pacific_hansard_db");
    $documents = $stmt->fetchAll(PDO::FETCH_ASSOC);
    
    echo "Found " . count($documents) . " documents to re-index\n";
    
    // Prepare documents for Solr
    $solr_docs = [];
    foreach ($documents as $doc) {
        $solr_doc = [
            'id' => $doc['id'],
            'title' => $doc['title'],
            'document_type' => $doc['document_type'],
            'date' => $doc['date'] ? $doc['date'] . 'T00:00:00Z' : null,
            'source' => $doc['source'],
            'speaker' => $doc['speaker'],
            'speaker2' => $doc['speaker2'],
            'content' => $doc['content'],
            'created' => $doc['created_at'] ? str_replace(' ', 'T', $doc['created_at']) . 'Z' : null,
            'new_id' => $doc['new_id']
        ];
        
        // Remove null values
        $solr_doc = array_filter($solr_doc, function($value) {
            return $value !== null;
        });
        
        $solr_docs[] = $solr_doc;
    }
    
    // Send to Solr in batches
    $batch_size = 50;
    $total_indexed = 0;
    
    for ($i = 0; $i < count($solr_docs); $i += $batch_size) {
        $batch = array_slice($solr_docs, $i, $batch_size);
        
        // Prepare JSON
        $json_data = json_encode($batch);
        
        // Send to Solr
        $ch = curl_init($solr_url . '/update?commit=true');
        curl_setopt($ch, CURLOPT_POSTFIELDS, $json_data);
        curl_setopt($ch, CURLOPT_HTTPHEADER, ['Content-Type: application/json']);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        
        $response = curl_exec($ch);
        $http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);
        
        if ($http_code == 200) {
            $total_indexed += count($batch);
            echo "Indexed batch " . ($i/$batch_size + 1) . " (" . $total_indexed . " documents)\n";
        } else {
            echo "Error indexing batch: HTTP $http_code\n";
            echo "Response: $response\n";
            break;
        }
    }
    
    echo "\nRe-indexing complete! Indexed $total_indexed documents.\n";
    
    // Verify speaker facets
    echo "\nVerifying speaker facets...\n";
    $ch = curl_init($solr_url . '/select?q=*:*&rows=0&facet=true&facet.field=speaker&facet.field=speaker2&facet.mincount=1');
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    $response = curl_exec($ch);
    curl_close($ch);
    
    $data = json_decode($response, true);
    if (isset($data['facet_counts']['facet_fields'])) {
        $speaker_count = count($data['facet_counts']['facet_fields']['speaker']) / 2;
        $speaker2_count = count($data['facet_counts']['facet_fields']['speaker2']) / 2;
        echo "Found $speaker_count unique speakers in 'speaker' field\n";
        echo "Found $speaker2_count unique speakers in 'speaker2' field\n";
    }
    
} catch (Exception $e) {
    echo "Error: " . $e->getMessage() . "\n";
}
?>