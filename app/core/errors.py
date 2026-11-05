"""统一异常与响应格式。

所有接口无论成功失败都返回：
    { "code": 0, "message": "success", "data": ... }

`code` 是业务错误码（401/1001/2001...），HTTP 状态码单独看 `status_code`。
客户端通常只需要判断 `code`。
"""

import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = structlog.get_logger("app")


class AppError(Exception):
    """业务异常。

    用法：
        raise AppError("金币不足", code=4001, status_code=409)

    不要在业务层直接返回 JSONResponse——抛这个异常，
    由下面的处理器统一转换，保证格式一致。
    """

    def __init__(self, message: str, *, code: int = 1, status_code: int = 400) -> None:
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(message)


def register_exception_handlers(app: FastAPI) -> None:
    """注册全局异常处理器。启动时调用一次。"""

    @app.exception_handler(AppError)
    async def _handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        # 业务异常是预期内的，用 warning 而不是 error，
        # 否则日志里会被正常的 4xx 刷屏。
        logger.warning(
            "app.error",
            code=exc.code,
            message=exc.message,
            status_code=exc.status_code,
            path=request.url.path,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": exc.code, "message": exc.message, "data": None},
        )

    @app.exception_handler(Exception)
    async def _handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        # 未捕获异常用 exception 级别，会带完整堆栈。
        # 对外只返回通用文案，不泄露内部细节。
        logger.exception("app.unhandled", path=request.url.path)
        return JSONResponse(
            status_code=500,
            content={"code": 500, "message": "服务开小差了，请稍后再试", "data": None},
        )
