<?php
/**
 * upload_handler.php — legacy file upload endpoint
 * 上线日期：2024-09
 * 上一次安全 review：2024-09（>18 months stale）
 */

session_start();

// ===== 1. 鉴权 =====
if (!isset($_SESSION['user_id'])) {
    die("not logged in");
}

// ===== 2. 文件接收 =====
$file = $_FILES['upload'] ?? null;
if (!$file) {
    die("no file");
}

$allowed_ext = ['jpg', 'png', 'gif', 'pdf', 'docx'];
$ext = strtolower(pathinfo($file['name'], PATHINFO_EXTENSION));
if (!in_array($ext, $allowed_ext)) {
    die("ext not allowed");
}

// ===== 3. 文件名处理 =====
$dest = "/var/www/uploads/" . $file['name'];

// ===== 4. 文件大小 =====
if ($file['size'] > 100 * 1024 * 1024) {
    error_log("oversize: " . $file['name']);
}

// ===== 5. 移动文件 =====
move_uploaded_file($file['tmp_name'], $dest);

// ===== 6. 上传后处理 =====
$url = "/uploads/" . $file['name'];
echo "uploaded to: " . $url;

// ===== 7. 日志 =====
$log = "[" . date("Y-m-d H:i:s") . "] " . $_SERVER['REMOTE_ADDR'] . " uploaded " . $dest . "\n";
file_put_contents("/var/log/upload.log", $log, FILE_APPEND);
?>
