"""秘密树的 HTTP 接口。

约定：
- 列表接口永远不返回 content
- 只有 POST /{id}/unlock 才会返回内容并扣币
- 销毁只能作用于自己发布的秘密
"""

from fastapi import APIRouter

from app.core.deps import CurrentUser, SessionDep
from app.core.schemas import Envelope
from app.modules.couples.deps import CurrentCouple
from app.modules.secrets import service
from app.modules.secrets.schemas import SecretCreate, SecretDetail, SecretListItem

router = APIRouter(prefix="/secrets", tags=["secrets"])


@router.post("", response_model=Envelope[SecretListItem])
async def publish(
    body: SecretCreate, user: CurrentUser, couple: CurrentCouple, session: SessionDep
) -> Envelope[SecretListItem]:
    """发布一条秘密。返回列表项，不回显内容。"""
    secret = await service.publish(session, couple, user, body)
    return Envelope(
        data=SecretListItem(
            id=secret.id,
            level=secret.level,
            cost_coins=secret.cost_coins,
            is_burn_after_read=secret.is_burn_after_read,
            status=secret.status,
            authored_by_me=True,
            viewed=False,
            created_at=secret.created_at,
        )
    )


@router.get("", response_model=Envelope[list[SecretListItem]])
async def list_available(
    user: CurrentUser, couple: CurrentCouple, session: SessionDep
) -> Envelope[list[SecretListItem]]:
    """对方发布、我还能摘的秘密。列表里没有内容。"""
    # 列表只返回对方发布的、还能摘的秘密，不含内容
    return Envelope(data=await service.list_available(session, couple, user))


@router.get("/mine", response_model=Envelope[list[SecretListItem]])
async def list_mine(
    user: CurrentUser, couple: CurrentCouple, session: SessionDep
) -> Envelope[list[SecretListItem]]:
    """我发布的秘密，包含被摘取和已销毁的。"""
    return Envelope(data=await service.list_mine(session, couple, user))


@router.post("/{secret_id}/unlock", response_model=Envelope[SecretDetail])
async def unlock(
    secret_id: int, user: CurrentUser, couple: CurrentCouple, session: SessionDep
) -> Envelope[SecretDetail]:
    """花金币摘取。成功才扣费，余额不足会返回 4001。"""
    return Envelope(data=await service.unlock(session, couple, user, secret_id))


@router.delete("/{secret_id}", response_model=Envelope[None])
async def destroy(
    secret_id: int, user: CurrentUser, couple: CurrentCouple, session: SessionDep
) -> Envelope[None]:
    """销毁单条。只能销毁自己发布的。"""
    await service.destroy(session, couple, user, secret_id)
    return Envelope()


@router.delete("", response_model=Envelope[dict])
async def destroy_all(
    user: CurrentUser, couple: CurrentCouple, session: SessionDep
) -> Envelope[dict]:
    """一键销毁自己发布的全部秘密，不碰对方的。"""
    count = await service.destroy_all_mine(session, couple, user)
    return Envelope(data={"destroyed": count})
