from sqlalchemy import Text
from sqlalchemy.types import TypeDecorator

from app.core.crypto import decrypt, encrypt


class EncryptedText(TypeDecorator):
    """透明加密的文本列。

    数据库里存的是密文，ORM 读写时自动加解密。
    不要在这类列上做 LIKE / 全文检索——密文搜不到。
    """

    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return encrypt(str(value))

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return decrypt(value)
