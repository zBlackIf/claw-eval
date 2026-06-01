// AI退款智能体注入脚本
(function() {
    // 样式注入
    const style = document.createElement('style');
    style.textContent = `
        .ai-agent-ball {
            position: fixed;
            bottom: 30px;
            right: 30px;
            width: 60px;
            height: 60px;
            border-radius: 50%;
            background: linear-gradient(135deg, #1890ff 0%, #40a9ff 100%);
            box-shadow: 0 4px 16px rgba(24, 144, 255, 0.4);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 24px;
            cursor: pointer;
            z-index: 999999;
            transition: all 0.3s ease;
            user-select: none;
        }
        .ai-agent-ball:hover {
            transform: scale(1.1);
            box-shadow: 0 6px 20px rgba(24, 144, 255, 0.6);
        }
        .ai-agent-panel {
            position: fixed;
            bottom: 100px;
            right: 30px;
            width: 380px;
            background: white;
            border-radius: 12px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
            z-index: 999998;
            display: none;
            overflow: hidden;
        }
        .ai-agent-panel.active {
            display: block;
        }
        .ai-panel-header {
            background: linear-gradient(135deg, #1890ff 0%, #40a9ff 100%);
            color: white;
            padding: 16px 20px;
            font-size: 16px;
            font-weight: 500;
        }
        .ai-panel-body {
            padding: 20px;
        }
        .ai-upload-area {
            border: 2px dashed #d9d9d9;
            border-radius: 8px;
            padding: 30px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s;
        }
        .ai-upload-area:hover {
            border-color: #1890ff;
            background: #f0f7ff;
        }
        .ai-status {
            margin-top: 12px;
            padding: 8px 12px;
            border-radius: 6px;
            font-size: 13px;
            display: none;
        }
        .ai-status.show {
            display: block;
        }
        .ai-status.processing {
            background: #e6f7ff;
            color: #1890ff;
        }
        .ai-status.success {
            background: #f6ffed;
            color: #52c41a;
        }
        .ai-status.error {
            background: #fff2f0;
            color: #ff4d4f;
        }
    `;
    document.head.appendChild(style);

    // API 配置
    const API_BASE = 'http://localhost:8001';

    // 创建悬浮球
    const ball = document.createElement('div');
    ball.className = 'ai-agent-ball';
    ball.innerHTML = '🤖';
    ball.title = 'AI 退款助手';
    document.body.appendChild(ball);

    // 创建面板
    const panel = document.createElement('div');
    panel.className = 'ai-agent-panel';
    panel.innerHTML = `
        <div class="ai-panel-header">退款申请 AI 填充</div>
        <div class="ai-panel-body">
            <div class="ai-upload-area" id="ai-upload-zone">
                <div style="font-size: 36px; margin-bottom: 8px;">📄</div>
                <div style="color: #666;">点击或拖拽上传退款凭证</div>
                <div style="color: #999; font-size: 12px; margin-top: 4px;">支持 JPG/PNG/PDF</div>
                <input type="file" id="ai-file-input" accept=".jpg,.jpeg,.png,.pdf" style="display:none;">
            </div>
            <div class="ai-status" id="ai-status"></div>
        </div>
    `;
    document.body.appendChild(panel);

    // 悬浮球点击
    ball.addEventListener('click', function() {
        panel.classList.toggle('active');
    });

    // 文件上传
    const uploadZone = document.getElementById('ai-upload-zone');
    const fileInput = document.getElementById('ai-file-input');
    const statusEl = document.getElementById('ai-status');

    uploadZone.addEventListener('click', () => fileInput.click());
    uploadZone.addEventListener('dragover', (e) => { e.preventDefault(); uploadZone.style.borderColor = '#1890ff'; });
    uploadZone.addEventListener('dragleave', () => { uploadZone.style.borderColor = '#d9d9d9'; });
    uploadZone.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadZone.style.borderColor = '#d9d9d9';
        if (e.dataTransfer.files.length > 0) {
            handleFile(e.dataTransfer.files[0]);
        }
    });
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFile(e.target.files[0]);
        }
    });

    // 处理文件上传和识别
    async function handleFile(file) {
        showStatus('processing', '正在识别退款凭证...');
        const formData = new FormData();
        formData.append('file', file);
        formData.append('business_name', '退款申请');

        try {
            const resp = await fetch(`${API_BASE}/api/recognize`, {
                method: 'POST',
                body: formData
            });
            const data = await resp.json();
            if (data.success) {
                showStatus('success', '识别完成，正在填充表单...');
                fillForm(data.records);
                // TODO: 记录操作日志
            } else {
                showStatus('error', '识别失败: ' + (data.message || '未知错误'));
            }
        } catch (err) {
            showStatus('error', '请求失败: ' + err.message);
        }
    }

    // 自动填充表单
    function fillForm(records) {
        console.log('===== [自动填充表单] 开始 =====');
        console.log('待填充的记录：', records);

        // BUG: 填充逻辑未实现——只打印了日志
        // 需要根据 records 中的字段自动填入页面表单
        // records 格式: [{field_name: "客户姓名", value: "张三"}, ...]

        showStatus('success', '表单填充完成');
    }

    // 显示状态
    function showStatus(type, message) {
        statusEl.className = 'ai-status show ' + type;
        statusEl.textContent = message;
    }

    // TODO: 弹窗模式逻辑
    // 当后端 model 接口返回的弹窗模式 state 为激活时，
    // 需要实现页面锁定和自动解锁逻辑

    // TODO: 操作日志记录
    // 识别完成后需要调用后端日志接口记录结果
})();
