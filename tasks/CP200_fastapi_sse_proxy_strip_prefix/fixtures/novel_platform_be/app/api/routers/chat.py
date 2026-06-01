"""Novel API router - chat and analysis endpoints."""
import logging
import httpx
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, Body
from fastapi.responses import StreamingResponse

from app.core.database import get_db
from app.core.config import settings
from app.core.response import create_response, Errno
from app.models.novel import BasicInfo, Content, RecommendQuestion

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/novels", tags=["novels"])


@router.post("/chat")
async def chat_with_novel(
    request_data: dict,
    db: Session = Depends(get_db),
):
    """Chat with a novel via LangChain SSE endpoint.

    The upstream LangChain service returns SSE-formatted streaming data.
    This endpoint should proxy the upstream response to the frontend as a
    clean text stream suitable for direct display.
    """
    novel_id = request_data.get("novelId")
    message = request_data.get("message")
    history = request_data.get("history", [])

    if not novel_id or not message:
        return create_response(Errno.ParamBindError[0], "参数错误", None)

    # Check for pre-cached answer
    matched_question = db.query(RecommendQuestion).filter(
        RecommendQuestion.novel_id == novel_id,
        RecommendQuestion.question == message,
    ).first()

    if matched_question and matched_question.answer:
        return StreamingResponse(
            iter([matched_question.answer]),
            media_type="text/event-stream",
        )

    # Get novel summary for context
    novel = db.query(BasicInfo).filter(BasicInfo.id == novel_id).first()
    summary = novel.intro if novel and novel.intro else ""
    if not summary:
        content_record = db.query(Content).filter(Content.novel_id == novel_id).first()
        if content_record and content_record.novel_introduce:
            summary = content_record.novel_introduce

    async def generate():
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream(
                    "POST",
                    f"{settings.LANGCHAIN_HOST}/novel/chat/",
                    json={
                        "query": message,
                        "summary": summary,
                        "history": history,
                    },
                ) as response:
                    async for line in response.aiter_lines():
                        if line:
                            yield line
        except Exception as e:
            yield f"data: {{\"error\": \"{str(e)}\"}}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.post("/re_analysis")
async def re_analysis(
    request_data: dict,
    db: Session = Depends(get_db),
):
    """Re-analyze a specific module for a novel."""
    task_id = request_data.get("taskid")
    name = request_data.get("name", "")
    summary = request_data.get("summary", "")
    chunk = request_data.get("chunk", "")
    analysis_type = request_data.get("type", "person")
    pairs = request_data.get("pairs", [])

    if not task_id:
        return create_response(Errno.ParamBindError[0], "参数错误: taskid 不能为空", None)

    novel = db.query(BasicInfo).filter(BasicInfo.id == task_id).first()
    if not novel:
        return create_response(Errno.DataNotExist[0], "小说不存在", None)

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{settings.LANGCHAIN_HOST}/novel/re_analysis/",
                json={
                    "taskid": task_id,
                    "name": name,
                    "summary": summary,
                    "chunk": chunk,
                    "type": analysis_type,
                    "pairs": pairs,
                },
            )
            return create_response(Errno.Success[0], "重新分析已提交", resp.json())
    except Exception as e:
        logger.error(f"Re-analysis failed: {e}")
        return create_response(Errno.ServerError[0], f"重新分析失败: {str(e)}", None)
