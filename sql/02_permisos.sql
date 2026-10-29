-- Usuario de la ingesta: SOLO lectura. La contraseña la fija 03_password_lectura.sh.
CREATE ROLE lectura_bigdata LOGIN;

GRANT CONNECT ON DATABASE itaca_academico TO lectura_bigdata;
GRANT USAGE ON SCHEMA public TO lectura_bigdata;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO lectura_bigdata;
-- tablas futuras que cree el propietario
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO lectura_bigdata;
