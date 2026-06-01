"""AI 退款助手后端服务（简化版）"""
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
import json
import os

app = FastAPI(title="AI Refund Agent Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 模拟数据库 - model 表（控制 UI 模式）
MODELS_DATA = [
    {"id": 1, "name": "浮窗模式", "state": 0},
    {"id": 2, "name": "弹窗模式", "state": 1},
    {"id": 3, "name": "固定模式", "state": 0},
    {"id": 4, "name": "静默模式", "state": 0},
]

# 模拟数据库 - operation_logs 表
OPERATION_LOGS = []


class LogEntry(BaseModel):
    file_name: str
    business_name: str = "退款申请"
    result: str  # BUG: 应该是 int 类型 (1=成功, 0=失败)


@app.get("/api/models")
def get_models():
    """获取 model 列表（UI 模式配置）"""
    return {"success": True, "data": MODELS_DATA}


@app.post("/api/recognize")
async def recognize(file: UploadFile = File(...), business_name: str = Form("退款申请")):
    """模拟 OCR 识别退款凭证"""
    # 模拟识别结果
    records = [
        {"field_name": "客户姓名", "value": "王小明"},
        {"field_name": "退款金额", "value": "1280.00"},
        {"field_name": "退款原因", "value": "房间设施损坏未修复"},
        {"field_name": "订单编号", "value": "RF-2026-0517-0023"},
        {"field_name": "入住日期", "value": "2026-05-10"},
        {"field_name": "退房日期", "value": "2026-05-12"},
    ]
    return {"success": True, "records": records, "file_name": file.filename}


@app.post("/api/logs")
def create_log(log: LogEntry):
    """创建操作日志"""
    # BUG: result 字段声明为 str，但业务要求是 int (1=成功, 0=失败)
    # 当前直接存储，未做类型校验
    entry = {
        "id": len(OPERATION_LOGS) + 1,
        "file_name": log.file_name,
        "business_name": log.business_name,
        "result": log.result,
    }
    OPERATION_LOGS.append(entry)
    return {"success": True, "data": entry}


@app.get("/api/logs")
def get_logs(result: Optional[str] = None):
    """获取操作日志列表"""
    logs = OPERATION_LOGS
    if result is not None:
        logs = [l for l in logs if str(l["result"]) == result]
    return {"success": True, "data": logs}


@app.get("/agent.js")
def serve_agent_js():
    """提供 agent.js 静态文件"""
    js_path = os.path.join(os.path.dirname(__file__), "agent.js")
    if os.path.exists(js_path):
        return FileResponse(js_path, media_type="application/javascript")
    raise HTTPException(status_code=404, detail="agent.js not found")


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
