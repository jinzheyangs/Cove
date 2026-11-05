from sqlalchemy import text

from app.core.crypto import decrypt, encrypt
from app.modules.secrets import service as secret_service
from app.modules.secrets.models import Secret
from app.modules.secrets.schemas import SecretCreate
from tests.helpers import seed_couple


def test_encrypt_roundtrip():
    token = encrypt("很私密的话")

    assert token is not None
    assert token.startswith("v1:")
    assert decrypt(token) == "很私密的话"


def test_plaintext_is_passed_through():
    # 兼容历史明文数据
    assert decrypt("老数据") == "老数据"


def test_reencrypt_is_idempotent():
    token = encrypt("abc")
    assert encrypt(token) == token


async def test_secret_is_ciphertext_in_database(session):
    a, _, couple = await seed_couple(session)
    secret = await secret_service.publish(
        session, couple, a, SecretCreate(content="不要告诉别人")
    )
    secret_id = secret.id

    raw = await session.scalar(
        text("SELECT content FROM secrets WHERE id = :id"), {"id": secret_id}
    )
    assert raw.startswith("v1:")
    assert "不要告诉别人" not in raw

    session.expire_all()
    fetched = await session.get(Secret, secret_id)
    assert fetched is not None
    assert fetched.content == "不要告诉别人"
