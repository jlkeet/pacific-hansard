<?php
// Railway deployment configuration
// Using SQLite for simplicity on Railway free tier

$db_path = getenv('RAILWAY_VOLUME_MOUNT_PATH') ?: '/data';
$db_file = $db_path . '/pacific_hansard.db';

// Create directory if it doesn't exist
if (!file_exists($db_path)) {
    mkdir($db_path, 0777, true);
}

// Database connection
try {
    $pdo = new PDO('sqlite:' . $db_file);
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
    
    // Create table if not exists
    $pdo->exec("CREATE TABLE IF NOT EXISTS pacific_hansard_db (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source TEXT,
        file_name TEXT,
        part_number INTEGER,
        date TEXT,
        year INTEGER,
        month TEXT,
        day INTEGER,
        content TEXT,
        speaker TEXT,
        speaker2 TEXT,
        parliament_number INTEGER,
        url TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )");
} catch(PDOException $e) {
    error_log("Database connection failed: " . $e->getMessage());
}

// Solr configuration
$solr_url = "http://localhost:8983/solr/hansard_core";

// For Railway deployment
if (getenv('RAILWAY_ENVIRONMENT')) {
    // Use environment variables if available
    $solr_url = getenv('SOLR_URL') ?: $solr_url;
}
?>