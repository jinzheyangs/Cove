"""隐私操作的 HTTP 接口。

- POST /privacy/delete：注销账号（不可逆）
"""

from fastapi import APIRouter

from app.core.deps import CurrentUser, SessionDep
from app.core.schemas import Envelope
from app.modules.privacy import service
from app.modules.privacy.schemas import DeleteAccountRequest

router = APIRouter(prefix="/privacy", tags=["privacy"])


@router.post("/delete", response_model=Envelope[None])
async def delete_account(
    body: DeleteAccountRequest, user: CurrentUser, session: SessionDep
) -> Envelope[None]:
    """注销账号。

    需要重新输入密码。注销后账号被匿名化，个人内容删除，
    但金币流水和商城记录保留，避免对方账目错乱。
    """
    await service.delete_account(session, user, body.password)
    return Envelope()
