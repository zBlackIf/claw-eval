"""Standard response helpers."""
from typing import Any


class Errno:
    Success = (0, "成功")
    ParamBindError = (400, "参数错误")
    DataNotExist = (404, "数据不存在")
    ServerError = (500, "服务器错误")


def create_response(code: int, message: str, data: Any) -> dict:
    return {"code": code, "message": message, "data": data}
