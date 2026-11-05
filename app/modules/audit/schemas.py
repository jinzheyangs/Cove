from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AuditOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    action: str
    target_type: str | None
    target_id: int | None
    detail: dict | None
    ip: str | None
    request_id: str | None
    created_at: datetime
