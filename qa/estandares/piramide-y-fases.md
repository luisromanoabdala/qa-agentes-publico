# Pirámide de testing y fases

## Dónde va cada prueba

| Nivel | Qué valida | Ejemplos (app odontológica, si el módulo existe) | Dueño típico |
|---|---|---|---|
| Unitario | Reglas y lógica aislada | Cálculo de saldo de tratamiento, solapamiento de horarios, validación de odontograma | Dev + qa-automatizacion sugiere casos |
| Componente | Unidad de UI o servicio con dependencias simuladas | Formulario de turno muestra errores; servicio de agenda con repositorio fake | Dev / qa-automatizacion |
| Integración | Interacción con persistencia/servicios reales | RLS/permisos en DB, transacción de pago + saldo, subida de archivo a storage | qa-automatizacion |
| Contrato | Acuerdo consumidor ↔ proveedor | Frontend ↔ API según OpenAPI; webhooks de pasarela de pago | qa-automatizacion |
| E2E | Recorridos críticos completos | Login → crear paciente → agendar → registrar tratamiento → cobrar | qa-automatizacion / qa-ejecutor |

Regla: **bajar el test al nivel más bajo que detecte el riesgo.** Un riesgo de cálculo se cubre con unitarias, no con 30 E2E.
No se imponen porcentajes de cobertura; se exige que cada riesgo alto tenga cobertura en el nivel adecuado.

## Complementos según el producto

Exploratorio (cartas por riesgo), accesibilidad (WCAG 2.2 AA en flujos de paciente), seguridad (ver `qa-seguridad`),
rendimiento (solo con autorización y ambiente apto), compatibilidad (navegadores/dispositivos que usan los consultorios).

## Fases

| Fase | Actividades QA |
|---|---|
| Requisitos | Revisar ambigüedad, reglas, criterios de aceptación verificables, riesgos de negocio y normativos |
| Diseño | Testabilidad (IDs estables, datos de prueba, ambientes), estados, permisos, integraciones |
| Desarrollo / PR | Impacto del diff, pruebas unitarias/componente/integración, regresión focalizada |
| Integración / QA | Contratos, API, persistencia, flujos, permisos, exploratorio |
| Prelanzamiento | Smoke, regresión crítica, riesgos residuales, recomendación |
| Posdespliegue | Smoke autorizado (lectura), monitoreo de errores, seguimiento de bugs |

Las pruebas destructivas, de carga o sobre datos reales requieren alcance explícito por escrito.
