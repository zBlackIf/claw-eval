# wecom-media-processor

企微媒体后处理技能 - 对已经下载解密的媒体进行识别处理

## 功能说明
本技能依赖 wecom-media-downloader 先下载解密保存媒体文件，再对本地文件做后续处理：
- 图片压缩、识别、回答用户问题
- 文件类型检测、内容提取

## 环境变量
```bash
VISION_API_KEY=your_api_key
VISION_API_URL=https://ark.cn-beijing.volces.com/api/v3/responses
VISION_MODEL=doubao-seed-2-0-pro-260215
MEDIA_DIR=./media
```
