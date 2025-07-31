<?php
// Improved error handling
error_reporting(E_ALL);
ini_set('display_errors', 1);

// Include database configuration
require_once 'config/database.php';

// Get article ID from URL
$article_id = isset($_GET['id']) ? $_GET['id'] : '';

$article = null;
$error_message = null;

// Validate article ID
if (empty($article_id)) {
    $error_message = "Article ID is required";
} else {
    try {
        // Connect to the database using PDO
        $pdo = getDatabaseConnection();
        
        // Get article data
        $sql = "SELECT title, date, document_type, source, content, speaker, speaker2 FROM pacific_hansard_db WHERE new_id = :id";
        $stmt = $pdo->prepare($sql);
        $stmt->execute(['id' => $article_id]);
        
        $article = $stmt->fetch(PDO::FETCH_ASSOC);
        
        if ($article) {
            
            // Format the date
            if (!empty($article['date'])) {
                $date = new DateTime($article['date']);
                $article['formatted_date'] = $date->format('l, F j, Y');
            } else {
                $article['formatted_date'] = "Unknown date";
            }
            
            // Get speakers list
            $article['speakers'] = array_filter([$article['speaker'], $article['speaker2']]);
        } else {
            $error_message = "Article not found";
        }
    } catch (Exception $e) {
        $error_message = "Database error: " . $e->getMessage();
    }
}

/**
 * Format hansard content with proper paragraphs and speaker highlighting
 */
function format_hansard_content($content, $source = '') {
    if (empty($content)) {
        return '<p>No content available</p>';
    }
    
    // Check if content is HTML (for Fiji)
    if ($source === 'Fiji' && strpos($content, '<') !== false) {
        // Content is already formatted HTML, just return it
        return $content;
    }
    
    // Otherwise, format plain text content
    // Split the content into paragraphs
    $paragraphs = preg_split('/\n{2,}/', $content);
    $formatted_content = '';
    
    foreach ($paragraphs as $paragraph) {
        $paragraph = trim($paragraph);
        if (empty($paragraph)) continue;
        
        // Check if this is a speaker line (HON. NAME:)
        $speaker_pattern = '/^(HON\.\s+[A-Z][A-Z\s.]+|MR\.\s+[A-Z][A-Z\s.]+|DR\.\s+[A-Z][A-Z\s.]+|MRS\.\s+[A-Z][A-Z\s.]+|MS\.\s+[A-Z][A-Z\s.]+):\s*(.*)/i';
        
        if (preg_match($speaker_pattern, $paragraph, $matches)) {
            $speaker = $matches[1];
            $dialogue = $matches[2];
            $formatted_content .= '<div class="hansard-speech">';
            $formatted_content .= '<div class="hansard-speaker">' . htmlspecialchars($speaker) . ':</div>';
            $formatted_content .= '<div class="hansard-dialogue">' . htmlspecialchars($dialogue) . '</div>';
            $formatted_content .= '</div>';
        } 
        // Check if this is a procedural line (all caps)
        else if (strtoupper($paragraph) === $paragraph && strlen($paragraph) > 10) {
            $formatted_content .= '<div class="hansard-procedural">' . htmlspecialchars($paragraph) . '</div>';
        }
        // Regular paragraph
        else {
            $formatted_content .= '<p class="hansard-paragraph">' . htmlspecialchars($paragraph) . '</p>';
        }
    }
    
    return $formatted_content;
}

?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title><?php echo $article ? htmlspecialchars($article['title']) : 'Article Not Found'; ?> - Pacific Hansard</title>
    <link rel="icon" href="favicon.png" type="image/x-icon">
    <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.4.1/css/bootstrap.min.css">
    <link href="https://maxcdn.bootstrapcdn.com/font-awesome/4.7.0/css/font-awesome.min.css" rel="stylesheet">
    <link rel="stylesheet" href="style.css">
    <style>
        .article-container {
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }
        .article-header {
            margin-bottom: 30px;
            border-bottom: 1px solid #eee;
            padding-bottom: 20px;
        }
        .article-title {
            font-size: 2rem;
            margin-bottom: 15px;
        }
        .article-metadata {
            color: #666;
            margin-bottom: 10px;
            font-size: 0.9rem;
        }
        .article-metadata i {
            width: 20px;
            text-align: center;
            margin-right: 5px;
        }
        .article-content {
            line-height: 1.6;
            margin-top: 30px;
        }
        .hansard-speech {
            margin-bottom: 15px;
            padding-left: 15px;
        }
        .hansard-speaker {
            font-weight: bold;
            color: #333;
            display: inline;
        }
        .hansard-dialogue {
            display: inline;
            margin-left: 5px;
        }
        .hansard-procedural {
            font-weight: bold;
            margin: 20px 0;
            text-align: center;
            font-style: italic;
        }
        .hansard-paragraph {
            margin-bottom: 15px;
        }
        .back-button {
            margin-bottom: 20px;
        }
        /* Styles for Fiji formatted content */
        .article-content h3 {
            margin-top: 30px;
            margin-bottom: 20px;
            color: #333;
            font-size: 1.8rem;
        }
        .article-content h4 {
            margin-top: 25px;
            margin-bottom: 15px;
            color: #555;
            font-size: 1.3rem;
            font-weight: 600;
        }
        .article-content p {
            margin-bottom: 18px;
            text-align: justify;
            line-height: 1.8;
        }
        .article-content p strong {
            color: #333;
        }
        /* Page markers */
        .article-content div a[name] {
            display: block;
            margin: 30px 0;
            text-align: center;
            color: #999;
            font-size: 0.9rem;
            font-style: italic;
        }
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-light">
        <a class="navbar-brand" href="index.html"><img src="tkb.png" alt="The Knowledge Basket" /></a>
        <button class="navbar-toggler" type="button" data-toggle="collapse" data-target="#navbarSupportedContent">
            <span class="navbar-toggler-icon"></span>
        </button>
        <div class="collapse navbar-collapse" id="navbarSupportedContent">
            <ul class="navbar-nav mr-auto">
                <li class="nav-item">
                    <a class="nav-link" href="index.html">Home</a>
                </li>
                <li class="nav-item">
                    <a class="nav-link" href="hansard-browser.html">Browse</a>
                </li>
            </ul>
        </div>
    </nav>

    <div class="container article-container">
        <div class="back-button">
            <a href="javascript:history.back()" class="btn btn-outline-secondary btn-sm">
                <i class="fa fa-arrow-left"></i> Back to search results
            </a>
        </div>

        <?php if ($error_message): ?>
            <div class="alert alert-danger">
                <h4>Error</h4>
                <p><?php echo htmlspecialchars($error_message); ?></p>
                <a href="index.html" class="btn btn-primary">Return to search</a>
            </div>
        <?php elseif ($article): ?>
            <div class="article-header">
                <h1 class="article-title"><?php echo htmlspecialchars($article['title']); ?></h1>
                
                <div class="article-metadata">
                    <p><i class="fa fa-calendar"></i> <?php echo htmlspecialchars($article['formatted_date']); ?></p>
                    <p><i class="fa fa-bookmark"></i> <?php echo htmlspecialchars($article['document_type']); ?></p>
                    <p><i class="fa fa-globe"></i> <?php echo htmlspecialchars($article['source']); ?></p>
                    
                    <?php if (!empty($article['speakers'])): ?>
                    <p>
                        <i class="fa fa-microphone"></i> 
                        <strong>Speakers:</strong> 
                        <?php echo htmlspecialchars(implode(', ', $article['speakers'])); ?>
                    </p>
                    <?php endif; ?>
                </div>
            </div>

            <div class="article-content">
                <?php echo format_hansard_content($article['content'], $article['source']); ?>
            </div>
        <?php endif; ?>
    </div>

    <script src="https://code.jquery.com/jquery-3.4.1.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/popper.js@1.16.0/dist/umd/popper.min.js"></script>
    <script src="https://stackpath.bootstrapcdn.com/bootstrap/4.4.1/js/bootstrap.min.js"></script>
</body>
</html>