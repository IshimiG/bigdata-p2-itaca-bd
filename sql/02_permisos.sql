-- Usuario de la ingesta: SOLO lectura. Se aplica DESPUÉS de cargar las tablas del profesor
-- (sql/cargar_origen.sh); la contraseña la fija 03_password_lectura.sh. Es idempotente.
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'lectura_bigdata') THEN
        CREATE ROLE lectura_bigdata LOGIN;
    END IF;
END
$$;

GRANT CONNECT ON DATABASE itaca_academico TO lectura_bigdata;
GRANT USAGE ON SCHEMA public TO lectura_bigdata;
-- DROP TABLE + CREATE TABLE de los SQL del profesor borra los privilegios: se vuelven a dar
GRANT SELECT ON alumnos, cursos, calificaciones, contenidos, grupos TO lectura_bigdata;
