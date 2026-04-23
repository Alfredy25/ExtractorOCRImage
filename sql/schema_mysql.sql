-- Extractor OCR — esquema MySQL InnoDB (tools_OCR)
-- Requisitos: MySQL 8+ o MariaDB 10.3+ (utf8mb4)
-- Ejecución: mysql -h HOST -u USER -p tools_OCR < sql/schema_mysql.sql
--           o: python scripts/create_mysql_schema.py

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

CREATE TABLE IF NOT EXISTS extractions (
    id INT NOT NULL AUTO_INCREMENT,
    sede VARCHAR(32) NOT NULL,
    nombre_imagen VARCHAR(512) NOT NULL,
    destinatario_raw TEXT NOT NULL,
    nombre_o_titulo TEXT NULL,
    cargo_dependencia TEXT NULL,
    direccion TEXT NULL,
    colonia TEXT NULL,
    municipio_o_alcaldia TEXT NULL,
    estado TEXT NULL,
    codigo_postal VARCHAR(32) NULL,
    extras TEXT NULL,
    contacto TEXT NULL,
    indicaciones TEXT NULL,
    observaciones_ia TEXT NULL,
    crop_x INT NULL,
    crop_y INT NULL,
    crop_w INT NULL,
    crop_h INT NULL,
    rotation_deg INT NULL,
    aspect_mode VARCHAR(16) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NULL,
    PRIMARY KEY (id),
    KEY idx_extractions_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SET FOREIGN_KEY_CHECKS = 1;

-- Nota: sede y aspect_mode se validan en la aplicación (AJUSCO|COYOACÁN, FREE|SQUARE).
