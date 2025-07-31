<?php
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

// Include database configuration
require_once '../config/database.php';

try {
    $pdo = getDatabaseConnection();
    
    // Get search query
    $query = $_GET['q'] ?? '';
    $source = $_GET['source'] ?? '';
    
    // Build SQL query
    $sql = "SELECT DISTINCT speaker FROM pacific_hansard_db 
            WHERE speaker IS NOT NULL 
            AND speaker != ''
            AND speaker != 'No speakers identified'";
    
    $params = [];
    
    if (!empty($query)) {
        $sql .= " AND speaker LIKE :query";
        $params['query'] = "%$query%";
    }
    
    if (!empty($source)) {
        $sql .= " AND source = :source";
        $params['source'] = $source;
    }
    
    $sql .= " ORDER BY speaker LIMIT 100";
    
    $stmt = $pdo->prepare($sql);
    $stmt->execute($params);
    $speakers = $stmt->fetchAll(PDO::FETCH_COLUMN);
    
    // Also get speaker2 if exists
    $sql2 = str_replace('speaker', 'speaker2', $sql);
    $stmt2 = $pdo->prepare($sql2);
    $stmt2->execute($params);
    $speakers2 = $stmt2->fetchAll(PDO::FETCH_COLUMN);
    
    // Combine and remove duplicates
    $allSpeakers = array_unique(array_merge($speakers, $speakers2));
    sort($allSpeakers);
    
    // Format response
    $response = [
        'speakers' => array_values($allSpeakers),
        'count' => count($allSpeakers),
        'debug' => [
            'speaker_count' => count($speakers),
            'speaker2_count' => count($speakers2),
            'host' => $host,
            'database' => $dbname
        ]
    ];
    
    echo json_encode($response);
    
} catch (PDOException $e) {
    http_response_code(500);
    echo json_encode(['error' => 'Database error: ' . $e->getMessage()]);
}
?>