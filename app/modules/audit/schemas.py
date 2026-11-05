"""审计日志的响应结构。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AuditOut(BaseModel):
    """一条审计记录。detail 是结构化元信息，不含隐私正文。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    action: str
    target_type: str | None
    target_id: int | None
    detail: dict | None
    ip: str | None
    request_id: str | None
    created_at: datetime
