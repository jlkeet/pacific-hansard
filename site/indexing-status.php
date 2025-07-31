<?php
require_once 'config/database.php';

echo "<h1>Indexing Status</h1>";
echo "<p>Page refreshes every 5 seconds...</p>";
echo "<meta http-equiv='refresh' content='5'>";

try {
    $pdo = getDatabaseConnection();
    
    // Check if tables exist
    $stmt = $pdo->query("SHOW TABLES");
    $tables = $stmt->fetchAll(PDO::FETCH_COLUMN);
    
    echo "<h2>Database Status:</h2>";
    echo "<p>Connected to database: " . $pdo->query("SELECT DATABASE()")->fetchColumn() . "</p>";
    echo "<p>Tables: " . (empty($tables) ? "None yet" : implode(', ', $tables)) . "</p>";
    
    if (in_array('pacific_hansard_db', $tables)) {
        // Count records
        $stmt = $pdo->query("SELECT COUNT(*) as total, source, COUNT(DISTINCT speaker) as speakers FROM pacific_hansard_db GROUP BY source");
        $results = $stmt->fetchAll(PDO::FETCH_ASSOC);
        
        echo "<h2>Documents Indexed:</h2>";
        echo "<table border='1' cellpadding='5'>";
        echo "<tr><th>Source</th><th>Documents</th><th>Unique Speakers</th></tr>";
        
        $total = 0;
        foreach ($results as $row) {
            echo "<tr>";
            echo "<td>" . htmlspecialchars($row['source']) . "</td>";
            echo "<td>" . $row['total'] . "</td>";
            echo "<td>" . $row['speakers'] . "</td>";
            echo "</tr>";
            $total += $row['total'];
        }
        echo "<tr><th>TOTAL</th><th>$total</th><th>-</th></tr>";
        echo "</table>";
    } else {
        echo "<p style='color:orange'>⚠️ Waiting for indexing to start...</p>";
    }
    
    // Check Solr
    echo "<h2>Solr Status:</h2>";
    $solrUrl = getenv('SOLR_URL') ?: 'http://localhost:8983/solr/hansard_core';
    $ch = curl_init($solrUrl . '/select?q=*:*&rows=0&wt=json');
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, 5);
    $response = curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);
    
    if ($httpCode == 200) {
        $data = json_decode($response, true);
        $numFound = $data['response']['numFound'] ?? 0;
        echo "<p>Documents in Solr: <strong>$numFound</strong></p>";
        
        if ($numFound > 0) {
            echo "<p style='color:green'>✓ Search is ready! <a href='/'>Go to search page</a></p>";
        }
    } else {
        echo "<p style='color:red'>✗ Could not connect to Solr</p>";
    }
    
} catch (Exception $e) {
    echo "<p style='color:red'>Error: " . $e->getMessage() . "</p>";
}

// Check if indexing log exists
if (file_exists('/var/log/indexing.log')) {
    echo "<h2>Recent Indexing Activity:</h2>";
    echo "<pre style='background:#f5f5f5; padding:10px; max-height:200px; overflow:auto;'>";
    echo htmlspecialchars(shell_exec('tail -20 /var/log/indexing.log'));
    echo "</pre>";
}
?>

<p><a href="/debug.php">Debug Info</a> | <a href="/">Search Page</a></p>