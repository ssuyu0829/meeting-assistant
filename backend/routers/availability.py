from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Dict
from database import get_db
from auth import get_current_user
import models

router = APIRouter(prefix="/api/availability", tags=["availability"])

HOUR_SLOTS = 16  # slots 0–15 = 7:00–8:00 through 22:00–23:00


def slot_label(i: int) -> str:
    return f"{7 + i}:00-{8 + i}:00"


class SubmitAvailabilityRequest(BaseModel):
    # {date: [slot_index, ...]}  — only the available slots are listed
    slots: Dict[str, List[int]]


class AvailabilityGridOut(BaseModel):
    dates: List[str]
    hour_slots: List[str]
    # grid[date][slot] = list of user names who are available
    grid: Dict[str, Dict[int, List[str]]]
    # my own slots
    my_slots: Dict[str, List[int]]
    # member names who have submitted
    submitted_members: List[str]


@router.post("/{meeting_id}")
def submit_availability(
    meeting_id: int,
    body: SubmitAvailabilityRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    meeting = db.get(models.Meeting, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    if meeting.status == models.MeetingStatus.finished:
        raise HTTPException(status_code=400, detail="Meeting is already finished")

    valid_dates = {d.date for d in meeting.dates}

    # delete existing availability for this user+meeting
    db.query(models.Availability).filter_by(
        meeting_id=meeting_id, user_id=current_user.id
    ).delete()

    for date, slots in body.slots.items():
        if date not in valid_dates:
            continue
        for slot in slots:
            if 0 <= slot < HOUR_SLOTS:
                db.add(models.Availability(
                    meeting_id=meeting_id,
                    user_id=current_user.id,
                    date=date,
                    hour_slot=slot,
                    available=True,
                ))

    # track that this user has submitted (upsert in attendance table)
    att = db.query(models.Attendance).filter_by(
        meeting_id=meeting_id, user_id=current_user.id
    ).first()
    if not att:
        db.add(models.Attendance(meeting_id=meeting_id, user_id=current_user.id))

    db.commit()
    return {"ok": True}


@router.get("/{meeting_id}", response_model=AvailabilityGridOut)
def get_availability(
    meeting_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    meeting = db.get(models.Meeting, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    dates = sorted([d.date for d in meeting.dates])
    hour_slots = [slot_label(i) for i in range(HOUR_SLOTS)]

    # build grid
    grid: Dict[str, Dict[int, List[str]]] = {d: {i: [] for i in range(HOUR_SLOTS)} for d in dates}
    all_avail = db.query(models.Availability).filter_by(meeting_id=meeting_id).all()
    for a in all_avail:
        user = db.get(models.User, a.user_id)
        if user and a.date in grid:
            grid[a.date][a.hour_slot].append(user.name)

    # my slots
    my_slots: Dict[str, List[int]] = {d: [] for d in dates}
    my_avail = db.query(models.Availability).filter_by(
        meeting_id=meeting_id, user_id=current_user.id
    ).all()
    for a in my_avail:
        if a.date in my_slots:
            my_slots[a.date].append(a.hour_slot)

    # who has submitted
    submitted_user_ids = {
        a.user_id for a in db.query(models.Attendance).filter_by(meeting_id=meeting_id).all()
    }
    submitted_members = []
    for uid in submitted_user_ids:
        u = db.get(models.User, uid)
        if u:
            submitted_members.append(u.name)

    return AvailabilityGridOut(
        dates=dates,
        hour_slots=hour_slots,
        grid=grid,
        my_slots=my_slots,
        submitted_members=submitted_members,
    )
