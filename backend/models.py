from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, DateTime, Boolean,
    ForeignKey, UniqueConstraint, Text, Enum
)
from sqlalchemy.orm import relationship
from database import Base
import enum


class GroupRole(str, enum.Enum):
    leader = "leader"
    member = "member"


class MeetingStatus(str, enum.Enum):
    unfinished = "unfinished"
    finished = "finished"


class AbsenceStatus(str, enum.Enum):
    ontime = "ontime"
    late = "late"
    absent = "absent"


class MissionStatus(str, enum.Enum):
    done = "done"
    undone = "undone"
    none = "none"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    group_memberships = relationship("GroupMember", back_populates="user")


class Group(Base):
    __tablename__ = "groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    invitation_code = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    members = relationship("GroupMember", back_populates="group")
    folders = relationship("Folder", back_populates="group")
    meetings = relationship("Meeting", back_populates="group")


class GroupMember(Base):
    __tablename__ = "group_members"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role = Column(Enum(GroupRole), default=GroupRole.member, nullable=False)
    joined_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (UniqueConstraint("group_id", "user_id"),)

    group = relationship("Group", back_populates="members")
    user = relationship("User", back_populates="group_memberships")


class Folder(Base):
    __tablename__ = "folders"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    group = relationship("Group", back_populates="folders")
    meetings = relationship("Meeting", back_populates="folder")


class Meeting(Base):
    __tablename__ = "meetings"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False)
    folder_id = Column(Integer, ForeignKey("folders.id"), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(Enum(MeetingStatus), default=MeetingStatus.unfinished, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    group = relationship("Group", back_populates="meetings")
    folder = relationship("Folder", back_populates="meetings")
    dates = relationship("MeetingDate", back_populates="meeting", cascade="all, delete-orphan")
    availability = relationship("Availability", back_populates="meeting", cascade="all, delete-orphan")
    attendance = relationship("Attendance", back_populates="meeting", cascade="all, delete-orphan")
    record = relationship("MeetingRecord", back_populates="meeting", uselist=False, cascade="all, delete-orphan")


class MeetingDate(Base):
    __tablename__ = "meeting_dates"

    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id"), nullable=False)
    date = Column(String, nullable=False)  # stored as "YYYY/MM/DD"

    __table_args__ = (UniqueConstraint("meeting_id", "date"),)

    meeting = relationship("Meeting", back_populates="dates")


class Availability(Base):
    __tablename__ = "availability"

    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(String, nullable=False)   # "YYYY/MM/DD"
    hour_slot = Column(Integer, nullable=False)  # 0=7:00-8:00 ... 15=22:00-23:00
    available = Column(Boolean, default=True, nullable=False)

    __table_args__ = (UniqueConstraint("meeting_id", "user_id", "date", "hour_slot"),)

    meeting = relationship("Meeting", back_populates="availability")


class Attendance(Base):
    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    absence_status = Column(Enum(AbsenceStatus), nullable=True)
    mission_status = Column(Enum(MissionStatus), nullable=True)

    __table_args__ = (UniqueConstraint("meeting_id", "user_id"),)

    meeting = relationship("Meeting", back_populates="attendance")


class MeetingRecord(Base):
    __tablename__ = "meeting_records"

    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id"), unique=True, nullable=False)
    record_text = Column(Text, default="")
    decided_time = Column(String, default="")   # e.g. "2025/06/01  09:00~10:00"
    notes = Column(Text, default="")

    meeting = relationship("Meeting", back_populates="record")
