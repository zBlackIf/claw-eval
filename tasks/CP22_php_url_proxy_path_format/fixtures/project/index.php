<?php

define('PROXY_START', microtime(true));

if (file_exists("vendor/autoload.php")) {
    require("vendor/autoload.php");
}

if (!function_exists('curl_version')) {
    die("cURL extension is not loaded!");
}

if (empty($_GET['q'])) {
    if (file_exists('templates/main.php')) {
        require 'templates/main.php';
        exit;
    }
    echo "<h1>PHP Proxy</h1><form><input name=q><button>Go</button></form>";
    exit;
}

$target_url = $_GET['q'];

// Normalize: if the user typed the URL without a scheme, default to http://
if (!preg_match('#^https?://#i', $target_url)) {
    $target_url = 'http://' . $target_url;
}

// Load the proxy config (in real deploy this sets up headers, plugins, etc.)
// Config::load('./config.php');

echo "Proxying to: " . htmlspecialchars($target_url) . "\n";
