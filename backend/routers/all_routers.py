"""
Barcha API Routerlar
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, func, desc
from typing import List, Optional
from datetime import datetime

from database import get_db
from models import (User, Equipment, EquipmentAssignment, EquipmentHistory,
                    WorkReport, Penalty, AuditLog,
                    UserRole, EquipmentStatus, AssignmentStatus)
from auth import (get_current_user, require_admin, can_assign,
                  hash_password, verify_password, create_access_token,
                  check_own_resource)
from schemas import *

# ══════════════════════════════════════════════════
# AUTH ROUTER
# ══════════════════════════════════════════════════
auth_router = APIRouter(prefix="/api/auth", tags=["Auth"])

@auth_router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, request: Request, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.login == data.login, User.is_active == True).first()
    if not user or not verify_password(data.parol, user.parol_hash):
        raise HTTPException(401, "Login yoki parol noto'g'ri")

    token = create_access_token({"sub": str(user.id), "role": user.role})

    # Audit log
    log = AuditLog(user_id=user.id, action="login",
                   description=f"{user.full_name} tizimga kirdi",
                   ip_address=request.client.host if request.client else None)
    db.add(log)
    db.commit()

    return TokenResponse(
        access_token=token,
        user={"id": user.id, "ism": user.ism, "familiya": user.familiya,
              "login": user.login, "role": user.role, "telefon": user.telefon,
              "can_assign_equipment": user.can_assign_equipment,
              "can_edit_equipment": user.can_edit_equipment}
    )

@auth_router.get("/me")
def me(user: User = Depends(get_current_user)):
    return {"id": user.id, "ism": user.ism, "familiya": user.familiya,
            "login": user.login, "role": user.role, "telefon": user.telefon,
            "can_assign_equipment": user.can_assign_equipment,
            "can_edit_equipment": user.can_edit_equipment}


# ══════════════════════════════════════════════════
# USERS ROUTER
# ══════════════════════════════════════════════════
users_router = APIRouter(prefix="/api/users", tags=["Users"])

@users_router.get("/", response_model=List[UserOut])
def get_users(
    role: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin)
):
    q = db.query(User)
    if role:
        q = q.filter(User.role == role)
    if search:
        q = q.filter(or_(
            User.ism.ilike(f"%{search}%"),
            User.familiya.ilike(f"%{search}%"),
            User.login.ilike(f"%{search}%"),
        ))
    return q.order_by(User.role, User.familiya).all()

@users_router.post("/", response_model=UserOut, status_code=201)
def create_user(data: UserCreate, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    if db.query(User).filter(User.login == data.login).first():
        raise HTTPException(400, "Bu login band")
    user = User(
        ism=data.ism, familiya=data.familiya, telefon=data.telefon,
        login=data.login, parol_hash=hash_password(data.parol),
        role=data.role,
        can_assign_equipment=data.can_assign_equipment,
        can_edit_equipment=data.can_edit_equipment,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@users_router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: int, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    check_own_resource(current, user_id)
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(404, "Topilmadi")
    return u

@users_router.put("/{user_id}", response_model=UserOut)
def update_user(user_id: int, data: UserUpdate, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(404, "Topilmadi")
    for field, val in data.model_dump(exclude_none=True).items():
        if field == "parol":
            setattr(u, "parol_hash", hash_password(val))
        else:
            setattr(u, field, val)
    db.commit()
    db.refresh(u)
    return u

@users_router.patch("/{user_id}/permissions")
def set_permissions(user_id: int, data: UserPermissions, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(404, "Topilmadi")
    u.can_assign_equipment = data.can_assign_equipment
    u.can_edit_equipment   = data.can_edit_equipment
    db.commit()
    return {"message": "Ruxsatlar yangilandi"}

@users_router.delete("/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(404, "Topilmadi")
    u.is_active = False
    db.commit()
    return {"message": "Bloklandi"}


# ══════════════════════════════════════════════════
# EQUIPMENT ROUTER
# ══════════════════════════════════════════════════
eq_router = APIRouter(prefix="/api/equipment", tags=["Equipment"])

def _eq_out(eq: Equipment, include_history=False) -> dict:
    """Equipment dict formatiga o'tkazish"""
    from datetime import timezone
    bosh_muddat = None
    if eq.status == EquipmentStatus.bosh and eq.bosh_qilingan_vaqt:
        diff = datetime.utcnow() - eq.bosh_qilingan_vaqt.replace(tzinfo=None)
        hours   = int(diff.total_seconds() // 3600)
        minutes = int((diff.total_seconds() % 3600) // 60)
        bosh_muddat = f"{hours} soat {minutes} daqiqa"

    result = {
        "id": eq.id, "ichki_raqam": eq.ichki_raqam, "tur": eq.tur,
        "davlat_raqam": eq.davlat_raqam, "haydovchi_ism": eq.haydovchi_ism,
        "haydovchi_tel": eq.haydovchi_tel, "status": eq.status, "mulk": eq.mulk,
        "bosh_qilingan_vaqt": eq.bosh_qilingan_vaqt,
        "bosh_qilish_sababi": eq.bosh_qilish_sababi,
        "bosh_turgan_muddat": bosh_muddat,
        "created_at": eq.created_at,
        "oxirgi_master": None, "oxirgi_prorab": None,
        "joriy_master": None, "joriy_pk": None,
    }
    if eq.oxirgi_master:
        result["oxirgi_master"] = {"id": eq.oxirgi_master.id, "ism": eq.oxirgi_master.ism,
                                    "familiya": eq.oxirgi_master.familiya,
                                    "telefon": eq.oxirgi_master.telefon}
    if eq.oxirgi_prorab:
        result["oxirgi_prorab"] = {"id": eq.oxirgi_prorab.id, "ism": eq.oxirgi_prorab.ism,
                                    "familiya": eq.oxirgi_prorab.familiya,
                                    "telefon": eq.oxirgi_prorab.telefon}
    # Joriy assignment
    active = next((a for a in eq.assignments if a.status == AssignmentStatus.active), None)
    if active:
        result["joriy_master"] = active.master.full_name if active.master else None
        result["joriy_pk"]     = f"{active.pk_boshlanish} → {active.pk_tugash}" if active.pk_boshlanish else None
        result["joriy_sloy"]   = active.sloy
    return result

@eq_router.get("/")
def get_equipment(
    status: Optional[str] = None,
    tur: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user)
):
    q = db.query(Equipment).options(
        joinedload(Equipment.oxirgi_master),
        joinedload(Equipment.oxirgi_prorab),
        joinedload(Equipment.assignments).joinedload(EquipmentAssignment.master),
    )
    if status:
        q = q.filter(Equipment.status == status)
    if tur:
        q = q.filter(Equipment.tur == tur)
    if search:
        q = q.filter(or_(
            Equipment.ichki_raqam.ilike(f"%{search}%"),
            Equipment.davlat_raqam.ilike(f"%{search}%"),
            Equipment.tur.ilike(f"%{search}%"),
        ))
    return [_eq_out(e) for e in q.order_by(Equipment.ichki_raqam).all()]

@eq_router.post("/", status_code=201)
def create_equipment(data: EquipmentCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role not in [UserRole.admin, UserRole.mexanik] and not user.can_edit_equipment:
        raise HTTPException(403, "Ruxsat yo'q")
    if db.query(Equipment).filter(Equipment.ichki_raqam == data.ichki_raqam).first():
        raise HTTPException(400, "Bu raqam band")
    eq = Equipment(**data.model_dump())
    db.add(eq)
    db.flush()
    # History
    db.add(AuditLog(user_id=user.id, action="equipment_create",
                    entity_type="equipment", entity_id=eq.id,
                    description=f"{eq.ichki_raqam} texnika qo'shildi"))
    db.commit()
    db.refresh(eq)
    return _eq_out(eq)

@eq_router.get("/{eq_id}")
def get_equipment_detail(eq_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    eq = db.query(Equipment).options(
        joinedload(Equipment.oxirgi_master),
        joinedload(Equipment.oxirgi_prorab),
        joinedload(Equipment.assignments).joinedload(EquipmentAssignment.master),
        joinedload(Equipment.history).joinedload(EquipmentHistory.user),
        joinedload(Equipment.penalties),
    ).filter(Equipment.id == eq_id).first()
    if not eq:
        raise HTTPException(404, "Topilmadi")
    result = _eq_out(eq)
    # Tarix
    result["tarix"] = [{"id": h.id, "action": h.action, "description": h.description,
                         "pk": f"{h.pk_boshlanish}→{h.pk_tugash}" if h.pk_boshlanish else None,
                         "user": h.user.full_name if h.user else None,
                         "created_at": h.created_at} for h in eq.history[:20]]
    # Jalbalar
    result["jalbalar_soni"] = len(eq.penalties)
    return result

@eq_router.put("/{eq_id}")
def update_equipment(eq_id: int, data: EquipmentUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role not in [UserRole.admin, UserRole.mexanik] and not user.can_edit_equipment:
        raise HTTPException(403, "Ruxsat yo'q")
    eq = db.query(Equipment).filter(Equipment.id == eq_id).first()
    if not eq:
        raise HTTPException(404, "Topilmadi")
    for field, val in data.model_dump(exclude_none=True).items():
        setattr(eq, field, val)
    db.add(AuditLog(user_id=user.id, action="equipment_update",
                    entity_type="equipment", entity_id=eq_id,
                    description=f"{eq.ichki_raqam} yangilandi"))
    db.commit()
    db.refresh(eq)
    return _eq_out(eq)

@eq_router.patch("/{eq_id}/status")
def update_equipment_status(eq_id: int, data: EquipmentStatusUpdate,
                             db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role not in [UserRole.admin, UserRole.mexanik]:
        raise HTTPException(403, "Ruxsat yo'q")
    eq = db.query(Equipment).filter(Equipment.id == eq_id).first()
    if not eq:
        raise HTTPException(404, "Topilmadi")
    old_status = eq.status
    eq.status = data.status
    if data.status == EquipmentStatus.bosh:
        eq.bosh_qilingan_vaqt  = datetime.utcnow()
        eq.bosh_qilish_sababi  = data.sabab
    # History
    db.add(EquipmentHistory(equipment_id=eq_id, user_id=user.id,
                             action=data.status,
                             description=data.sabab or f"Status: {old_status}→{data.status}"))
    db.add(AuditLog(user_id=user.id, action="equipment_status",
                    entity_type="equipment", entity_id=eq_id,
                    description=f"{eq.ichki_raqam}: {old_status}→{data.status}"))
    db.commit()
    return {"message": "Status yangilandi", "status": data.status}


# ══════════════════════════════════════════════════
# ASSIGNMENTS ROUTER
# ══════════════════════════════════════════════════
assign_router = APIRouter(prefix="/api/assignments", tags=["Assignments"])

@assign_router.get("/")
def get_assignments(
    status: Optional[str] = None,
    master_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user)
):
    q = db.query(EquipmentAssignment).options(
        joinedload(EquipmentAssignment.equipment),
        joinedload(EquipmentAssignment.master),
        joinedload(EquipmentAssignment.prorab),
    )
    # Master faqat o'zini ko'radi
    if current.role in [UserRole.master, UserRole.prorab]:
        q = q.filter(EquipmentAssignment.master_id == current.id)
    elif master_id:
        q = q.filter(EquipmentAssignment.master_id == master_id)
    if status:
        q = q.filter(EquipmentAssignment.status == status)
    rows = q.order_by(desc(EquipmentAssignment.created_at)).limit(100).all()
    return [{
        "id": a.id, "status": a.status,
        "pk_boshlanish": a.pk_boshlanish, "pk_tugash": a.pk_tugash, "sloy": a.sloy,
        "boshlanish_vaqt": a.boshlanish_vaqt, "tugash_vaqt": a.tugash_vaqt,
        "bosh_qilish_sababi": a.bosh_qilish_sababi,
        "equipment": {"id": a.equipment.id, "ichki_raqam": a.equipment.ichki_raqam,
                       "tur": a.equipment.tur, "davlat_raqam": a.equipment.davlat_raqam,
                       "haydovchi_ism": a.equipment.haydovchi_ism,
                       "haydovchi_tel": a.equipment.haydovchi_tel} if a.equipment else None,
        "master": {"id": a.master.id, "ism": a.master.ism, "familiya": a.master.familiya,
                    "telefon": a.master.telefon} if a.master else None,
        "prorab": {"id": a.prorab.id, "ism": a.prorab.ism, "familiya": a.prorab.familiya,
                    "telefon": a.prorab.telefon} if a.prorab else None,
    } for a in rows]

@assign_router.post("/", status_code=201)
def create_assignment(data: AssignmentCreate, request: Request,
                       db: Session = Depends(get_db), user: User = Depends(can_assign)):
    eq = db.query(Equipment).filter(Equipment.id == data.equipment_id).first()
    if not eq:
        raise HTTPException(404, "Texnika topilmadi")
    if eq.status == EquipmentStatus.remont:
        raise HTTPException(400, "Texnika remontda")

    master = db.query(User).filter(User.id == data.master_id, User.is_active == True).first()
    if not master:
        raise HTTPException(404, "Master topilmadi")

    # Avvalgi aktiv assignment ni tugatish
    prev = db.query(EquipmentAssignment).filter(
        EquipmentAssignment.equipment_id == data.equipment_id,
        EquipmentAssignment.status == AssignmentStatus.active
    ).first()
    if prev:
        prev.status     = AssignmentStatus.completed
        prev.tugash_vaqt = datetime.utcnow()
        prev.bosh_qilish_sababi = "Yangi biriktiruv bilan almashtirildi"

    # Yangi assignment
    a = EquipmentAssignment(
        equipment_id=data.equipment_id, master_id=data.master_id,
        prorab_id=data.prorab_id, assigned_by=user.id,
        pk_boshlanish=data.pk_boshlanish, pk_tugash=data.pk_tugash,
        sloy=data.sloy, status=AssignmentStatus.active,
    )
    db.add(a)

    # Texnika holatini yangilash
    eq.status           = EquipmentStatus.band
    eq.oxirgi_master_id = data.master_id
    if data.prorab_id:
        eq.oxirgi_prorab_id = data.prorab_id

    # History
    pk_info = f"{data.pk_boshlanish}→{data.pk_tugash}" if data.pk_boshlanish else ""
    db.add(EquipmentHistory(equipment_id=eq.id, user_id=user.id, action="band",
                             description=f"{master.full_name}ga biriktirildi {pk_info}",
                             pk_boshlanish=data.pk_boshlanish, pk_tugash=data.pk_tugash))
    db.add(AuditLog(user_id=user.id, action="assignment_create",
                    entity_type="equipment", entity_id=eq.id,
                    description=f"{eq.ichki_raqam} → {master.full_name}",
                    ip_address=request.client.host if request.client else None))
    db.commit()
    db.refresh(a)
    return {"id": a.id, "message": "Biriktirildi"}

@assign_router.post("/{assign_id}/complete")
def complete_assignment(assign_id: int, data: AssignmentComplete,
                         db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    a = db.query(EquipmentAssignment).options(
        joinedload(EquipmentAssignment.equipment)
    ).filter(EquipmentAssignment.id == assign_id).first()
    if not a:
        raise HTTPException(404, "Topilmadi")
    # Faqat admin, mexanik yoki biriktirilgan master tugatishi mumkin
    if user.role not in [UserRole.admin, UserRole.mexanik]:
        if a.master_id != user.id:
            raise HTTPException(403, "Ruxsat yo'q")

    a.status      = AssignmentStatus.completed
    a.tugash_vaqt = datetime.utcnow()
    a.bosh_qilish_sababi = data.sabab

    eq = a.equipment
    eq.status                = EquipmentStatus.bosh
    eq.bosh_qilingan_vaqt    = datetime.utcnow()
    eq.bosh_qilish_sababi    = data.sabab

    db.add(EquipmentHistory(equipment_id=eq.id, user_id=user.id, action="bosh",
                             description=data.sabab or "Ish yakunlandi",
                             pk_boshlanish=a.pk_boshlanish, pk_tugash=a.pk_tugash))
    db.commit()
    return {"message": "Tugallandi", "sabab": data.sabab}


# ══════════════════════════════════════════════════
# WORK REPORTS ROUTER
# ══════════════════════════════════════════════════
report_router = APIRouter(prefix="/api/reports", tags=["Work Reports"])

@report_router.get("/")
def get_reports(
    user_id: Optional[int] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user)
):
    q = db.query(WorkReport).options(joinedload(WorkReport.user))
    if current.role in [UserRole.master, UserRole.prorab]:
        q = q.filter(WorkReport.user_id == current.id)
    elif user_id:
        q = q.filter(WorkReport.user_id == user_id)
    rows = q.order_by(desc(WorkReport.sana)).limit(limit).all()
    return [{
        "id": r.id, "pk_boshlanish": r.pk_boshlanish, "pk_tugash": r.pk_tugash,
        "sloy": r.sloy, "hajm": r.hajm, "hajm_turi": r.hajm_turi,
        "uzunlik": r.uzunlik, "kenglik": r.kenglik, "qalinlik": r.qalinlik,
        "formula": r.formula, "tx_soni": r.tx_soni, "izoh": r.izoh,
        "sana": r.sana,
        "user": {"id": r.user.id, "ism": r.user.ism, "familiya": r.user.familiya} if r.user else None,
    } for r in rows]

@report_router.post("/", status_code=201)
def create_report(data: WorkReportCreate, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    # Hajm hisoblash
    formula = None
    if data.hajm_turi == VolumeUnit.m3 and data.uzunlik and data.kenglik and data.qalinlik:
        calculated = data.uzunlik * data.kenglik * data.qalinlik
        formula = f"{data.uzunlik}×{data.kenglik}×{data.qalinlik}={calculated:.2f}m³"
        data_dict = data.model_dump()
        data_dict["hajm"] = calculated
    elif data.uzunlik and data.kenglik:
        calculated = data.uzunlik * data.kenglik
        formula = f"{data.uzunlik}×{data.kenglik}={calculated:.1f}m²"
        data_dict = data.model_dump()
        data_dict["hajm"] = calculated
    else:
        data_dict = data.model_dump()

    r = WorkReport(user_id=user.id, formula=formula, **{
        k: v for k,v in data_dict.items() if k not in ["assignment_id"]
    })
    r.assignment_id = data.assignment_id
    db.add(r)
    db.add(AuditLog(user_id=user.id, action="report_create",
                    description=f"{user.full_name}: {data.pk_boshlanish}→{data.pk_tugash} {data.sloy}"))
    db.commit()
    db.refresh(r)
    return {"id": r.id, "hajm": r.hajm, "formula": r.formula, "message": "Saqlandi"}

@report_router.get("/stats/me")
def my_stats(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """O'z statistikam"""
    uid = user.id
    total_m2 = db.query(func.sum(WorkReport.hajm)).filter(
        WorkReport.user_id == uid, WorkReport.hajm_turi == VolumeUnit.m2).scalar() or 0
    total_m3 = db.query(func.sum(WorkReport.hajm)).filter(
        WorkReport.user_id == uid, WorkReport.hajm_turi == VolumeUnit.m3).scalar() or 0
    total_count = db.query(func.count(WorkReport.id)).filter(WorkReport.user_id == uid).scalar() or 0
    penalties   = db.query(func.count(Penalty.id)).filter(Penalty.to_user_id == uid).scalar() or 0
    return {"jami_m2": round(total_m2,1), "jami_m3": round(total_m3,2),
            "hisobotlar": total_count, "jalbalar": penalties}


# ══════════════════════════════════════════════════
# PENALTIES ROUTER
# ══════════════════════════════════════════════════
penalty_router = APIRouter(prefix="/api/penalties", tags=["Penalties"])

@penalty_router.get("/")
def get_penalties(
    user_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user)
):
    q = db.query(Penalty).options(
        joinedload(Penalty.from_user),
        joinedload(Penalty.to_user),
        joinedload(Penalty.equipment),
    )
    if current.role in [UserRole.master, UserRole.prorab]:
        q = q.filter(Penalty.to_user_id == current.id)
    elif user_id:
        q = q.filter(or_(Penalty.to_user_id == user_id, Penalty.from_user_id == user_id))
    rows = q.order_by(desc(Penalty.created_at)).limit(100).all()
    return [{
        "id": p.id, "sabab": p.sabab, "is_read": p.is_read, "created_at": p.created_at,
        "from_user": {"id": p.from_user.id, "ism": p.from_user.ism,
                       "familiya": p.from_user.familiya} if p.from_user else None,
        "to_user":   {"id": p.to_user.id,   "ism": p.to_user.ism,
                       "familiya": p.to_user.familiya,
                       "telefon": p.to_user.telefon} if p.to_user else None,
        "equipment": {"id": p.equipment.id, "ichki_raqam": p.equipment.ichki_raqam,
                       "tur": p.equipment.tur} if p.equipment else None,
    } for p in rows]

@penalty_router.post("/", status_code=201)
def create_penalty(data: PenaltyCreate, db: Session = Depends(get_db),
                    user: User = Depends(get_current_user)):
    target = db.query(User).filter(User.id == data.to_user_id, User.is_active == True).first()
    if not target:
        raise HTTPException(404, "Foydalanuvchi topilmadi")
    p = Penalty(from_user_id=user.id, to_user_id=data.to_user_id,
                equipment_id=data.equipment_id, sabab=data.sabab)
    db.add(p)
    db.add(AuditLog(user_id=user.id, action="penalty_create",
                    entity_type="user", entity_id=data.to_user_id,
                    description=f"{user.full_name} → {target.full_name}: {data.sabab[:50]}"))
    db.commit()
    db.refresh(p)
    return {"id": p.id, "message": "Jalba yozildi"}

@penalty_router.patch("/{penalty_id}/read")
def mark_read(penalty_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    p = db.query(Penalty).filter(Penalty.id == penalty_id, Penalty.to_user_id == user.id).first()
    if not p:
        raise HTTPException(404, "Topilmadi")
    p.is_read = True
    db.commit()
    return {"message": "O'qildi"}


# ══════════════════════════════════════════════════
# SEARCH ROUTER
# ══════════════════════════════════════════════════
search_router = APIRouter(prefix="/api/search", tags=["Search"])

@search_router.get("/")
def global_search(q: str = Query(..., min_length=1),
                   db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    results = []

    # Texnikalar
    eqs = db.query(Equipment).options(
        joinedload(Equipment.oxirgi_master),
        joinedload(Equipment.assignments).joinedload(EquipmentAssignment.master)
    ).filter(or_(
        Equipment.ichki_raqam.ilike(f"%{q}%"),
        Equipment.davlat_raqam.ilike(f"%{q}%"),
        Equipment.tur.ilike(f"%{q}%"),
        Equipment.haydovchi_ism.ilike(f"%{q}%"),
    )).limit(10).all()

    for eq in eqs:
        active = next((a for a in eq.assignments if a.status == AssignmentStatus.active), None)
        results.append({
            "type": "equipment", "id": eq.id,
            "title": f"{eq.ichki_raqam} — {eq.tur}",
            "subtitle": eq.davlat_raqam,
            "status": eq.status,
            "extra": {
                "master": active.master.full_name if active and active.master else None,
                "pk": f"{active.pk_boshlanish}→{active.pk_tugash}" if active and active.pk_boshlanish else None,
                "haydovchi": eq.haydovchi_ism, "haydovchi_tel": eq.haydovchi_tel,
            }
        })

    # Foydalanuvchilar (faqat admin)
    if user.role == UserRole.admin:
        users = db.query(User).filter(or_(
            User.ism.ilike(f"%{q}%"),
            User.familiya.ilike(f"%{q}%"),
            User.login.ilike(f"%{q}%"),
            User.telefon.ilike(f"%{q}%"),
        )).limit(5).all()
        for u in users:
            results.append({
                "type": "user", "id": u.id,
                "title": u.full_name, "subtitle": u.role,
                "status": "active" if u.is_active else "blocked",
                "extra": {"telefon": u.telefon, "login": u.login}
            })

    return results


# ══════════════════════════════════════════════════
# AUDIT ROUTER
# ══════════════════════════════════════════════════
audit_router = APIRouter(prefix="/api/audit", tags=["Audit"])

@audit_router.get("/")
def get_audit_logs(
    limit: int = 50,
    user_id: Optional[int] = None,
    action: Optional[str] = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin)
):
    q = db.query(AuditLog).options(joinedload(AuditLog.user))
    if user_id:
        q = q.filter(AuditLog.user_id == user_id)
    if action:
        q = q.filter(AuditLog.action == action)
    rows = q.order_by(desc(AuditLog.created_at)).limit(limit).all()
    return [{
        "id": r.id, "action": r.action, "description": r.description,
        "entity_type": r.entity_type, "entity_id": r.entity_id,
        "created_at": r.created_at,
        "user": {"id": r.user.id, "ism": r.user.ism,
                  "familiya": r.user.familiya} if r.user else None,
    } for r in rows]
