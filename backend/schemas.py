"""
Pydantic Schemas - Request/Response validation
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime
from models import UserRole, EquipmentStatus, VolumeUnit, AssignmentStatus


# ═══════════════════════════════════════════════
# AUTH
# ═══════════════════════════════════════════════
class LoginRequest(BaseModel):
    login: str
    parol: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


# ═══════════════════════════════════════════════
# USER
# ═══════════════════════════════════════════════
class UserCreate(BaseModel):
    ism:        str = Field(..., min_length=2, max_length=100)
    familiya:   str = Field(..., min_length=2, max_length=100)
    telefon:    str = Field(..., min_length=9, max_length=20)
    login:      str = Field(..., min_length=3, max_length=50)
    parol:      str = Field(..., min_length=3, max_length=50)
    role:       UserRole = UserRole.master
    can_assign_equipment: bool = False
    can_edit_equipment:   bool = False

class UserUpdate(BaseModel):
    ism:        Optional[str] = None
    familiya:   Optional[str] = None
    telefon:    Optional[str] = None
    role:       Optional[UserRole] = None
    is_active:  Optional[bool] = None
    can_assign_equipment: Optional[bool] = None
    can_edit_equipment:   Optional[bool] = None
    parol:      Optional[str] = None

class UserPermissions(BaseModel):
    can_assign_equipment: bool = False
    can_edit_equipment:   bool = False

class UserOut(BaseModel):
    id:         int
    ism:        str
    familiya:   str
    telefon:    str
    login:      str
    role:       UserRole
    is_active:  bool
    can_assign_equipment: bool
    can_edit_equipment:   bool
    created_at: datetime
    full_name:  str = ""

    model_config = {"from_attributes": True}

    @field_validator("full_name", mode="before")
    @classmethod
    def set_full_name(cls, v, info):
        data = info.data
        if "ism" in data and "familiya" in data:
            return f"{data['ism']} {data['familiya']}"
        return v


# ═══════════════════════════════════════════════
# EQUIPMENT
# ═══════════════════════════════════════════════
class EquipmentCreate(BaseModel):
    ichki_raqam:   str  = Field(..., min_length=1, max_length=20)
    tur:           str  = Field(..., min_length=2, max_length=50)
    davlat_raqam:  Optional[str] = None
    haydovchi_ism: Optional[str] = None
    haydovchi_tel: Optional[str] = None
    mulk:          str  = "O'z"

class EquipmentUpdate(BaseModel):
    tur:            Optional[str] = None
    davlat_raqam:   Optional[str] = None
    haydovchi_ism:  Optional[str] = None
    haydovchi_tel:  Optional[str] = None
    mulk:           Optional[str] = None

class EquipmentStatusUpdate(BaseModel):
    status: EquipmentStatus
    sabab:  Optional[str] = None

class EquipmentOut(BaseModel):
    id:             int
    ichki_raqam:    str
    tur:            str
    davlat_raqam:   Optional[str]
    haydovchi_ism:  Optional[str]
    haydovchi_tel:  Optional[str]
    status:         EquipmentStatus
    mulk:           str
    bosh_qilingan_vaqt:  Optional[datetime]
    bosh_qilish_sababi:  Optional[str]
    oxirgi_master:  Optional[dict] = None
    oxirgi_prorab:  Optional[dict] = None
    bosh_turgan_muddat: Optional[str] = None
    created_at:     datetime

    model_config = {"from_attributes": True}


# ═══════════════════════════════════════════════
# ASSIGNMENT
# ═══════════════════════════════════════════════
class AssignmentCreate(BaseModel):
    equipment_id:  int
    master_id:     int
    prorab_id:     Optional[int] = None
    pk_boshlanish: Optional[str] = None
    pk_tugash:     Optional[str] = None
    sloy:          Optional[str] = None

class AssignmentComplete(BaseModel):
    sabab: Optional[str] = "Ish yakunlandi"

class AssignmentOut(BaseModel):
    id:            int
    equipment_id:  int
    master_id:     int
    prorab_id:     Optional[int]
    pk_boshlanish: Optional[str]
    pk_tugash:     Optional[str]
    sloy:          Optional[str]
    status:        AssignmentStatus
    boshlanish_vaqt: datetime
    tugash_vaqt:   Optional[datetime]
    bosh_qilish_sababi: Optional[str]

    # Nested
    equipment:  Optional[dict] = None
    master:     Optional[dict] = None
    prorab:     Optional[dict] = None

    model_config = {"from_attributes": True}


# ═══════════════════════════════════════════════
# WORK REPORT
# ═══════════════════════════════════════════════
class WorkReportCreate(BaseModel):
    pk_boshlanish: str = Field(..., min_length=1)
    pk_tugash:     str = Field(..., min_length=1)
    sloy:          str = Field(..., min_length=1)
    hajm:          float = Field(..., gt=0)
    hajm_turi:     VolumeUnit = VolumeUnit.m2
    uzunlik:       Optional[float] = None
    kenglik:       Optional[float] = None
    qalinlik:      Optional[float] = None
    tx_soni:       int = 1
    assignment_id: Optional[int] = None
    izoh:          Optional[str] = None

class WorkReportOut(BaseModel):
    id:            int
    user_id:       int
    pk_boshlanish: str
    pk_tugash:     str
    sloy:          str
    hajm:          float
    hajm_turi:     VolumeUnit
    uzunlik:       Optional[float]
    kenglik:       Optional[float]
    qalinlik:      Optional[float]
    formula:       Optional[str]
    tx_soni:       int
    izoh:          Optional[str]
    sana:          datetime
    user:          Optional[dict] = None

    model_config = {"from_attributes": True}


# ═══════════════════════════════════════════════
# PENALTY
# ═══════════════════════════════════════════════
class PenaltyCreate(BaseModel):
    to_user_id:   int
    equipment_id: Optional[int] = None
    sabab:        str = Field(..., min_length=5)

class PenaltyOut(BaseModel):
    id:           int
    from_user_id: int
    to_user_id:   int
    equipment_id: Optional[int]
    sabab:        str
    is_read:      bool
    created_at:   datetime
    from_user:    Optional[dict] = None
    to_user:      Optional[dict] = None
    equipment:    Optional[dict] = None

    model_config = {"from_attributes": True}


# ═══════════════════════════════════════════════
# SEARCH
# ═══════════════════════════════════════════════
class SearchResult(BaseModel):
    type:        str   # equipment, user
    id:          int
    title:       str
    subtitle:    Optional[str]
    status:      Optional[str]
    extra:       Optional[dict] = None
