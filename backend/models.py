"""
MySQL Database Models - SQLAlchemy ORM
Texnika Nazorat Tizimi
"""
from sqlalchemy import (
    Column, Integer, String, Text, Float, Boolean,
    DateTime, ForeignKey, Enum, Index, BigInteger
)
from sqlalchemy.orm import relationship, DeclarativeBase
from sqlalchemy.sql import func
import enum


class Base(DeclarativeBase):
    pass


# ═══════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════
class UserRole(str, enum.Enum):
    admin     = "admin"
    mexanik   = "mexanik"
    master    = "master"
    prorab    = "prorab"

class EquipmentStatus(str, enum.Enum):
    band       = "band"
    bosh       = "bosh"
    remont     = "remont"

class VolumeUnit(str, enum.Enum):
    m2 = "m2"
    m3 = "m3"

class AssignmentStatus(str, enum.Enum):
    active    = "active"
    completed = "completed"


# ═══════════════════════════════════════════════
# USERS
# ═══════════════════════════════════════════════
class User(Base):
    __tablename__ = "users"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    ism        = Column(String(100), nullable=False)
    familiya   = Column(String(100), nullable=False)
    telefon    = Column(String(20), nullable=False)
    login      = Column(String(50), unique=True, nullable=False, index=True)
    parol_hash = Column(String(255), nullable=False)
    role       = Column(Enum(UserRole), nullable=False, default=UserRole.master)
    is_active  = Column(Boolean, default=True)

    # Qo'shimcha ruxsatlar
    can_assign_equipment = Column(Boolean, default=False)  # texnika biriktira oladi
    can_edit_equipment   = Column(Boolean, default=False)  # texnika tahrirlay oladi

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    assignments   = relationship("EquipmentAssignment", foreign_keys="EquipmentAssignment.master_id", back_populates="master")
    work_reports  = relationship("WorkReport", back_populates="user")
    penalties_given    = relationship("Penalty", foreign_keys="Penalty.from_user_id", back_populates="from_user")
    penalties_received = relationship("Penalty", foreign_keys="Penalty.to_user_id",   back_populates="to_user")
    audit_logs    = relationship("AuditLog", back_populates="user")

    __table_args__ = (
        Index("ix_users_role", "role"),
        Index("ix_users_is_active", "is_active"),
    )

    @property
    def full_name(self):
        return f"{self.ism} {self.familiya}"

    def __repr__(self):
        return f"<User {self.login} ({self.role})>"


# ═══════════════════════════════════════════════
# EQUIPMENT (TEXNIKA)
# ═══════════════════════════════════════════════
class Equipment(Base):
    __tablename__ = "equipment"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    ichki_raqam    = Column(String(20), unique=True, nullable=False, index=True)
    tur            = Column(String(50), nullable=False)   # Samasvol, Katok, Greyder ...
    davlat_raqam   = Column(String(30), nullable=True)
    haydovchi_ism  = Column(String(150), nullable=True)
    haydovchi_tel  = Column(String(20), nullable=True)
    status         = Column(Enum(EquipmentStatus), default=EquipmentStatus.bosh, index=True)
    mulk           = Column(String(20), default="O'z")    # O'z, Nayom

    # Bo'shatish ma'lumotlari
    bosh_qilingan_vaqt  = Column(DateTime, nullable=True)
    bosh_qilish_sababi  = Column(Text, nullable=True)

    # Oxirgi assignment ma'lumotlari (denormalized tezlik uchun)
    oxirgi_master_id    = Column(Integer, ForeignKey("users.id"), nullable=True)
    oxirgi_prorab_id    = Column(Integer, ForeignKey("users.id"), nullable=True)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    assignments       = relationship("EquipmentAssignment", back_populates="equipment", order_by="EquipmentAssignment.created_at.desc()")
    history           = relationship("EquipmentHistory",    back_populates="equipment", order_by="EquipmentHistory.created_at.desc()")
    penalties         = relationship("Penalty",             back_populates="equipment")
    oxirgi_master     = relationship("User", foreign_keys=[oxirgi_master_id])
    oxirgi_prorab     = relationship("User", foreign_keys=[oxirgi_prorab_id])

    __table_args__ = (
        Index("ix_equipment_tur",    "tur"),
        Index("ix_equipment_status", "status"),
    )

    def __repr__(self):
        return f"<Equipment {self.ichki_raqam} ({self.tur})>"


# ═══════════════════════════════════════════════
# EQUIPMENT ASSIGNMENTS (BIRIKTIRUV)
# ═══════════════════════════════════════════════
class EquipmentAssignment(Base):
    __tablename__ = "equipment_assignments"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    equipment_id = Column(Integer, ForeignKey("equipment.id", ondelete="CASCADE"), nullable=False, index=True)
    master_id    = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    prorab_id    = Column(Integer, ForeignKey("users.id"), nullable=True)
    assigned_by  = Column(Integer, ForeignKey("users.id"), nullable=False)

    pk_boshlanish = Column(String(30), nullable=True)   # PK210+00
    pk_tugash     = Column(String(30), nullable=True)   # PK220+00
    sloy          = Column(String(20), nullable=True)   # 1-sloy
    status        = Column(Enum(AssignmentStatus), default=AssignmentStatus.active, index=True)

    boshlanish_vaqt  = Column(DateTime, server_default=func.now())
    tugash_vaqt      = Column(DateTime, nullable=True)
    bosh_qilish_sababi = Column(Text, nullable=True)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    equipment    = relationship("Equipment",   back_populates="assignments")
    master       = relationship("User",        foreign_keys=[master_id], back_populates="assignments")
    prorab       = relationship("User",        foreign_keys=[prorab_id])
    assigner     = relationship("User",        foreign_keys=[assigned_by])

    __table_args__ = (
        Index("ix_assignments_status",   "status"),
        Index("ix_assignments_eq_status","equipment_id", "status"),
    )


# ═══════════════════════════════════════════════
# EQUIPMENT HISTORY
# ═══════════════════════════════════════════════
class EquipmentHistory(Base):
    __tablename__ = "equipment_history"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    equipment_id = Column(Integer, ForeignKey("equipment.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id      = Column(Integer, ForeignKey("users.id"), nullable=True)
    action       = Column(String(50), nullable=False)   # band, bosh, remont, biriktir ...
    description  = Column(Text, nullable=True)
    pk_boshlanish = Column(String(30), nullable=True)
    pk_tugash     = Column(String(30), nullable=True)
    created_at   = Column(DateTime, server_default=func.now(), index=True)

    # Relationships
    equipment = relationship("Equipment", back_populates="history")
    user      = relationship("User")

    __table_args__ = (
        Index("ix_eq_history_eq_date", "equipment_id", "created_at"),
    )


# ═══════════════════════════════════════════════
# WORK REPORTS (ISH TOPSHIRISH)
# ═══════════════════════════════════════════════
class WorkReport(Base):
    __tablename__ = "work_reports"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    user_id       = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    assignment_id = Column(Integer, ForeignKey("equipment_assignments.id"), nullable=True)

    pk_boshlanish = Column(String(30), nullable=False)
    pk_tugash     = Column(String(30), nullable=False)
    sloy          = Column(String(30), nullable=False)   # 1-sloy, 2-sloy ...
    hajm          = Column(Float, nullable=False)
    hajm_turi     = Column(Enum(VolumeUnit), nullable=False, default=VolumeUnit.m2)

    # Hisob-kitob uchun (m3 => uzunlik*kenglik*qalinlik)
    uzunlik  = Column(Float, nullable=True)
    kenglik  = Column(Float, nullable=True)
    qalinlik = Column(Float, nullable=True)
    formula  = Column(String(100), nullable=True)

    tx_soni   = Column(Integer, default=1)   # nechta texnika bilan
    izoh      = Column(Text, nullable=True)
    sana      = Column(DateTime, server_default=func.now(), index=True)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    user       = relationship("User", back_populates="work_reports")
    assignment = relationship("EquipmentAssignment")

    __table_args__ = (
        Index("ix_reports_user_date", "user_id", "sana"),
    )


# ═══════════════════════════════════════════════
# PENALTIES (JALBALAR)
# ═══════════════════════════════════════════════
class Penalty(Base):
    __tablename__ = "penalties"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    from_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    to_user_id   = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    equipment_id = Column(Integer, ForeignKey("equipment.id"), nullable=True)
    sabab        = Column(Text, nullable=False)
    is_read      = Column(Boolean, default=False)
    created_at   = Column(DateTime, server_default=func.now(), index=True)

    # Relationships
    from_user = relationship("User", foreign_keys=[from_user_id], back_populates="penalties_given")
    to_user   = relationship("User", foreign_keys=[to_user_id],   back_populates="penalties_received")
    equipment = relationship("Equipment", back_populates="penalties")

    __table_args__ = (
        Index("ix_penalties_to_user", "to_user_id"),
    )


# ═══════════════════════════════════════════════
# AUDIT LOGS
# ═══════════════════════════════════════════════
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id          = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id     = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    action      = Column(String(100), nullable=False)
    entity_type = Column(String(50), nullable=True)   # equipment, user, assignment ...
    entity_id   = Column(Integer, nullable=True)
    description = Column(Text, nullable=True)
    ip_address  = Column(String(45), nullable=True)
    created_at  = Column(DateTime, server_default=func.now(), index=True)

    # Relationships
    user = relationship("User", back_populates="audit_logs")

    __table_args__ = (
        Index("ix_audit_date",        "created_at"),
        Index("ix_audit_entity",      "entity_type", "entity_id"),
        Index("ix_audit_user_date",   "user_id", "created_at"),
    )
