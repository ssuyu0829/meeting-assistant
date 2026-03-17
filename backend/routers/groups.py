from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from database import get_db
from auth import get_current_user
import models

router = APIRouter(prefix="/api/groups", tags=["groups"])


class CreateGroupRequest(BaseModel):
    name: str
    invitation_code: str


class JoinGroupRequest(BaseModel):
    invitation_code: str


class MemberOut(BaseModel):
    user_id: int
    name: str
    email: str
    role: str


class GroupOut(BaseModel):
    id: int
    name: str
    invitation_code: str
    role: str
    member_count: int


class GroupDetailOut(BaseModel):
    id: int
    name: str
    invitation_code: str
    role: str
    members: List[MemberOut]


@router.get("", response_model=List[GroupOut])
def list_my_groups(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    memberships = (
        db.query(models.GroupMember)
        .filter_by(user_id=current_user.id)
        .all()
    )
    result = []
    for m in memberships:
        count = db.query(models.GroupMember).filter_by(group_id=m.group_id).count()
        result.append(GroupOut(
            id=m.group.id,
            name=m.group.name,
            invitation_code=m.group.invitation_code,
            role=m.role.value,
            member_count=count,
        ))
    return result


@router.post("", response_model=GroupOut)
def create_group(
    body: CreateGroupRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if len(body.name) > 5:
        raise HTTPException(status_code=400, detail="Group name must be 5 characters or fewer")
    if db.query(models.Group).filter_by(name=body.name).first():
        raise HTTPException(status_code=400, detail="Group name already taken")
    if db.query(models.Group).filter_by(invitation_code=body.invitation_code).first():
        raise HTTPException(status_code=400, detail="Invitation code already taken")

    group = models.Group(name=body.name, invitation_code=body.invitation_code)
    db.add(group)
    db.flush()

    membership = models.GroupMember(
        group_id=group.id, user_id=current_user.id, role=models.GroupRole.leader
    )
    db.add(membership)
    db.commit()
    db.refresh(group)

    return GroupOut(id=group.id, name=group.name, invitation_code=group.invitation_code,
                    role="leader", member_count=1)


@router.post("/join", response_model=GroupOut)
def join_group(
    body: JoinGroupRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    group = db.query(models.Group).filter_by(invitation_code=body.invitation_code).first()
    if not group:
        raise HTTPException(status_code=404, detail="Invitation code not found")

    already = db.query(models.GroupMember).filter_by(
        group_id=group.id, user_id=current_user.id
    ).first()
    if already:
        raise HTTPException(status_code=400, detail="You are already in this group")

    membership = models.GroupMember(
        group_id=group.id, user_id=current_user.id, role=models.GroupRole.member
    )
    db.add(membership)
    db.commit()

    count = db.query(models.GroupMember).filter_by(group_id=group.id).count()
    return GroupOut(id=group.id, name=group.name, invitation_code=group.invitation_code,
                    role="member", member_count=count)


@router.get("/{group_id}", response_model=GroupDetailOut)
def get_group(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    membership = db.query(models.GroupMember).filter_by(
        group_id=group_id, user_id=current_user.id
    ).first()
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of this group")

    group = db.get(models.Group, group_id)
    members = []
    for m in group.members:
        members.append(MemberOut(
            user_id=m.user_id,
            name=m.user.name,
            email=m.user.email,
            role=m.role.value,
        ))
    return GroupDetailOut(
        id=group.id,
        name=group.name,
        invitation_code=group.invitation_code,
        role=membership.role.value,
        members=members,
    )


@router.delete("/{group_id}/leave")
def leave_group(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    membership = db.query(models.GroupMember).filter_by(
        group_id=group_id, user_id=current_user.id
    ).first()
    if not membership:
        raise HTTPException(status_code=404, detail="Not a member")
    db.delete(membership)
    db.commit()
    return {"ok": True}
