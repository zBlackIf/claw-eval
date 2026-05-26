<?php

require __DIR__ . '/vendor/autoload.php';

use Proxy\Http\Request;
use Proxy\Proxy;

$request = Request::createFromGlobals();

$url = isset($_GET['q']) ? $_GET['q'] : '';

if (empty($url)) {
    echo '<html><body><h1>PHP Proxy</h1><form method="get"><input name="q" placeholder="Enter URL..." style="width:400px"><button>Go</button></form></body></html>';
    exit;
}

$proxy = new Proxy();

try {
    $response = $proxy->forward($request, $url);
    $response->send();
} catch (\Exception $e) {
    echo 'Error: ' . $e->getMessage();
}
