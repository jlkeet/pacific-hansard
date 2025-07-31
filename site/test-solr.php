<?php
header('Content-Type: text/plain');

echo "Testing Solr Connection\n";
echo "======================\n\n";

$solrUrl = getenv('SOLR_URL') ?: 'http://localhost:8983/solr/hansard_core';
echo "SOLR_URL: " . $solrUrl . "\n\n";

// Test direct connection to Solr
$testUrl = $solrUrl . '/select?q=*:*&rows=0&wt=json';
echo "Testing: " . $testUrl . "\n\n";

$ch = curl_init();
curl_setopt($ch, CURLOPT_URL, $testUrl);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
curl_setopt($ch, CURLOPT_TIMEOUT, 10);

$response = curl_exec($ch);
$httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
$error = curl_error($ch);
curl_close($ch);

if ($error) {
    echo "CURL Error: " . $error . "\n";
} else {
    echo "HTTP Code: " . $httpCode . "\n";
    echo "Response: " . substr($response, 0, 500) . "...\n";
}

// Test the proxy
echo "\n\nTesting Proxy\n";
echo "=============\n";
$proxyUrl = '/solr/hansard_core/select?q=*:*&rows=0&wt=json';
echo "Would access: " . $proxyUrl . "\n";
?>