# Política de seguridad

## Reportar una vulnerabilidad

Si encuentras una vulnerabilidad, **no la publiques en un issue público**.

Repórtala de forma privada:
- Usa **GitHub Security Advisories** ("Report a vulnerability" en la pestaña *Security* del repositorio), o
- Escribe a: _[completar: correo de contacto]_

Incluye, si puedes: descripción, pasos para reproducir, impacto potencial y
una posible mitigación. Intentaremos responder en un plazo razonable y te
daremos crédito por el reporte si así lo deseas.

## Alcance

Esta plataforma es una herramienta de transparencia electoral. Nos interesan
especialmente reportes sobre:

- Acceso no autorizado al backend o evasión del secreto compartido / rate-limiting.
- Fugas de secretos (`GROQ_API_KEY`, `BACKEND_SHARED_SECRET`) o de datos.
- Inyección de prompts que rompa las reglas editoriales de imparcialidad.
- Cualquier vector que permita abusar de la API del LLM y generar costos.

## Buenas prácticas para quien despliegue (self-hosting)

- Define **`BACKEND_SHARED_SECRET`** (mismo valor en backend y frontend) para que
  solo tu proxy pueda llamar al backend. Genéralo con `openssl rand -hex 32`.
- Restringe **`ALLOWED_ORIGINS`** al dominio de tu frontend.
- Ajusta **`RATE_LIMIT_PER_MIN`** a tu tráfico esperado.
- Nunca subas el archivo `.env` ni claves al repositorio (ya está en `.gitignore`).
- Trae **tu propia** `GROQ_API_KEY`.
