<?php
// error_reporting(E_ALL);
// ini_set('display_errors', 1);
// header('Content-Type: application/json');

// $servername = getenv('DB_HOST') ?: 'mysql';
// $username = getenv('DB_USER') ?: 'root';
// $password = getenv('DB_PASSWORD') ?: 'Wh1t3sh33ts';
// $dbname = getenv('DB_NAME') ?: 'pacific_hansard_db';

// $conn = new mysqli($servername, $username, $password, $dbname);

// if ($conn->connect_error) {
//     die(json_encode(array("error" => "Connection failed: " . $conn->connect_error)));
// }

// $article_id = $_GET['id'];
// // Log the received ID
// error_log("Received article ID: " . $article_id);

// $sql = "SELECT content FROM pacific_hansard_db WHERE new_id = ?";
// $stmt = $conn->prepare($sql);
// $stmt->bind_param("s", $article_id);  // Change to string parameter
// $stmt->execute();
// $result = $stmt->get_result();

// if ($result->num_rows > 0) {
//     $row = $result->fetch_assoc();
//     $response = json_encode(array("content" => $row['content']));
//     error_log("Response: " . $response);  // Log the response
//     echo $response;
// } else {
//     // Log the SQL query
//     error_log("SQL Query: " . $sql . " with ID: " . $article_id);
//     echo json_encode(array("error" => "Article not found"));
// }

// $stmt->close();
// $conn->close();


error_reporting(E_ALL);
ini_set('display_errors', 0);
ini_set('log_errors', 1);
header('Content-Type: application/json');

$servername = getenv('DB_HOST') ?: 'mysql';
$username = getenv('DB_USER') ?: 'root';
$password = getenv('DB_PASSWORD') ?: 'Wh1t3sh33ts';
$dbname = getenv('DB_NAME') ?: 'pacific_hansard_db';

// Solr connection details
$solr_url = getenv('SOLR_URL') ?: 'http://solr:8983/solr/hansard_core';

// Check if it's a Solr search request or a single article request
if (isset($_GET['q'])) {
    // This is a Solr search request
    $query = isset($_GET['q']) ? $_GET['q'] : '*:*';
    
    $document_type = isset($_GET['fq']) ? $_GET['fq'] : '';

    $solr_params = array(
        'q' => $query,
        'wt' => 'json',
        'fl' => 'id,new_id,title,document_type,date,source,content',
        'hl' => 'true',
        'hl.fl' => 'content',
        'hl.snippets' => '3',
        'hl.fragsize' => '250',
        'facet' => 'true',
        'facet.mincount' => '0',
        'facet.field' => array('source', 'document_type'),
        'rows' => '10',
        'start' => isset($_GET['start']) ? $_GET['start'] : '0',
        'facet.range' => 'date',
        'f.date.facet.range.start' => '2008-01-01T00:00:00Z',
        'f.date.facet.range.end' => '2023-06-08T00:00:00Z',
        'f.date.facet.range.gap' => '+1MONTH'
    );

    if (!empty($document_type)) {
        $solr_params['fq'] = $document_type;
    }

    // Make the Solr request
    $ch = curl_init($solr_url . '/select?' . http_build_query($solr_params));
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    $response = curl_exec($ch);
    
    if(curl_errno($ch)){
        echo json_encode(array("error" => "Solr request failed: " . curl_error($ch)));
    } else {
        echo $response;
    }
    
    curl_close($ch);

} else {
    // This is a single article request
    $conn = new mysqli($servername, $username, $password, $dbname);
    if ($conn->connect_error) {
        die(json_encode(array("error" => "Connection failed: " . $conn->connect_error)));
    }

    $article_id = $_GET['id'];
    error_log("Received article ID: " . $article_id);

    $sql = "SELECT content FROM pacific_hansard_db WHERE new_id = ?";
    $stmt = $conn->prepare($sql);
    $stmt->bind_param("s", $article_id);
    $stmt->execute();
    $result = $stmt->get_result();

    if ($result->num_rows > 0) {
        $row = $result->fetch_assoc();
        $response = json_encode(array("content" => $row['content']));
        error_log("Response: " . $response);
        echo $response;
    } else {
        error_log("SQL Query: " . $sql . " with ID: " . $article_id);
        echo json_encode(array("error" => "Article not found"));
    }

    $stmt->close();
    $conn->close();
}

?>