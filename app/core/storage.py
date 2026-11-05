"""对象存储。

支持两种后端：
- local：开发环境，文件写到本地目录，由 FastAPI 静态挂载到 /uploads
- oss：阿里云 OSS

关键约定：**数据库里存的是 object key，不是完整 URL。**
读取时由 `build_url()` 按当前配置生成可访问地址：
- local：`/uploads/{key}`
- OSS 私有桶：带有效期的签名 URL
- OSS 公共读：公共域名 + key

这样换 CDN、改私有桶、迁移存储都不需要改数据。
"""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

import structlog

from app.core.config import settings

logger = structlog.get_logger("storage")


class Storage:
    """存储后端的统一接口。"""

    def save(self, key: str, data: bytes, content_type: str) -> None:
        raise NotImplementedError

    def delete(self, key: str) -> None:
        raise NotImplementedError

    def build_url(self, key: str) -> str:
        raise NotImplementedError


class LocalStorage(Storage):
    """本地磁盘。

    只用于开发和测试。生产环境请用 OSS：
    本地文件不会自动备份，也无法多实例共享。
    """

    def __init__(self, root: str | Path, base_url: str = "/uploads") -> None:
        self.root = Path(root).resolve()
        self.base_url = base_url.rstrip("/")
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        """把 key 转成绝对路径，并阻止目录穿越。"""
        path = (self.root / key).resolve()
        if not path.is_relative_to(self.root):
            raise ValueError(f"非法的存储 key: {key}")
        return path

    def save(self, key: str, data: bytes, content_type: str) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def delete(self, key: str) -> None:
        path = self._path(key)
        if path.exists():
            path.unlink()

    def build_url(self, key: str) -> str:
        # 历史数据或外部图片可能是完整 URL，原样返回
        if key.startswith(("http://", "https://")):
            return key
        return f"{self.base_url}/{key}"


class OSSStorage(Storage):
    """阿里云 OSS。

    oss2 是可选依赖：只有 STORAGE_BACKEND=oss 时才需要安装。
    安装方式：uv sync --extra oss
    """

    def __init__(
        self,
        *,
        endpoint: str,
        bucket_name: str,
        access_key_id: str,
        access_key_secret: str,
        private: bool,
        public_base_url: str,
        expire_seconds: int,
    ) -> None:
        import oss2  # 延迟导入，local 模式不需要这个依赖

        self.bucket_name = bucket_name
        self.endpoint = endpoint
        self.private = private
        self.public_base_url = public_base_url.rstrip("/")
        self.expire_seconds = expire_seconds
        self.bucket = oss2.Bucket(
            oss2.Auth(access_key_id, access_key_secret), endpoint, bucket_name
        )

    def save(self, key: str, data: bytes, content_type: str) -> None:
        self.bucket.put_object(key, data, headers={"Content-Type": content_type})

    def delete(self, key: str) -> None:
        self.bucket.delete_object(key)

    def build_url(self, key: str) -> str:
        if key.startswith(("http://", "https://")):
            return key

        if self.private:
            # 私有桶：生成有时效的签名 URL
            return self.bucket.sign_url("GET", key, self.expire_seconds)

        if self.public_base_url:
            return f"{self.public_base_url}/{key}"

        host = urlparse(self.endpoint).hostname or ""
        return f"https://{self.bucket_name}.{host}/{key}"


_storage: Storage | None = None


def get_storage() -> Storage:
    """按配置返回存储后端（进程内单例）。"""
    global _storage
    if _storage is not None:
        return _storage

    if settings.STORAGE_BACKEND == "oss":
        _storage = OSSStorage(
            endpoint=settings.OSS_ENDPOINT,
            bucket_name=settings.OSS_BUCKET,
            access_key_id=settings.OSS_ACCESS_KEY_ID,
            access_key_secret=settings.OSS_ACCESS_KEY_SECRET,
            private=settings.OSS_PRIVATE,
            public_base_url=settings.STORAGE_PUBLIC_BASE_URL,
            expire_seconds=settings.STORAGE_URL_EXPIRE_SECONDS,
        )
    else:
        _storage = LocalStorage(
            settings.UPLOAD_DIR, settings.STORAGE_PUBLIC_BASE_URL or "/uploads"
        )
    return _storage


def validate_storage_config() -> None:
    """启动时检查 OSS 配置，避免上线后第一次上传才发现缺参数。"""
    if settings.STORAGE_BACKEND != "oss":
        return

    missing = [
        name
        for name, value in {
            "OSS_ENDPOINT": settings.OSS_ENDPOINT,
            "OSS_BUCKET": settings.OSS_BUCKET,
            "OSS_ACCESS_KEY_ID": settings.OSS_ACCESS_KEY_ID,
            "OSS_ACCESS_KEY_SECRET": settings.OSS_ACCESS_KEY_SECRET,
        }.items()
        if not value
    ]
    if missing:
        raise RuntimeError(f"OSS 配置缺失: {', '.join(missing)}")
