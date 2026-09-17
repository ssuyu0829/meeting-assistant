"""共用的權限檢查。

原本三個 router 各自寫一份成員檢查，availability.py 就整個漏掉了
（任何登入者猜到 meeting_id 就能讀寫別人群組的時段）。放這裡讓新端點有現成的可用。
"""
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
import models


def require_group_member(group_id: int, user_id: int, db: Session) -> models.GroupMember:
    membership = db.query(models.GroupMember).filter_by(
        group_id=group_id, user_id=user_id
    ).first()
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of this group")
    return membership


def require_meeting_member(
    meeting_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> models.Meeting:
    """會議存在，而且目前使用者是該會議所屬群組的成員。"""
    meeting = db.get(models.Meeting, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    require_group_member(meeting.group_id, current_user.id, db)
    return meeting
