# Contexto QA del repo (copiar a `.qa/contexto.md` en el repo de la app)

El orquestador lo lee al empezar, así no te pregunta lo mismo cada vez. Sin secretos: solo nombres de variables.

## Producto
- Nombre: <app>
- Stack: <p. ej. SvelteKit + PHP + MySQL>
- Repos relacionados: <otros repos que consume o la consumen>

## Ambientes
| Ambiente | URL | Rama | ¿Se pueden crear/modificar datos? |
|---|---|---|---|
| Test | https://<test> | test | Sí, datos sintéticos |
| Producción | https://<prod> | main | **No**: solo lectura |

## Roles y cuentas de prueba (solo nombres de variables)
| Rol | Variables |
|---|---|
| dueño | `QA_USER_DUENO_EMAIL`, `QA_USER_DUENO_PASSWORD` |
| admin | `QA_USER_ADMIN_EMAIL`, `QA_USER_ADMIN_PASSWORD` |

## Módulos y flujos prioritarios
- <módulo>: <qué no se puede romper>

## Jira
- Sitio: https://<sitio>.atlassian.net · Proyecto: `<KEY>` · Tipo: `<Bug/Error>` · Asignar a: <persona>
- Épica o issue de origen (opcional): `<KEY-N>`

## Pruebas existentes
- `pnpm test`, `pnpm test:e2e`, `composer test`… (qué corre en CI y qué no)
