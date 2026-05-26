<?php
/**
 * upload_handler.php — legacy file upload endpoint
 * 上线日期：2024-09
 * 上一次安全 review：2024-09（>18 months stale）
 *
 * 本文件包含多处安全漏洞，需要审计指出。
 */

session_start();

// ===== 1. 鉴权（弱） =====
if (!isset($_SESSION['user_id'])) {
    // 没鉴权直接 die，但没有 CSRF token 校验！
    die("not logged in");
}

// ===== 2. 文件接收 =====
$file = $_FILES['upload'] ?? null;
if (!$file) {
    die("no file");
}

// ⚠️ 仅靠扩展名白名单（绕过点：双扩展名、大小写、URL 编码、.htaccess）
$allowed_ext = ['jpg', 'png', 'gif', 'pdf', 'docx'];
$ext = strtolower(pathinfo($file['name'], PATHINFO_EXTENSION));
if (!in_array($ext, $allowed_ext)) {
    die("ext not allowed");
}

// ⚠️ 没有校验 MIME type；没有用 finfo 探嗅真实内容；
//   攻击者可上传 evil.jpg.php 或 evil.JPG（如服务器配置不当）

// ===== 3. 文件名处理 =====
// ⚠️ 直接用用户提供的文件名（path traversal 风险：../../etc/passwd）
$dest = "/var/www/uploads/" . $file['name'];

// ===== 4. 文件大小 =====
// ⚠️ 没有上传大小限制 → DoS（文件系统填满）
if ($file['size'] > 100 * 1024 * 1024) {  // 100MB 注释错位，实际是写在 if 内
    // ⚠️ 仅 log 但**没有 return**，文件仍会被保存
    error_log("oversize: " . $file['name']);
}

// ===== 5. 移动文件 =====
// ⚠️ 没有处理 race condition (TOCTOU)：
//   同名文件并发上传可能互相覆盖；攻击者也可能在 move 前 racing 一个 symlink
move_uploaded_file($file['tmp_name'], $dest);

// ===== 6. 上传后处理 =====
// ⚠️ 立即给 URL 返给前端 → 攻击者可以马上访问 evil.php
$url = "/uploads/" . $file['name'];
echo "uploaded to: " . $url;  // ⚠️ XSS：未对 filename 做 htmlspecialchars

// ===== 7. 日志 =====
// ⚠️ 把完整用户 IP + 文件路径写到日志，可能泄露隐私（GDPR）
$log = "[" . date("Y-m-d H:i:s") . "] " . $_SERVER['REMOTE_ADDR'] . " uploaded " . $dest . "\n";
file_put_contents("/var/log/upload.log", $log, FILE_APPEND);

// ===== 8. 没有 .htaccess 防护 =====
// ⚠️ /var/www/uploads/ 没有放置 .htaccess 阻止 PHP 执行；
//   nginx 也没有 location ~ \.php$ deny 配置；
//   配合扩展名绕过 → RCE
?>
