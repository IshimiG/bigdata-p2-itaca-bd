# Proyecto 2 · Analítica académica ITACA (origen relacional)

> Proyecto del módulo **Big Data aplicado** (IABD). Mismo dashboard y modelo de datos que el P1 (ITACA desde XML), pero con origen en una base **PostgreSQL** (réplica de ITACA) accedida por JDBC. Arquitectura batch.

## Descripción y objetivo

Construir un pipeline batch que extrae los datos académicos desde PostgreSQL, los transforma y los deja listos para un dashboard de análisis académico en Power BI.

## Arquitectura

```mermaid
graph LR
    A[PostgreSQL - réplica ITACA] --> B[Ingesta JDBC]
    B --> C[Almacenamiento]
    C --> D[ETL]
    D --> E[Dashboard Power BI]
```

*Diagrama provisional (Bloque 0). Se actualizará al terminar cada bloque.*

## Fuentes de datos

| Fuente | URL / origen | Formato | Frecuencia de actualización | Licencia | Última ingesta |
|---|---|---|---|---|---|
| ITACA (réplica) | PostgreSQL del aula (`servidor:5432`) | BD relacional | Única (práctica) | Uso docente | — |

## Estructura del repositorio

| Carpeta | Contenido |
|---|---|
| `ingesta/` | Scripts de extracción desde PostgreSQL |
| `etl/` | Transformaciones y modelo de datos |
| `dashboard/` | Informe de Power BI |
| `docs/` | Capturas y diagramas |
| `docker-compose.yml` | Servicio PostgreSQL local para desarrollo |
| `.env.example` | Plantilla de variables de entorno (el `.env` real no se sube) |

## Cómo desplegar el entorno

```bash
cp .env.example .env           # rellena las credenciales
./scripts/levantar.sh          # levanta PostgreSQL y carga data/seed/*.sql
docker compose ps
```

`scripts/cargar_datos.sh` se puede ejecutar cuantas veces haga falta: no borra nada y salta las tablas ya cargadas. Si una tabla existe con otro número de filas, se detiene sin tocarla.

Conexión local: `localhost:5432`, base y usuario definidos en `.env`.

## Bitácora de prácticas

### Bloque 0 · Entorno

- Objetivo: dejar preparado el repositorio y un PostgreSQL local con Docker.
- Pasos realizados: creación del repo con la estructura de la práctica, `.gitignore` del módulo, `docker-compose.yml` con PostgreSQL 16 (volumen persistente y healthcheck), `.env` fuera del control de versiones, primer commit y publicación en GitHub.
- Problemas encontrados y solución: —
- Resultado: `docker compose ps` con el contenedor `bigdata-postgres` en ejecución.

### Bloque 1 · Ingesta batch

- Objetivo: —
- Pasos realizados: —
- Problemas encontrados y solución: —
- Resultado: —

## Decisiones técnicas

| Decisión | Alternativa descartada | Motivo |
|---|---|---|
| PostgreSQL 16 (alpine) en Docker | Instalación nativa | Reproducible y aislado; misma imagen que el resto del equipo |
| Puerto enlazado sólo a `127.0.0.1` | `0.0.0.0` | El servicio de desarrollo no debe quedar expuesto en la red |
| Credenciales en `.env` | Contraseña en el `docker-compose.yml` | Evita subir credenciales a GitHub |

## Incidencias resueltas

*Ninguna por ahora.*
