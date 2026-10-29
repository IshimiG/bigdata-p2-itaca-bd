-- Esquema de la réplica de ITACA (solo lectura para la ingesta).
-- Todas las tablas llevan `anyo` (curso académico). Los campos y sus nombres son los de la P1.

CREATE TABLE cursos (
    anyo        text NOT NULL,
    codigo      text NOT NULL,
    nombre_cas  text,
    nombre_val  text,
    abreviatura text,
    ensenanza   text,
    padre       text,
    PRIMARY KEY (anyo, codigo)
);

CREATE TABLE grupos (
    anyo      text NOT NULL,
    codigo    text NOT NULL,
    nombre    text,
    turno     text,
    linea     text,
    modalidad text,
    PRIMARY KEY (anyo, codigo)
);

CREATE TABLE contenidos (
    anyo       text NOT NULL,
    codigo     text NOT NULL,
    nombre_cas text,
    nombre_val text,
    ensenanza  text,
    curso      text NOT NULL,
    PRIMARY KEY (anyo, curso, codigo)
);

-- Un alumno puede tener varias matrículas en un mismo curso: la clave es técnica.
CREATE TABLE alumnos (
    id                   bigserial PRIMARY KEY,
    anyo                 text NOT NULL,
    "NIA"                text,
    sexo                 text,
    nacionalidad         text,
    provincia            text,
    municipio            text,
    ensenanza            text,
    curso                text,
    grupo                text,
    turno                text,
    linea                text,
    modalidad            text,
    repite               text,
    estado_matricula     text,
    tipo_matricula       text,
    fecha_matricula      text,
    fecha_ingreso_centro text,
    -- un alumno sin grupo (NULL) no incumple la FK
    FOREIGN KEY (anyo, grupo) REFERENCES grupos (anyo, codigo)
);

-- Sin FK a alumnos: el origen tiene calificaciones cuyo alumno falta en la matrícula
-- del curso (hueco conocido, se informa en la validación).
CREATE TABLE calificaciones (
    id               bigserial PRIMARY KEY,
    anyo             text NOT NULL,
    evaluacion       text,
    alumno           text,
    ensenanza        text,
    curso            text NOT NULL,
    contenido        text NOT NULL,
    bloque_contenido text,
    nota_numerica    text,
    tipo_nota        text,
    FOREIGN KEY (anyo, curso, contenido) REFERENCES contenidos (anyo, curso, codigo)
);

CREATE INDEX idx_alumnos_nia ON alumnos (anyo, "NIA");
CREATE INDEX idx_calificaciones_alumno ON calificaciones (anyo, alumno);
