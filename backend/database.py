"""
MySQL Database Connection - SQLAlchemy
"""
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from models import Base
import os

# ── .env dan yoki environment dan ──
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_USER = os.getenv("DB_USER", "root")
DB_PASS = os.getenv("DB_PASS", "password")
DB_NAME = os.getenv("DB_NAME", "texnika_nazorat")

DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"

engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Jadvallarni yaratish va boshlang'ich ma'lumotlar"""
    Base.metadata.create_all(bind=engine)
    _seed_data()


def _seed_data():
    """Boshlang'ich admin va namuna ma'lumotlar"""
    from models import User, UserRole
    from auth import hash_password
    db = SessionLocal()
    try:
        # Admin bor-yo'qligini tekshirish
        existing = db.query(User).filter(User.login == "admin").first()
        if existing:
            return

        # Admin
        admin = User(
            ism="Administrator", familiya="Tizim",
            telefon="+998901234567", login="admin",
            parol_hash=hash_password("admin123"),
            role=UserRole.admin,
            can_assign_equipment=True,
            can_edit_equipment=True,
        )
        db.add(admin)

        # Namuna masterlar
        sample_users = [
            ("Fayzullo", "Nosiraliyev", "+998901234567", "fayzullo", "1234", UserRole.master),
            ("Jaloliddin", "Urazimbatov", "+998907654321", "jaloliddin", "1234", UserRole.master),
            ("Sherxon", "Xolmatov", "+998931112233", "sherxon", "1234", UserRole.master),
            ("Bobur", "Soqiev", "+998905556677", "bobur", "1234", UserRole.prorab),
            ("Xudoyor", "Qilichov", "+998911122334", "xudoyor", "1234", UserRole.master),
            ("Mirzo", "Texnikov", "+998907770001", "mirzo", "1234", UserRole.mexanik),
        ]
        for ism, fam, tel, login, parol, role in sample_users:
            u = User(ism=ism, familiya=fam, telefon=tel, login=login,
                     parol_hash=hash_password(parol), role=role,
                     can_assign_equipment=(role == UserRole.mexanik))
            db.add(u)

        db.commit()

        # Namuna texnikalar
        from models import Equipment, EquipmentStatus
        txs = [
            ("401", "Katok",      "01A401KK", "Abdurahmon Xoliqov", "+998901110001"),
            ("402", "Katok",      "01A402KK", "Sardor Rahimov",     "+998901110002"),
            ("501", "Samasvol",   "01A501VV", "Jasur Qodirov",      "+998901110003"),
            ("502", "Samasvol",   "01A502VV", "Sherzod Toshmatov",  "+998901110004"),
            ("503", "Samasvol",   "01B503HH", "Nodir Ismoilov",     "+998901110005"),
            ("601", "Greyder",    "01C601GG", "Ulugbek Mirzaev",    "+998901110006"),
            ("701", "Vadavoz",    "01D701MM", "Mansur Ergashev",    "+998901110007"),
            ("702", "Vadavoz",    "01D702MM", "Kamol Yunusov",      "+998901110008"),
            ("801", "Pagruzchik", "01E801PP", "Zafar Nazarov",      "+998901110009"),
        ]
        for raqam, tur, davlat, haydovchi, tel in txs:
            eq = Equipment(ichki_raqam=raqam, tur=tur,
                           davlat_raqam=davlat,
                           haydovchi_ism=haydovchi,
                           haydovchi_tel=tel,
                           status=EquipmentStatus.bosh)
            db.add(eq)
        db.commit()
        print("✅ Boshlang'ich ma'lumotlar kiritildi")
    except Exception as e:
        db.rollback()
        print(f"Seed xatolik: {e}")
    finally:
        db.close()
