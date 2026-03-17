from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from database import get_db
from auth import get_current_user
import models

router = APIRouter(prefix="/api/meetings", tags=["meetings"])


class CreateFolderRequest(BaseModel):
    name: str
    group_id: int


class CreateMeetingRequest(BaseModel):
    name: str
    group_id: int
    folder_id: Optional[int] = None
    dates: List[str]  # ["YYYY/MM/DD", ...]


class FolderOut(BaseModel):
    id: int
    name: str
    group_id: int
    meeting_count: int


class MeetingOut(BaseModel):
    id: int
    name: str
    group_id: int
    folder_id: Optional[int]
    status: str
    dates: List[str]
    created_by_name: str
    is_leader: bool


class GroupMeetingsOut(BaseModel):
    folders: List[FolderOut]
    meetings: List[MeetingOut]  # standalone meetings only


def _meeting_to_out(m: models.Meeting, current_user_id: int, db: Session) -> MeetingOut:
    creator = db.get(models.User, m.created_by)
    return MeetingOut(
        id=m.id,
        name=m.name,
        group_id=m.group_id,
        folder_id=m.folder_id,
        status=m.status.value,
        dates=sorted([d.date for d in m.dates]),
        created_by_name=creator.name if creator else "",
        is_leader=(m.created_by == current_user_id),
    )


# ─── Folders ────────────────────────────────────────────────────────────────

@router.get("/folders/{group_id}", response_model=List[FolderOut])
def list_folders(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    _require_member(group_id, current_user.id, db)
    folders = db.query(models.Folder).filter_by(group_id=group_id).all()
    return [FolderOut(
        id=f.id, name=f.name, group_id=f.group_id,
        meeting_count=len(f.meetings)
    ) for f in folders]


@router.post("/folders", response_model=FolderOut)
def create_folder(
    body: CreateFolderRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    _require_member(body.group_id, current_user.id, db)
    if len(body.name) > 6:
        raise HTTPException(status_code=400, detail="Folder name must be 6 characters or fewer")
    existing_names = [f.name for f in db.query(models.Folder).filter_by(group_id=body.group_id).all()]
    if body.name in existing_names:
        raise HTTPException(status_code=400, detail="Folder name already exists in this group")

    folder = models.Folder(name=body.name, group_id=body.group_id, created_by=current_user.id)
    db.add(folder)
    db.commit()
    db.refresh(folder)
    return FolderOut(id=folder.id, name=folder.name, group_id=folder.group_id, meeting_count=0)


# ─── Meetings ───────────────────────────────────────────────────────────────

@router.get("/group/{group_id}", response_model=GroupMeetingsOut)
def list_group_meetings(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    _require_member(group_id, current_user.id, db)

    folders = db.query(models.Folder).filter_by(group_id=group_id).all()
    folder_outs = [FolderOut(
        id=f.id, name=f.name, group_id=f.group_id,
        meeting_count=len(f.meetings)
    ) for f in folders]

    standalone = db.query(models.Meeting).filter_by(
        group_id=group_id, folder_id=None
    ).all()
    meeting_outs = [_meeting_to_out(m, current_user.id, db) for m in standalone]

    return GroupMeetingsOut(folders=folder_outs, meetings=meeting_outs)


@router.get("/folder/{folder_id}", response_model=List[MeetingOut])
def list_folder_meetings(
    folder_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    folder = db.get(models.Folder, folder_id)
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")
    _require_member(folder.group_id, current_user.id, db)
    return [_meeting_to_out(m, current_user.id, db) for m in folder.meetings]


@router.post("", response_model=MeetingOut)
def create_meeting(
    body: CreateMeetingRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    _require_member(body.group_id, current_user.id, db)
    if len(body.name) > 8:
        raise HTTPException(status_code=400, detail="Meeting name must be 8 characters or fewer")
    if not body.dates:
        raise HTTPException(status_code=400, detail="At least one date is required")

    # check uniqueness within group+folder context
    scope_q = db.query(models.Meeting).filter_by(group_id=body.group_id)
    if body.folder_id:
        scope_q = scope_q.filter_by(folder_id=body.folder_id)
    else:
        scope_q = scope_q.filter(models.Meeting.folder_id.is_(None))
    if scope_q.filter_by(name=body.name).first():
        raise HTTPException(status_code=400, detail="Meeting name already exists")

    meeting = models.Meeting(
        name=body.name,
        group_id=body.group_id,
        folder_id=body.folder_id,
        created_by=current_user.id,
    )
    db.add(meeting)
    db.flush()

    for date in body.dates:
        db.add(models.MeetingDate(meeting_id=meeting.id, date=date))

    db.add(models.MeetingRecord(meeting_id=meeting.id))
    db.commit()
    db.refresh(meeting)
    return _meeting_to_out(meeting, current_user.id, db)


@router.get("/{meeting_id}", response_model=MeetingOut)
def get_meeting(
    meeting_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    meeting = db.get(models.Meeting, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    _require_member(meeting.group_id, current_user.id, db)
    return _meeting_to_out(meeting, current_user.id, db)


@router.post("/{meeting_id}/finish")
def finish_meeting(
    meeting_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    meeting = db.get(models.Meeting, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    if meeting.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Only the meeting creator can finish it")
    meeting.status = models.MeetingStatus.finished
    db.commit()
    return {"ok": True}


# ─── Helper ─────────────────────────────────────────────────────────────────

def _require_member(group_id: int, user_id: int, db: Session):
    if not db.query(models.GroupMember).filter_by(group_id=group_id, user_id=user_id).first():
        raise HTTPException(status_code=403, detail="Not a member of this group")
