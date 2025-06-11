<?php
// Analyze Fiji hansard HTML structure
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
    
    // Get a Fiji article with the most content
    $sql = "SELECT new_id, title, date, content FROM pacific_hansard_db WHERE source = 'Fiji' AND LENGTH(content) > 10000 ORDER BY LENGTH(content) DESC LIMIT 1";
    $result = $conn->query($sql);
    
    if ($result->num_rows > 0) {
        $row = $result->fetch_assoc();
        echo "=== ANALYZING FIJI HANSARD ===\n";
        echo "Article ID: " . $row['new_id'] . "\n";
        echo "Title: " . $row['title'] . "\n";
        echo "Date: " . $row['date'] . "\n";
        echo "Content Length: " . strlen($row['content']) . " characters\n\n";
        
        // Analyze HTML structure
        $content = $row['content'];
        
        // Count different HTML tags
        echo "=== HTML TAG ANALYSIS ===\n";
        $tags = ['<p>', '<h3>', '<h4>', '<strong>', '<br>', '<br/>', '<div>', '<span>'];
        foreach ($tags as $tag) {
            $count = substr_count($content, $tag);
            if ($count > 0) {
                echo "$tag tags: $count\n";
            }
        }
        
        echo "\n=== FIRST 2000 CHARACTERS OF CONTENT ===\n";
        echo substr($content, 0, 2000) . "...\n";
        
        // Find a section with dialogue
        echo "\n=== LOOKING FOR DIALOGUE SECTIONS ===\n";
        if (preg_match('/<p><strong>HON\..+?<\/strong>.+?<\/p>/s', $content, $matches)) {
            echo "Found dialogue section:\n";
            echo $matches[0] . "\n";
        }
        
        // Check for sections without proper paragraph breaks
        echo "\n=== CHECKING FOR LONG PARAGRAPHS ===\n";
        preg_match_all('/<p>(.+?)<\/p>/s', $content, $paragraphs);
        $long_paragraphs = 0;
        foreach ($paragraphs[1] as $i => $para) {
            if (strlen($para) > 1000) {
                $long_paragraphs++;
                echo "Paragraph " . ($i + 1) . " is " . strlen($para) . " characters long\n";
                if ($long_paragraphs <= 3) {
                    echo "Preview: " . substr(strip_tags($para), 0, 200) . "...\n\n";
                }
            }
        }
        
        // Check for missing speaker formatting
        echo "\n=== CHECKING FOR SPEAKER PATTERNS ===\n";
        // Look for patterns like "HON. NAME:" that might not be properly formatted
        preg_match_all('/(?<![<>])(HON\.\s+[A-Z][A-Z\s.]+):/i', $content, $unformatted_speakers);
        if (count($unformatted_speakers[0]) > 0) {
            echo "Found " . count($unformatted_speakers[0]) . " potentially unformatted speaker lines\n";
            foreach (array_slice($unformatted_speakers[0], 0, 5) as $speaker) {
                echo "- $speaker\n";
            }
        }
        
    } else {
        echo "No Fiji articles found with substantial content\n";
    }
    
    $conn->close();
    
} catch (Exception $e) {
    echo "Error: " . $e->getMessage() . "\n";
}
?>