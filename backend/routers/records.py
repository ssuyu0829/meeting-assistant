import os
import resend
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional, Dict
from database import get_db
from auth import get_current_user
import models

router = APIRouter(prefix="/api/records", tags=["records"])


class AttendanceItem(BaseModel):
    user_id: int
    absence_status: Optional[str] = None   # "ontime" | "late" | "absent"
    mission_status: Optional[str] = None   # "done" | "undone" | "none"


class SaveAttendanceRequest(BaseModel):
    items: List[AttendanceItem]


class SaveMeetingNoteRequest(BaseModel):
    record_text: str


class DecideTimeRequest(BaseModel):
    date: str
    start_time: str
    end_time: str
    notes: str


class MeetingRecordOut(BaseModel):
    record_text: str
    decided_time: str
    notes: str
    time_decided: bool


class MeetingSummaryOut(BaseModel):
    meeting_name: str
    decided_time: str
    record_text: str
    notes: str
    ontime: List[str]
    late: List[str]
    absent: List[str]
    done: List[str]
    undone: List[str]
    none_task: List[str]


# ─── Meeting Record ──────────────────────────────────────────────────────────

@router.get("/{meeting_id}", response_model=MeetingRecordOut)
def get_record(
    meeting_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    record = _require_record(meeting_id, current_user.id, db)
    return MeetingRecordOut(
        record_text=record.record_text or "",
        decided_time=record.decided_time or "",
        notes=record.notes or "",
        time_decided=bool(record.decided_time),
    )


@router.post("/{meeting_id}/note")
def save_note(
    meeting_id: int,
    body: SaveMeetingNoteRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    record = _require_record(meeting_id, current_user.id, db)
    record.record_text = body.record_text
    db.commit()
    return {"ok": True}


@router.post("/{meeting_id}/decide-time")
def decide_time(
    meeting_id: int,
    body: DecideTimeRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    meeting = db.get(models.Meeting, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    if meeting.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Only the meeting creator can decide the time")

    record = meeting.record
    if not record:
        raise HTTPException(status_code=404, detail="Meeting record not found")

    decided_time = f"{body.date}  {body.start_time}~{body.end_time}"
    record.decided_time = decided_time
    record.notes = body.notes
    db.commit()

    # Send email notifications
    _send_notification_emails(meeting, decided_time, body.notes, db)

    return {"ok": True}


# ─── Attendance ──────────────────────────────────────────────────────────────

@router.get("/{meeting_id}/attendance")
def get_attendance(
    meeting_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    meeting = db.get(models.Meeting, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    # get all group members
    memberships = db.query(models.GroupMember).filter_by(group_id=meeting.group_id).all()
    result = []
    for m in memberships:
        att = db.query(models.Attendance).filter_by(
            meeting_id=meeting_id, user_id=m.user_id
        ).first()
        result.append({
            "user_id": m.user_id,
            "name": m.user.name,
            "absence_status": att.absence_status.value if att and att.absence_status else None,
            "mission_status": att.mission_status.value if att and att.mission_status else None,
        })
    return result


@router.post("/{meeting_id}/attendance")
def save_attendance(
    meeting_id: int,
    body: SaveAttendanceRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    meeting = db.get(models.Meeting, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    if meeting.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Only the meeting creator can update attendance")

    for item in body.items:
        att = db.query(models.Attendance).filter_by(
            meeting_id=meeting_id, user_id=item.user_id
        ).first()
        if not att:
            att = models.Attendance(meeting_id=meeting_id, user_id=item.user_id)
            db.add(att)
        if item.absence_status:
            att.absence_status = models.AbsenceStatus(item.absence_status)
        if item.mission_status:
            att.mission_status = models.MissionStatus(item.mission_status)

    db.commit()
    return {"ok": True}


# ─── Summary ─────────────────────────────────────────────────────────────────

@router.get("/{meeting_id}/summary", response_model=MeetingSummaryOut)
def get_summary(
    meeting_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    meeting = db.get(models.Meeting, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    record = meeting.record
    ontime, late, absent, done, undone, none_task = [], [], [], [], [], []

    all_att = db.query(models.Attendance).filter_by(meeting_id=meeting_id).all()
    for att in all_att:
        user = db.get(models.User, att.user_id)
        name = user.name if user else "?"
        if att.absence_status == models.AbsenceStatus.ontime:
            ontime.append(name)
        elif att.absence_status == models.AbsenceStatus.late:
            late.append(name)
        elif att.absence_status == models.AbsenceStatus.absent:
            absent.append(name)
        if att.mission_status == models.MissionStatus.done:
            done.append(name)
        elif att.mission_status == models.MissionStatus.undone:
            undone.append(name)
        elif att.mission_status == models.MissionStatus.none:
            none_task.append(name)

    return MeetingSummaryOut(
        meeting_name=meeting.name,
        decided_time=record.decided_time if record else "",
        record_text=record.record_text if record else "",
        notes=record.notes if record else "",
        ontime=ontime, late=late, absent=absent,
        done=done, undone=undone, none_task=none_task,
    )


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _require_record(meeting_id: int, user_id: int, db: Session) -> models.MeetingRecord:
    meeting = db.get(models.Meeting, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    if not db.query(models.GroupMember).filter_by(
        group_id=meeting.group_id, user_id=user_id
    ).first():
        raise HTTPException(status_code=403, detail="Not a member")
    if not meeting.record:
        raise HTTPException(status_code=404, detail="Record not found")
    return meeting.record


def _send_notification_emails(meeting: models.Meeting, decided_time: str, notes: str, db: Session):
    api_key = os.getenv("RESEND_API_KEY")
    from_email = os.getenv("FROM_EMAIL", "onboarding@resend.dev")
    if not api_key:
        return  # skip if not configured

    resend.api_key = api_key
    memberships = db.query(models.GroupMember).filter_by(group_id=meeting.group_id).all()

    for m in memberships:
        user = db.get(models.User, m.user_id)
        if not user:
            continue
        try:
            resend.Emails.send({
                "from": f"Meeting Assistant <{from_email}>",
                "to": [user.email],
                "subject": f"{meeting.name} 開會時間通知",
                "text": (
                    f"{meeting.name} 的開會時間為：\n{decided_time}\n\n"
                    f"備忘錄內容如下:\n{notes}"
                ),
            })
        except Exception:
            pass  # don't fail the request if email fails
