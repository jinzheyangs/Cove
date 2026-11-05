"""自定义 SQLAlchemy 类型。"""

from sqlalchemy import Text
from sqlalchemy.types import TypeDecorator

from app.core.crypto import decrypt, encrypt


class EncryptedText(TypeDecorator):
    """透明加密的文本列。

    数据库里存的是密文，ORM 读写时自动加解密，
    业务代码完全不需要感知加密的存在。

    用法：
        content: Mapped[str] = mapped_column(EncryptedText)

    注意：
    - 不要在这类列上做 LIKE / 全文检索——密文搜不到
    - 不要拿这类列做唯一约束或排序——密文没有可比性
    - 密钥更换后旧数据无法解密，换密钥前必须重新加密
    """

    # 底层 DDL 类型仍然是 TEXT，所以迁移只是在改类型注解，不改变存储大小
    impl = Text
    # 告诉 SQLAlchemy 这个类型可以安全缓存
    cache_ok = True

    def process_bind_param(self, value, dialect):
        """写入数据库前调用：明文 -> 密文。"""
        if value is None:
            return None
        return encrypt(str(value))

    def process_result_value(self, value, dialect):
        """从数据库读出后调用：密文 -> 明文。"""
        if value is None:
            return None
        return decrypt(value)
