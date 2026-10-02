from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class AuditEventRead(BaseModel):
    id: int
    timestamp: datetime
    actor_id: Optional[int]
    actor_username: Optional[str]
    action: str
    target_type: Optional[str]
    target_id: Optional[str]
    result: str
    source_context: Optional[str]