<?php
// Solr proxy for Railway deployment
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

// Get the Solr URL from environment
$solrBaseUrl = getenv('SOLR_URL') ?: 'http://localhost:8983/solr/hansard_core';

// Get the request path
$requestPath = $_SERVER['REQUEST_URI'];
$requestPath = str_replace('/solr/hansard_core/', '', $requestPath);
$requestPath = str_replace('/solr/', '', $requestPath);

// Build the full Solr URL with query string
$solrUrl = $solrBaseUrl . '/' . $requestPath;
if ($_SERVER['QUERY_STRING']) {
    $solrUrl .= '?' . $_SERVER['QUERY_STRING'];
}

// Initialize cURL
$ch = curl_init();
curl_setopt($ch, CURLOPT_URL, $solrUrl);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
curl_setopt($ch, CURLOPT_HEADER, false);
curl_setopt($ch, CURLOPT_TIMEOUT, 30);

// Execute the request
$response = curl_exec($ch);
$httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
$error = curl_error($ch);
curl_close($ch);

// Handle errors
if ($error) {
    http_response_code(500);
    echo json_encode(['error' => 'Proxy error: ' . $error]);
    exit;
}

// Forward the HTTP status code
http_response_code($httpCode);

// Output the response
echo $response;
?>