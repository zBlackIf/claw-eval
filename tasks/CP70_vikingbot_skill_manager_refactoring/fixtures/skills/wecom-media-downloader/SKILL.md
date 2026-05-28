# wecom-media-downloader

企微媒体下载解密技能 - 只负责下载解密保存

## 功能说明
从企微获取加密媒体文件，下载、解密后保存到本地 ./media/ 目录。

## 处理流程
1. 从消息提取url和aeskey
2. 下载加密媒体
3. AES解密（32字节key，前16字节作为IV，CBC模式）
4. 保存到 ./media/
