<?php
// Disable error display in production
ini_set('display_errors', 0);
error_reporting(E_ALL);

header('Content-Type: application/json');
header('Cache-Control: public, max-age=300'); // Cache for 5 minutes

$host = getenv('DB_HOST');
$dbname = getenv('DB_NAME');
$user = getenv('DB_USER');
$pass = getenv('DB_PASSWORD');

// Validate and sanitize input
$source = isset($_GET['source']) ? filter_var($_GET['source'], FILTER_SANITIZE_STRING) : '';
$valid_sources = ['Cook Islands', 'Fiji', 'Papua New Guinea', 'Solomon Islands'];

if (!$source) {
    http_response_code(400);
    echo json_encode(['error' => 'Source is required']);
    exit;
}

if (!in_array($source, $valid_sources)) {
    http_response_code(400);
    echo json_encode(['error' => 'Invalid source provided']);
    exit;
}

try {
    $pdo = new PDO("mysql:host=$host;dbname=$dbname", $user, $pass);
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
    
    $stmt = $pdo->prepare("
        SELECT 
            DATE(date) as sitting_date,
            new_id,
            title,
            document_type,
            speaker,
            speaker2,
            `order`
        FROM pacific_hansard_db
        WHERE source = ?
        ORDER BY DATE(date) DESC, `order` ASC
    ");
    $stmt->execute([$source]);
    $results = $stmt->fetchAll(PDO::FETCH_ASSOC);

    $hansard_list = [];
    foreach ($results as $row) {
        $date = $row['sitting_date'];
        if (!isset($hansard_list[$date])) {
            $hansard_list[$date] = [
                'sitting_date' => $date,
                'documents' => []
            ];
        }
        $hansard_list[$date]['documents'][] = [
            'new_id' => $row['new_id'],
            'title' => $row['title'],
            'document_type' => $row['document_type'],
            'speakers' => array_filter([$row['speaker'], $row['speaker2']]),
            'order' => $row['order']
        ];
    }

    echo json_encode(array_values($hansard_list));
} catch (PDOException $e) {
    echo json_encode(['error' => "Database error: " . $e->getMessage()]);
}
?>