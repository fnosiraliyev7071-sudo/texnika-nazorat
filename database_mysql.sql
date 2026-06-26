-- ══════════════════════════════════════════════
-- TEXNIKA NAZORAT TIZIMI — MySQL 8.0
-- ══════════════════════════════════════════════

CREATE DATABASE IF NOT EXISTS texnika_nazorat
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE texnika_nazorat;

-- ── USERS ────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id                   INT AUTO_INCREMENT PRIMARY KEY,
    ism                  VARCHAR(100) NOT NULL,
    familiya             VARCHAR(100) NOT NULL,
    telefon              VARCHAR(20)  NOT NULL,
    login                VARCHAR(50)  NOT NULL UNIQUE,
    parol_hash           VARCHAR(255) NOT NULL,
    role                 ENUM('admin','mexanik','master','prorab') NOT NULL DEFAULT 'master',
    is_active            TINYINT(1)   NOT NULL DEFAULT 1,
    can_assign_equipment TINYINT(1)   NOT NULL DEFAULT 0,
    can_edit_equipment   TINYINT(1)   NOT NULL DEFAULT 0,
    created_at           DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at           DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX ix_users_login     (login),
    INDEX ix_users_role      (role),
    INDEX ix_users_is_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ── EQUIPMENT ────────────────────────────────
CREATE TABLE IF NOT EXISTS equipment (
    id                   INT AUTO_INCREMENT PRIMARY KEY,
    ichki_raqam          VARCHAR(20)  NOT NULL UNIQUE,
    tur                  VARCHAR(50)  NOT NULL,
    davlat_raqam         VARCHAR(30)  NULL,
    haydovchi_ism        VARCHAR(150) NULL,
    haydovchi_tel        VARCHAR(20)  NULL,
    status               ENUM('band','bosh','remont') NOT NULL DEFAULT 'bosh',
    mulk                 VARCHAR(20)  NOT NULL DEFAULT 'O''z',
    bosh_qilingan_vaqt   DATETIME     NULL,
    bosh_qilish_sababi   TEXT         NULL,
    oxirgi_master_id     INT          NULL,
    oxirgi_prorab_id     INT          NULL,
    created_at           DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at           DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (oxirgi_master_id) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (oxirgi_prorab_id) REFERENCES users(id) ON DELETE SET NULL,
    INDEX ix_equipment_raqam  (ichki_raqam),
    INDEX ix_equipment_tur    (tur),
    INDEX ix_equipment_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ── EQUIPMENT ASSIGNMENTS ────────────────────
CREATE TABLE IF NOT EXISTS equipment_assignments (
    id                   INT AUTO_INCREMENT PRIMARY KEY,
    equipment_id         INT          NOT NULL,
    master_id            INT          NOT NULL,
    prorab_id            INT          NULL,
    assigned_by          INT          NOT NULL,
    pk_boshlanish        VARCHAR(30)  NULL,
    pk_tugash            VARCHAR(30)  NULL,
    sloy                 VARCHAR(20)  NULL,
    status               ENUM('active','completed') NOT NULL DEFAULT 'active',
    boshlanish_vaqt      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    tugash_vaqt          DATETIME     NULL,
    bosh_qilish_sababi   TEXT         NULL,
    created_at           DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at           DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (equipment_id) REFERENCES equipment(id)   ON DELETE CASCADE,
    FOREIGN KEY (master_id)    REFERENCES users(id)       ON DELETE RESTRICT,
    FOREIGN KEY (prorab_id)    REFERENCES users(id)       ON DELETE SET NULL,
    FOREIGN KEY (assigned_by)  REFERENCES users(id)       ON DELETE RESTRICT,
    INDEX ix_assignments_eq     (equipment_id),
    INDEX ix_assignments_master (master_id),
    INDEX ix_assignments_status (status),
    INDEX ix_assignments_eq_st  (equipment_id, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ── EQUIPMENT HISTORY ────────────────────────
CREATE TABLE IF NOT EXISTS equipment_history (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    equipment_id INT          NOT NULL,
    user_id      INT          NULL,
    action       VARCHAR(50)  NOT NULL,
    description  TEXT         NULL,
    pk_boshlanish VARCHAR(30) NULL,
    pk_tugash    VARCHAR(30)  NULL,
    created_at   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (equipment_id) REFERENCES equipment(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id)      REFERENCES users(id)     ON DELETE SET NULL,
    INDEX ix_eqhist_eq   (equipment_id),
    INDEX ix_eqhist_date (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ── WORK REPORTS ─────────────────────────────
CREATE TABLE IF NOT EXISTS work_reports (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    user_id       INT          NOT NULL,
    assignment_id INT          NULL,
    pk_boshlanish VARCHAR(30)  NOT NULL,
    pk_tugash     VARCHAR(30)  NOT NULL,
    sloy          VARCHAR(30)  NOT NULL,
    hajm          DECIMAL(10,2) NOT NULL,
    hajm_turi     ENUM('m2','m3') NOT NULL DEFAULT 'm2',
    uzunlik       DECIMAL(10,2) NULL,
    kenglik       DECIMAL(10,2) NULL,
    qalinlik      DECIMAL(10,3) NULL,
    formula       VARCHAR(100)  NULL,
    tx_soni       INT           NOT NULL DEFAULT 1,
    izoh          TEXT          NULL,
    sana          DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id)       REFERENCES users(id)                ON DELETE CASCADE,
    FOREIGN KEY (assignment_id) REFERENCES equipment_assignments(id) ON DELETE SET NULL,
    INDEX ix_reports_user (user_id),
    INDEX ix_reports_date (sana),
    INDEX ix_reports_user_date (user_id, sana)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ── PENALTIES ────────────────────────────────
CREATE TABLE IF NOT EXISTS penalties (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    from_user_id INT      NOT NULL,
    to_user_id   INT      NOT NULL,
    equipment_id INT      NULL,
    sabab        TEXT     NOT NULL,
    is_read      TINYINT(1) NOT NULL DEFAULT 0,
    created_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (from_user_id) REFERENCES users(id)     ON DELETE CASCADE,
    FOREIGN KEY (to_user_id)   REFERENCES users(id)     ON DELETE CASCADE,
    FOREIGN KEY (equipment_id) REFERENCES equipment(id) ON DELETE SET NULL,
    INDEX ix_penalties_to   (to_user_id),
    INDEX ix_penalties_from (from_user_id),
    INDEX ix_penalties_date (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ── AUDIT LOGS ───────────────────────────────
CREATE TABLE IF NOT EXISTS audit_logs (
    id          BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id     INT          NULL,
    action      VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50)  NULL,
    entity_id   INT          NULL,
    description TEXT         NULL,
    ip_address  VARCHAR(45)  NULL,
    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    INDEX ix_audit_date     (created_at),
    INDEX ix_audit_user     (user_id),
    INDEX ix_audit_entity   (entity_type, entity_id),
    INDEX ix_audit_action   (action)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ══════════════════════════════════════════════
-- DEPLOY QILISH UCHUN QO'LLANMA
-- ══════════════════════════════════════════════
-- 1. MySQL serverida bu SQL ni ishga tushiring:
--    mysql -u root -p < database_mysql.sql
--
-- 2. .env faylini yarating:
--    DB_HOST=localhost
--    DB_PORT=3306
--    DB_USER=root
--    DB_PASS=yourpassword
--    DB_NAME=texnika_nazorat
--    SECRET_KEY=your_secret_key
--
-- 3. Python kutubxonalarini o'rnating:
--    pip install -r requirements.txt
--
-- 4. Serverni ishga tushiring:
--    python main.py
--
-- DEFAULT LOGIN:
--    Login: admin
--    Parol: admin123
--
-- NAMUNA MASTERLAR:
--    Login: fayzullo   Parol: 1234
--    Login: jaloliddin Parol: 1234
--    Login: bobur      Parol: 1234 (Prorab)
