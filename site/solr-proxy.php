<?php
// Solr proxy for Railway deployment
header('Access-Control-Allow-Origin: *');

// Get the Solr URL from environment
$solrBaseUrl = getenv('SOLR_URL') ?: 'http://localhost:8983/solr/hansard_core';

// Get the request path without query string
$requestUri = $_SERVER['REQUEST_URI'];
$requestPath = parse_url($requestUri, PHP_URL_PATH);
$requestPath = str_replace('/solr/hansard_core/', '', $requestPath);
$requestPath = str_replace('/solr/', '', $requestPath);

// Remove any leading slashes from the path
$requestPath = ltrim($requestPath, '/');

// Build the full Solr URL
if ($requestPath) {
    $solrUrl = $solrBaseUrl . '/' . $requestPath;
} else {
    $solrUrl = $solrBaseUrl;
}

// Add query string if present
if ($_SERVER['QUERY_STRING']) {
    $solrUrl .= '?' . $_SERVER['QUERY_STRING'];
}

// Debug logging (comment out in production)
error_log("Solr Proxy - Request URI: " . $_SERVER['REQUEST_URI']);
error_log("Solr Proxy - Query String: " . $_SERVER['QUERY_STRING']);
error_log("Solr Proxy - Final URL: " . $solrUrl);

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

// Set content type based on response
if ($httpCode == 200) {
    header('Content-Type: application/json');
}

// Output the response
echo $response;
?>