<?php

// CORS headers
header("Access-Control-Allow-Origin: *");
header("Access-Control-Allow-Methods: GET, POST, OPTIONS");
header("Access-Control-Allow-Headers: Content-Type, Authorization");

// Handle preflight requests (OPTIONS)
if ($_SERVER['REQUEST_METHOD'] == 'OPTIONS') {
    // If preflight, exit with success response.
    exit(0);
}

// Set content type
header('Content-Type: application/json');

$host = getenv('DB_HOST');
$dbname = getenv('DB_NAME');
$user = getenv('DB_USER');
$pass = getenv('DB_PASSWORD');

$new_id = isset($_GET['id']) ? $_GET['id'] : '';

if (!$new_id) {
    echo json_encode(['error' => 'Hansard ID is required']);
    exit;
}

try {
    $pdo = new PDO("mysql:host=$host;dbname=$dbname", $user, $pass);
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);

    $stmt = $pdo->prepare("SELECT new_id, title, date, document_type, content, source FROM pacific_hansard_db WHERE new_id = ?");
    $stmt->execute([$new_id]);
    $hansard_details = $stmt->fetch(PDO::FETCH_ASSOC);

    if (!$hansard_details) {
        echo json_encode(['error' => 'Hansard document not found']);
        exit;
    }

    // Convert date to string
    $hansard_details['date'] = date('Y-m-d', strtotime($hansard_details['date']));

    echo json_encode($hansard_details);
} catch(PDOException $e) {
    echo json_encode(['error' => $e->getMessage()]);
}


?>