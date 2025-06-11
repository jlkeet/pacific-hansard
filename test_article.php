<?php
// Test script to check if Fiji hansards contain HTML formatting

error_reporting(E_ALL);
ini_set('display_errors', 1);

// Database connection
$servername = '127.0.0.1';
$port = '3307';
$username = 'hansard_user';
$password = 'test_pass';
$dbname = 'pacific_hansard_db';

try {
    $conn = new mysqli($servername, $username, $password, $dbname, $port);
    
    if ($conn->connect_error) {
        die("Connection failed: " . $conn->connect_error);
    }
    
    echo "Connected successfully to database\n\n";
    
    // Get a sample of Fiji articles
    $sql = "SELECT new_id, title, date, content FROM pacific_hansard_db WHERE source = 'Fiji' ORDER BY date DESC LIMIT 5";
    $result = $conn->query($sql);
    
    if ($result->num_rows > 0) {
        echo "Found " . $result->num_rows . " Fiji articles\n\n";
        
        while ($row = $result->fetch_assoc()) {
            echo "Article ID: " . $row['new_id'] . "\n";
            echo "Title: " . $row['title'] . "\n";
            echo "Date: " . $row['date'] . "\n";
            
            // Check if content contains HTML tags
            $content = $row['content'];
            $hasHTML = false;
            
            if (strpos($content, '<p>') !== false) {
                echo "✓ Contains <p> tags\n";
                $hasHTML = true;
            }
            if (strpos($content, '<h4>') !== false) {
                echo "✓ Contains <h4> tags\n";
                $hasHTML = true;
            }
            if (strpos($content, '<strong>') !== false) {
                echo "✓ Contains <strong> tags\n";
                $hasHTML = true;
            }
            
            if (!$hasHTML) {
                echo "✗ No HTML formatting found - content appears to be plain text\n";
            }
            
            // Show first 500 characters of content
            echo "Content preview:\n";
            echo substr($content, 0, 500) . "...\n";
            echo str_repeat("-", 80) . "\n\n";
        }
    } else {
        echo "No Fiji articles found in the database\n";
    }
    
    $conn->close();
    
} catch (Exception $e) {
    echo "Error: " . $e->getMessage() . "\n";
}
?>