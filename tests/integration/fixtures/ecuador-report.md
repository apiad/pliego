---
title: "Propuesta de evolución arquitectónica — Chatbot UBE"
subtitle: "Del enrutador determinista al agente generalista con skills."
author: "Alejandro Piad Morffis — asesor técnico externo"
date: "2026-05-11"
lang: es
pliego:
  papersize: a4
  margin: { x: 2cm, y: 2cm }
  fontsize: 10pt
  toc: true
  toc-depth: 2
  section-numbering: ""
---

El Chatbot UBE funciona hoy. No está roto. Este reporte no es una corrección de errores: es un diagnóstico de un techo estructural que todo chatbot con arquitectura de enrutador termina alcanzando — y una propuesta concreta para atravesarlo sin tirar lo construido.

Este documento ha sido redactado para ser leído tanto por personas como por agentes de código (p. ej. Claude Code). La referencia es completa: el cuerpo del reporte contiene el análisis y la propuesta para revisores humanos; la **sección 10 — *Instructions for code agents*** codifica instrucciones específicas en inglés para que un agente con acceso al repositorio del Chatbot UBE verifique los claims técnicos contra el código real y produzca un *spec* de migración aterrizado en archivos concretos. Si eres un agente de código leyendo esto, salta a §10.
## 1. Resumen ejecutivo

La arquitectura actual del Chatbot UBE — un clasificador de intenciones que enruta hacia flujos deterministas especializados — resuelve bien el problema funcional. Cada intención tiene su flujo, cada flujo tiene su comportamiento predecible, y el equipo puede depurar y ajustar cada rama de forma independiente. Eso es valioso y no se descarta.

El problema es estructural, no funcional: el sistema escala mal en ancho. Cada nueva funcionalidad exige una nueva intención, un flujo nuevo desde cero y reentrenar el clasificador. No hay reutilización entre flujos; cuando dos intenciones comparten lógica, la duplicidad es la única salida. Este patrón se sostiene con 8 ó 10 intenciones; con 15 ó 20, el costo marginal de cada intención nueva crece superlinealmente. Hemos recorrido este mismo camino en el chatbot de un cliente empresarial previo: reconocemos los síntomas y conocemos dónde lleva el camino si no se interviene.

Este análisis parte de que los flujos actuales son deterministas — es decir, no tienen un ciclo de razonamiento iterativo propio, sino secuencias fijas de llamadas a modelo y herramientas. Si el equipo confirma que alguno de los flujos ya implementa un ciclo agéntico, parte de las recomendaciones cambia. Solicitamos esa confirmación antes de avanzar al paso 1.
La propuesta no es una re-arquitectura completa. Es una migración gradual en tres pasos que puede pausarse en cualquier punto sin perder la inversión acumulada. El primer paso — refactorizar una única intención como un ciclo agéntico ReAct, manteniendo el clasificador intacto — puede completarse en dos o tres semanas, con riesgo mínimo y con valor de aprendizaje alto: el equipo obtiene experiencia directa con el patrón agéntico antes de comprometerse con nada más. El segundo paso generaliza ese patrón a un agente único con skills declarativos en markdown, eliminando el clasificador y reduciendo el costo de añadir una intención nueva a escribir un documento. El tercer paso recupera, de forma selectiva, el determinismo donde importa — no como flujos de código, sino como secuencias de instrucciones que invocan al agente completo.

Lo que pedimos del equipo es simple: elegir la intención más sencilla de su catálogo actual, definir un conjunto mínimo de casos de prueba para esa intención, y ejecutar el paso 1. El resto se decide con datos.


## 2. Contexto y alcance del análisis

### 2.1 Antecedentes del engagement

Este reporte surge de una colaboración de asesoría técnica derivada directamente del curso de diseño de chatbots dictado en Ecuador a principios de este año. El equipo de desarrollo del Chatbot UBE participó en ese curso; conoce el lenguaje, los patrones y el marco conceptual con que trabajamos: clasificador de intenciones, flujos deterministas, ciclo de diseño iterativo. Eso es una ventaja real — no empezamos desde cero en terminología ni en confianza.

El engagement está pactado por cuatro meses. Durante ese período el equipo nos envía el código, avances y reportes; nosotros devolvemos análisis, recomendaciones y revisiones. Este documento es el primero de esa serie: establece el diagnóstico arquitectónico y la propuesta de evolución.

### 2.2 Alcance de este reporte

Este reporte cubre exclusivamente la **dimensión arquitectónica** del chatbot: cómo está organizado el sistema hoy, qué limitaciones estructurales impone esa organización a medida que el sistema crece, y cómo evolucionar hacia un patrón agéntico de forma gradual y reversible.

No cubre — ni pretende cubrir — los siguientes temas, que ya están identificados y documentados en la auditoría técnica previa ([[auditoria_ube_v2]]):

- Vulnerabilidades de seguridad bloqueantes (configuración de CSRF, `ALLOWED_HOSTS`, HTTPS).
- Deuda de plataforma: migración de Django 3.2 a versión actualmente soportada.
- Cobertura de tests automatizados.

Esos temas se abordan en paralelo a este reporte, no después. La arquitectura que se propone aquí es independiente de su resolución, aunque algunas recomendaciones del auditor — en particular el conjunto de tests del clasificador de intenciones — se vuelven más urgentes una vez que se inicia la migración propuesta en la sección 5.

### 2.3 Material base utilizado

El análisis se construyó a partir del siguiente material:

- La sesión de contextualización inicial con el equipo y dos sesiones posteriores.
- El informe de auditoría técnica [[auditoria_ube_v2]], recibido del equipo, que incluye hallazgos sobre la estructura de intenciones, el stack tecnológico (Django, LangChain 1.1.0) y problemas concretos detectados en el código.

**Lo que no tuvimos:** acceso directo al código fuente. Toda descripción de la arquitectura actual en la sección 3 se basa en lo referenciado en la auditoría y en el modelo mental que derivamos del curso. Donde el análisis depende de una suposición sobre el código — y no de un hecho confirmado — se marca explícitamente con una nota de validación. Pedimos al equipo que revise esas notas antes de avanzar al paso 1 de la propuesta.

### 2.4 Experiencia previa relevante

Este reporte no parte de cero. Hemos recorrido el mismo camino arquitectónico en el chatbot de un cliente empresarial en Cuba: un sistema que comenzó con el patrón enrutador-más-flujos, escaló hasta un punto donde añadir cada funcionalidad nueva dejó de ser razonable, y tuvo que ser reestructurado. Las lecciones de ese proyecto — dónde aparece el primer síntoma de techo, qué tan rápido se agrava, qué funciona en la migración y qué no — informan directamente el diagnóstico y la propuesta que siguen. Cuando en este reporte decimos "conocemos dónde lleva este camino", no es retórica: es experiencia concreta.


## 3. Análisis crítico de la arquitectura actual

### 3.1 Cómo entendemos lo que tienen

Esta sección describe el modelo mental con que leemos la arquitectura del Chatbot UBE. Si algo no encaja con la realidad del código, queremos saberlo antes de continuar — el resto del análisis descansa sobre este entendimiento.

La topología que derivamos es la siguiente. En la raíz del sistema hay un **clasificador de intenciones**: un módulo que recibe el mensaje del usuario y predice una etiqueta de un conjunto cerrado — `historia`, `notas`, `finanzas`, `QnA`, `consultas`, y las demás, hasta sumar los trece flujos que registra la auditoría. A partir de esa etiqueta, el sistema enruta hacia uno de esos trece **flujos especializados**. Cada flujo es, en nuestra lectura, una secuencia predefinida de llamadas al modelo de lenguaje intercaladas con accesos a datos — bases de datos, notas del estudiante, documentos del SGA, según corresponda. La secuencia es fija: no hay un paso de razonamiento que decida dinámicamente qué herramienta invocar a continuación; el código ya lo determina de antemano.

Llamarlos "agentes", como hace la nomenclatura interna del proyecto, no es incorrecto en sentido amplio, pero sí crea una ambigüedad que conviene resolver desde el inicio: en el vocabulario de este reporte, un **agente** tiene un ciclo iterativo propio — razona, actúa, observa el resultado y decide el siguiente paso. Lo que la arquitectura actual implementa es distinto y tiene un nombre más preciso: **flujo determinista de modelo de lenguaje**. La diferencia no es semántica; es la diferencia entre un sistema que puede improvisar ante lo inesperado y uno que no puede.

Todo el análisis que sigue asume que los flujos actuales **no** tienen ciclo agéntico iterativo — es decir, que la secuencia de llamadas a modelo y herramientas está predeterminada en código y no emerge del razonamiento del modelo en tiempo de ejecución. Si alguno de los flujos ya implementa un ciclo ReAct o equivalente, esta sección debe revisarse antes de continuar. Solicitamos al equipo confirmación explícita sobre este punto.
### 3.2 Diagrama 1 — Arquitectura actual: enrutador + flujos deterministas

![Diagrama 1 — Arquitectura actual: enrutador + flujos deterministas](diagrams/diagrama-1-actual.svg)

*El diagrama muestra el clasificador de intenciones como nodo raíz, del que parten trece ramas etiquetadas hacia sus respectivos flujos especializados. Cada flujo se representa como una secuencia lineal de pasos — llamadas al modelo, accesos a herramientas, respuesta final — sin ciclo de retroalimentación interno. La anotación clave es la que aparece en el margen derecho: "añadir una funcionalidad nueva = añadir una rama nueva desde cero". Ese eje de comparación — el costo marginal de crecer en ancho — es el hilo conductor de las secciones 3.4 y 4.*

### 3.3 Lo que funciona

Antes de hablar de limitaciones, conviene ser precisos sobre lo que la arquitectura actual resuelve bien. No son concesiones retóricas: son propiedades genuinas que cualquier propuesta de evolución debe preservar o compensar explícitamente.

**Predictibilidad.** Dado un mensaje de usuario, la secuencia de operaciones que ejecutará el sistema es completamente determinista y trazable. Si el flujo de `historia` llama al modelo con el prompt X y luego consulta la base de datos con la query Y, eso es lo que siempre ocurre. Eso facilita el debugging, simplifica los tests y hace que los errores sean reproducibles — cualidades que un sistema agéntico puro no ofrece sin esfuerzo adicional.

**Control fino por dominio.** El equipo puede ajustar el comportamiento del flujo de notas sin tocar el flujo de finanzas. El aislamiento es total: cada rama es un script independiente. En un equipo que mantiene varios dominios en paralelo, esta independencia reduce el riesgo de regresión.

**Costo computacional predecible.** Cada flujo tiene un número fijo de llamadas al modelo de lenguaje. El costo por interacción es calculable a priori; no hay riesgo de que el sistema decida hacer diez iteraciones cuando se esperaban tres. Para una institución educativa con presupuesto de API ajustado, eso no es un detalle menor.

**Curva de entrada baja para desarrolladores nuevos.** Un flujo determinista es, en última instancia, un script: se lee de arriba hacia abajo, se entiende sin necesidad de mental-model sobre comportamiento emergente. Esto no debe subestimarse cuando el equipo tiene rotación o cuando se incorporan estudiantes en práctica.

Estas cuatro propiedades son el activo real de la arquitectura actual. La propuesta de migración de la sección 5 está diseñada para no descartarlas, sino para moverlas hacia el lado correcto del balance cuando el sistema crezca.

### 3.4 Los defectos de escalabilidad

El problema central no es funcional. El chatbot cumple hoy lo que promete. El problema es **estructural**: la arquitectura impone un costo de crecimiento que se vuelve insostenible antes de lo que parece.

1. **Escalabilidad en ancho, no en profundidad.** Cada nueva funcionalidad requiere una nueva intención en el clasificador, un flujo nuevo desde cero y el mantenimiento de ese flujo de forma indefinida. No hay mecanismo de reutilización entre flujos: si dos intenciones comparten el ochenta por ciento de la lógica, la única salida es duplicar el código. La auditoría ya detecta un síntoma de esto: la duplicidad entre `agente_academico` y `agente_consultas`, que huele a un refactor inconcluso precisamente porque el patrón no facilita compartir nada entre ramas.

2. **Costo lineal del clasificador con N.** Cada intención nueva exige actualizar o reentrenar el clasificador — sea un modelo de clasificación, sea un prompt con ejemplos, sea una lógica basada en reglas. El clasificador se convierte en un cuello de botella silencioso: crecer en intenciones es crecer en la superficie de error de ese módulo central. La auditoría ya documenta un bug concreto en esta línea: la constante `INTENCION_HISTORIA = 'agente_historia'` mal asignada, que rompe silenciosamente toda la rama de historia sin error obvio. Un bug en el clasificador no afecta a una intención; afecta a todas las que compartan el mismo defecto de mapeo.

3. **Cero composición entre dominios.** Una pregunta que cruza dos dominios — por ejemplo, "¿cuándo es mi próximo examen de historia y cuál fue mi nota en el parcial anterior?" — no tiene cómo resolverse. El clasificador elige una intención; el flujo elegido trabaja en ese dominio; la otra mitad de la pregunta se pierde. No hay un mecanismo en la arquitectura actual para que dos flujos colaboren en responder una sola consulta. A medida que los usuarios del chatbot se familiarizan con el sistema y plantean preguntas más complejas, este límite se hará visible.

4. **Cero adaptabilidad en tiempo de ejecución.** Una vez que el clasificador elige un flujo, el destino está fijado. El sistema no puede decidir a mitad de la conversación que necesita una herramienta que no estaba prevista en ese flujo. No puede pedir una aclaración al usuario, reinterpretar la intención y replantear el plan. No puede detectar que la consulta a la base de datos devolvió vacío y decidir buscar en otro lado. El flujo es una vía única: termina donde termina, independientemente de lo que encuentre en el camino.

5. **La trampa conocida: el techo llega antes de lo esperado.** Este patrón se sostiene bien hasta cierto número de intenciones — y luego se rompe de forma no lineal. Hasta diez intenciones el sistema se siente manejable; pasadas las quince o veinte, el costo marginal de cada intención nueva crece superlinealmente, porque cada incorporación tiene que coordinarse con las anteriores, el clasificador acumula ambigüedad y los flujos empiezan a necesitar casos especiales para escenarios que en otra arquitectura serían triviales. En ese proyecto previo llegamos a ese punto: lo que en el inicio parecía un sistema que podía crecer indefinidamente mostró su techo de forma bastante abrupta, cuando añadir una funcionalidad nueva dejó de ser una tarea de días para convertirse en una tarea de semanas. El Chatbot UBE no está en ese punto todavía. Pero con trece intenciones actuales, no está lejos.


## 4. Marco conceptual: cuatro arquetipos de arquitectura

Antes de proponer un camino de migración conviene fijar un vocabulario compartido. Esta sección describe cuatro arquetipos arquitectónicos ordenados de menor a mayor flexibilidad agéntica. Son abstracciones, no recetas: el objetivo no es que el Chatbot UBE adopte uno de ellos al pie de la letra, sino que el equipo tenga un mapa conceptual claro sobre dónde está hoy, hacia dónde podría moverse y qué implica cada movimiento. El eje de comparación que atraviesa los cuatro arquetipos es siempre el mismo: **¿cuánto cuesta añadir una funcionalidad nueva?**

### 4.1 Arquetipo A — Enrutador + flujos deterministas

Este es el arquetipo que implementa hoy el Chatbot UBE. Su caracterización detallada, incluyendo el diagrama de topología, está en la sección anterior (ver Diagrama 1, sección 3.2). Aquí lo resumimos en sus rasgos conceptuales esenciales.

Un clasificador de intenciones opera como dispatcher en la raíz del sistema. Dado el mensaje del usuario, predice una etiqueta de un conjunto cerrado y enruta hacia el flujo correspondiente. Cada flujo es una secuencia predeterminada en código: llamadas al modelo de lenguaje intercaladas con accesos a datos, sin ciclo iterativo propio. El "conocimiento de dominio" vive en esa secuencia de código.

**Cuándo es una buena elección.** Este arquetipo es apropiado cuando el dominio es pequeño y cerrado — pocas intenciones, bien delimitadas, con escasa probabilidad de cruce entre dominios —, cuando los requisitos de comportamiento son rígidos y el equipo necesita poder auditar cada paso de forma determinista, o cuando el equipo carece aún de experiencia con patrones agénticos y la curva de entrada importa. En esas condiciones, las propiedades que describimos en la sección 3.3 — predictibilidad, control fino, costo computacional acotado — justifican la elección.

El problema, como argumentamos en la sección 3.4, no es que el arquetipo sea malo: es que su costo marginal de crecimiento en ancho es estructuralmente alto, y ese costo se acelera de forma no lineal pasado cierto umbral de intenciones.

### 4.2 Arquetipo B — Agente puro

En el extremo opuesto del espectro se sitúa el arquetipo de agente puro. Aquí no hay clasificador, no hay enrutador, no hay flujos predefinidos. Existe un único ciclo agéntico — típicamente ReAct: *razona, actúa, observa* — que tiene acceso simultáneo a todas las herramientas disponibles. El agente decide en tiempo de ejecución qué herramienta invocar, en qué orden y con qué argumentos, a partir de su razonamiento sobre el mensaje del usuario y los resultados que va acumulando.

![Diagrama 2 — Arquetipo B: agente puro](diagrams/diagrama-2-agente-puro.svg)

*El diagrama muestra un nodo central "Ciclo agéntico (ReAct)" del que parten conexiones bidireccionales hacia el conjunto completo de herramientas del sistema: consulta a base de datos, búsqueda en notas, llamada al SGA, búsqueda semántica en documentos, herramienta de terminación explícita (`done`), y las demás que el dominio requiera. La flecha de entrada llega del usuario; la flecha de salida, generada por la herramienta `done`, devuelve la respuesta. Una anotación en el margen señala el límite máximo de iteraciones como parámetro configurable — el único "determinismo" que se preserva en este arquetipo es ese tope defensivo.*

**Cuándo es una buena elección.** El arquetipo B es conceptualmente el destino natural de un sistema de agentes bien maduro: herramientas bien tipadas, equipo cómodo con observabilidad agéntica, dominio suficientemente amplio como para que el costo de mantener un clasificador supere al beneficio. Un agente puro puede responder preguntas que cruzan múltiples dominios, puede pedir aclaración al usuario y replantear su plan, puede adaptarse a resultados inesperados de las herramientas.

**Por qué no es el primer paso.** Pasar directamente del arquetipo A al arquetipo B es el movimiento más tentador y el más arriesgado. Se pierde de golpe todo el determinismo — y con él, la trazabilidad, la predictibilidad del costo y la posibilidad de hacer tests de regresión sobre comportamientos conocidos. El equipo tendría que construir simultáneamente el agente, la observabilidad necesaria para depurarlo y la confianza operativa para desplegarlo en producción. Es una re-arquitectura total, no una evolución. Por eso lo presentamos como destino conceptual, no como recomendación inmediata.

### 4.3 Arquetipo C — Híbrido: enrutador + agentes especializados

El arquetipo C es el puente entre A y B. La estructura de alto nivel no cambia: el clasificador de intenciones permanece en la raíz y el sistema sigue enrutando. Lo que cambia es lo que hay al final de cada rama. En lugar de un flujo determinista, cada destino es un pequeño agente ReAct con su propio ciclo iterativo y un conjunto reducido de herramientas propias del dominio de esa intención — típicamente dos a cuatro herramientas por agente especializado.

![Diagrama 3 — Arquetipo C: híbrido](diagrams/diagrama-3-hibrido.svg)

*El diagrama mantiene la estructura del Diagrama 1: clasificador de intenciones como nodo raíz con N ramas etiquetadas. La diferencia es que cada caja terminal ya no es un script lineal sino un mini-ciclo ReAct con sus propias herramientas. La anotación clave es que "añadir una intención nueva" sigue requiriendo una rama nueva, pero ahora el interior de esa rama es un agente con capacidad de razonamiento iterativo, no un flujo fijo.*

**Cuándo es una buena elección.** Este arquetipo es especialmente valioso como etapa de transición. Permite introducir el patrón agéntico en un contexto acotado — una sola intención, en producción paralela con el flujo original — sin necesidad de abandonar la estructura de clasificador que el equipo ya conoce y sabe operar. El riesgo está contenido: si el agente especializado de una intención se comporta de forma inesperada, el impacto está limitado a esa rama. El resto del sistema no se ve afectado.

Es también el arquetipo que mejor funciona como entorno de aprendizaje para un equipo sin experiencia agéntica previa: cada mini-agente es lo suficientemente pequeño para depurarse y entenderse en su totalidad, sin la complejidad de un agente con acceso ilimitado a herramientas.

La limitación es que el clasificador central sigue siendo un cuello de botella — cada intención nueva requiere actualizar el dispatcher — y la composición entre dominios sigue siendo nula: dos agentes especializados no colaboran entre sí.

### 4.4 Arquetipo D — Agente generalista + skills

El arquetipo D es el que resuelve los problemas estructurales del arquetipo A sin el riesgo del arquetipo B. La idea central es una separación de responsabilidades que el arquetipo B no hace explícita: separar el **motor de razonamiento** — el agente genérico con su ciclo ReAct — del **conocimiento de dominio** — que ya no vive en flujos de código sino en documentos declarativos llamados *skills*.

![Diagrama 4 — Arquetipo D: agente generalista + skills](diagrams/diagrama-4-generalista-skills.svg)

*El diagrama muestra un nodo central "Agente generalista (ReAct)" conectado a dos estructuras: a la izquierda, un conjunto reducido de herramientas genéricas (`lookup`, `search`, `action`, `done`) que sirven para todos los dominios; a la derecha, un "Registro de skills" que lista N skills en formato markdown, cada uno con su descripción corta. Las flechas de activación muestran que el agente, al recibir el mensaje del usuario, consulta el registro de skills, activa el más pertinente cargando su contenido como contexto adicional, y a partir de ese momento el ciclo ReAct opera guiado tanto por las herramientas como por las instrucciones narrativas del skill activado.*

**El concepto de skill.** Un skill es un documento markdown con tres componentes: una descripción corta que explica en una o dos frases *cuándo* debe activarse este skill (análogo a la descripción de una herramienta en un sistema de tool calling), un cuerpo narrativo que describe *cómo* abordar el problema — qué pasos seguir, qué herramientas son más relevantes, qué casos especiales tener en cuenta —, y un listado del subconjunto de herramientas disponibles para ese dominio. El skill no es código ejecutable: es conocimiento de dominio en lenguaje natural, revisable por cualquier miembro del equipo, incluyendo los que no son técnicos.

Este patrón no es una invención propia: es una generalización del modelo que herramientas como Claude Code usan para gestionar capacidades especializadas mediante archivos markdown con descripciones cortas que el agente evalúa para decidir qué activar. Lo relevante aquí no es la referencia concreta sino el principio: **el conocimiento de dominio como texto legible por humanos, activado dinámicamente por el agente según contexto**.

**Qué cambia respecto al arquetipo A.** El clasificador de intenciones desaparece como componente de código independiente: el agente generalista lo reemplaza con una operación de activación de skills — dado el input del usuario, ¿qué skill describe mejor esta situación? La diferencia es que añadir una intención nueva ya no requiere código: requiere escribir un nuevo archivo markdown. Cero reentrenamiento del clasificador, cero flujo nuevo desde cero. El costo marginal de crecer en ancho colapsa hacia el costo de redactar un documento.

**Qué se pierde.** La honestidad intelectual obliga a nombrarlo: el arquetipo D no garantiza la misma secuencia de operaciones en cada ejecución. El agente puede decidir invocar las herramientas en un orden diferente, o hacer más iteraciones de las esperadas, o activar un skill inesperado ante una formulación ambigua del usuario. Eso es exactamente lo que hace al sistema adaptable. Es también lo que obliga a invertir en observabilidad, límites duros de iteración y tests de comportamiento, no de flujo.

**Cuándo es una buena elección.** Este arquetipo se vuelve natural cuando el equipo ya tiene varios flujos refactorizados al patrón agéntico del arquetipo C y observa que el código de los distintos agentes especializados es esencialmente idéntico — solo cambian las herramientas y el prompt de sistema. Ese es el momento en que la generalización tiene sentido: el motor ya está probado, el patrón ya está internalizado por el equipo, y la deuda de mantener N clasificadores de intenciones y N flujos independientes empieza a superar el beneficio del control fino.

### 4.5 Tabla comparativa

La tabla siguiente resume los cuatro arquetipos sobre las dimensiones que más importan para una decisión de migración. Los valores son cualitativos y representan el comportamiento típico del arquetipo, no garantías absolutas.

| Dimensión | A: Enrutador + flujos | B: Agente puro | C: Híbrido | D: Generalista + skills |
|---|---|---|---|---|
| Coste de añadir una intención nueva | Alto — flujo nuevo desde cero | Bajo — tool nueva | Medio — rama + mini-agente | Muy bajo — skill markdown nuevo |
| Predictibilidad del comportamiento | Alta | Baja | Media | Media |
| Composición entre dominios | Nula | Alta | Baja | Alta |
| Curva de aprendizaje para el equipo | Suave | Empinada | Media | Media |
| Riesgo de migración desde A | — | Muy alto | Bajo | Medio |

La columna de "riesgo de migración" es quizás la más importante para la decisión inmediata. El arquetipo C es el único que permite una migración incremental y reversible desde el arquetipo A: se puede adoptar en una sola intención, medir, y decidir si continuar. El arquetipo D requiere que el arquetipo C ya esté consolidado en varias intenciones. El arquetipo B no tiene una ruta de migración gradual sensata desde A.

La propuesta de migración en tres pasos de la sección siguiente está diseñada para recorrer este mapa de izquierda a derecha, con puntos de parada explícitos y criterios de avance medibles.


## 5. Propuesta: migración gradual en tres pasos

La propuesta central de este reporte no es una re-arquitectura. Es una hoja de ruta de evolución que preserva la inversión existente y puede detenerse en cualquier punto sin perder lo construido. El **Paso 1** consiste en refactorizar una única intención como agente ReAct, para probar el patrón en terreno acotado con riesgo mínimo. El **Paso 2** generaliza la lección: cuando varias intenciones hayan seguido ese camino y el código empiece a converger, se consolida un agente único con un registro de skills declarativos, eliminando el clasificador central como cuello de botella. El **Paso 3** recupera selectivamente el determinismo allí donde importa, convirtiendo ciertos skills en secuencias ordenadas de invocaciones al agente — sin abandonar la flexibilidad agéntica, sino construyendo sobre ella.

### 5.1 Paso 1 — Refactorizar UNA intención como agente ReAct

#### 5.1.1 Objetivo

El objetivo del Paso 1 es probar el patrón agéntico en un contexto acotado, con riesgo mínimo y aprendizaje máximo. No se trata de reemplazar la arquitectura: se trata de sustituir un único flujo determinista por un ciclo ReAct pequeño — dos o tres herramientas, un límite explícito de iteraciones — y medir si el resultado es comparable o superior al flujo original. El equipo sale de este paso con un agente funcionando en producción, con criterios de éxito verificados, y con la experiencia práctica necesaria para decidir con información si tiene sentido continuar hacia el Paso 2.

#### 5.1.2 Selección del candidato

No todas las intenciones son igualmente buenas candidatas para este primer experimento. La selección debe respetar tres criterios en orden de prioridad: **(A) Sencillez de herramientas** — el flujo candidato debe poder modelarse con dos o tres herramientas bien delimitadas, sin lógica de negocio compleja ni dependencias cruzadas con otros flujos; **(B) Bajo riesgo operativo** — la intención no debe ser crítica para producción ni estar en el camino de usuario más frecuente, de modo que un comportamiento inesperado del agente tenga impacto acotado; **(C) Volumen suficiente** — debe tener un uso real que genere datos para evaluar la comparación side-by-side con el flujo original.

Basándonos en la descripción de la arquitectura actual, intenciones del tipo "consulta de notas" o "estado de matrícula" — que implican un lookup en base de datos seguido de una decisión sencilla — encajan bien en este perfil. Sin embargo, es el equipo quien conoce mejor los 13 flujos existentes, sus dependencias y su comportamiento real en producción. La recomendación es que el equipo aplique estos tres criterios sobre su conocimiento del sistema y proponga el candidato. En la sesión técnica de seguimiento se puede revisar esa elección conjuntamente.

#### 5.1.3 Diseño del agente

El agente del Paso 1 es deliberadamente pequeño. Su estructura es la del ciclo ReAct canónico: en cada iteración, el modelo razona sobre el estado actual de la tarea, decide qué herramienta invocar, recibe el resultado y actualiza su razonamiento. El ciclo termina cuando el agente invoca la herramienta `done` con la respuesta final, o cuando se alcanza el límite de iteraciones.

El conjunto de herramientas recomendado para este primer agente incluye: las dos o tres operaciones que el flujo determinista original ya tenía cableadas en código — típicamente un lookup en base de datos, una búsqueda en notas o documentos, y opcionalmente una llamada al SGA — más la herramienta `done`, que es el mecanismo de terminación explícita estándar en implementaciones ReAct. El límite de iteraciones recomendado es cinco, configurable como parámetro del agente; es un tope defensivo que previene bucles indefinidos sin ser tan restrictivo como para impedir el razonamiento en casos moderadamente complejos. El prompt del sistema del agente debe ser corto, en español, y describir explícitamente el rol del agente y las herramientas disponibles.

#### 5.1.4 Tecnología recomendada

**Recomendación principal: Pydantic AI.** Las razones son técnicas, no de marketing. Pydantic AI opera a un nivel de abstracción más bajo que LangChain: expone primitivas claras para definir herramientas, modelar esquemas de entrada y salida, y controlar el ciclo de ejecución, sin capas de abstracción que oculten lo que está ocurriendo. Esto importa especialmente en un contexto de primer agente, donde la depuración y la comprensión del comportamiento son más valiosas que la velocidad de prototipado. El tipado fuerte a través de Pydantic encaja naturalmente con una base de código Python seria, y los mensajes de error son informativos en lugar de crípticos. Finalmente, la API es concisa: un agente funcional con dos herramientas se puede escribir en treinta líneas legibles.

**Alternativa válida: LangGraph.** Si el equipo ya ha invertido en LangChain — y la auditoría registra LangChain 1.1.0 en el stack — LangGraph es el camino menos disruptivo. Comparte el ecosistema, reutiliza el conocimiento acumulado y ofrece una representación explícita del grafo de estados que algunos equipos encuentran más fácil de razonar. Su mayor opinionamiento puede ser una ventaja cuando el equipo no quiere tomar decisiones de diseño de bajo nivel, aunque a veces esa misma rigidez complica la depuración.

La propuesta de migración es válida con cualquiera de las dos opciones. La elección final se ajusta en la sesión técnica con el equipo, en función de la experiencia existente y la preferencia del desarrollador que liderará el Paso 1.

#### 5.1.5 Código ilustrativo

Los snippets siguientes son ilustrativos, no copiables. Su función es fijar la imagen mental del ciclo ReAct y mostrar cómo las tres bibliotecas lo expresan de forma diferente — no servir de plantilla para producción. Un agente real requiere manejo de errores, logging, configuración de credenciales y adaptación al dominio específico.

**Bloque A — Pseudocódigo genérico del ciclo ReAct**

```python
# Ciclo ReAct agnóstico de biblioteca
# Muestra la estructura fundamental: razonar → actuar → observar

def ciclo_react(mensaje_usuario: str, herramientas: dict, max_iter: int = 5) -> str:
    historial = [{"role": "user", "content": mensaje_usuario}]

    for iteracion in range(max_iter):
        # El modelo razona sobre el estado actual y decide qué hacer
        respuesta = llamar_modelo(historial)

        if respuesta.tipo == "herramienta":
            nombre = respuesta.herramienta
            argumentos = respuesta.argumentos

            # Terminación explícita: el agente declara que terminó
            if nombre == "done":
                return argumentos["respuesta_final"]

            # Ejecutar la herramienta y observar el resultado
            resultado = herramientas[nombre](**argumentos)
            historial.append({"role": "tool", "name": nombre, "content": str(resultado)})

        else:
            # El modelo respondió directamente sin invocar herramienta
            return respuesta.contenido

    # Límite de iteraciones alcanzado: fallback defensivo
    return "No pude completar la tarea en el límite de pasos permitidos."
```

**Bloque B — Pydantic AI**

```python
from pydantic_ai import Agent
from pydantic_ai.tools import ToolDefinition

# Definición del agente: modelo, prompt de sistema, sin más boilerplate
agente = Agent(
    model="openai:gpt-4o",
    system_prompt=(
        "Eres un asistente universitario. Respondes preguntas sobre notas y matrícula. "
        "Usa las herramientas disponibles para buscar información antes de responder. "
        "Cuando tengas la respuesta completa, invoca 'done'."
    ),
)

# Cada herramienta es una función Python tipada con decorador
@agente.tool
async def consultar_notas(estudiante_id: str, asignatura: str) -> dict:
    """Consulta las notas de un estudiante en una asignatura específica."""
    # Aquí va la lógica real de acceso a base de datos
    return {"asignatura": asignatura, "nota": 8.5, "estado": "aprobado"}

@agente.tool
async def consultar_matricula(estudiante_id: str) -> dict:
    """Devuelve el estado actual de matrícula del estudiante."""
    return {"estado": "activo", "semestre": "2026-1", "creditos": 18}

@agente.tool
async def done(respuesta_final: str) -> str:
    """Termina el ciclo agéntico y devuelve la respuesta al usuario."""
    return respuesta_final

# Invocación: una línea
async def responder(mensaje: str) -> str:
    resultado = await agente.run(mensaje)
    return resultado.data
```

**Bloque C — LangGraph**

```python
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from typing import TypedDict, Annotated
import operator

# Estado del grafo: acumula mensajes entre nodos
class EstadoAgente(TypedDict):
    mensajes: Annotated[list, operator.add]

# Herramientas del dominio (mismas que en Bloque B, idioma LangChain)
@tool
def consultar_notas(estudiante_id: str, asignatura: str) -> str:
    """Consulta las notas de un estudiante en una asignatura."""
    return f"Nota de {asignatura}: 8.5 — aprobado"

@tool
def consultar_matricula(estudiante_id: str) -> str:
    """Devuelve el estado de matrícula del estudiante."""
    return "Matrícula activa — semestre 2026-1 — 18 créditos"

herramientas = [consultar_notas, consultar_matricula]
modelo = ChatOpenAI(model="gpt-4o").bind_tools(herramientas)

# Nodo agente: invoca el modelo con el historial actual
def nodo_agente(estado: EstadoAgente) -> EstadoAgente:
    respuesta = modelo.invoke(estado["mensajes"])
    return {"mensajes": [respuesta]}

# Decisión de enrutamiento: ¿el modelo quiere usar herramienta o terminar?
def decidir_siguiente(estado: EstadoAgente) -> str:
    ultimo_mensaje = estado["mensajes"][-1]
    if hasattr(ultimo_mensaje, "tool_calls") and ultimo_mensaje.tool_calls:
        return "herramientas"
    return END

# Construcción del grafo
grafo = StateGraph(EstadoAgente)
grafo.add_node("agente", nodo_agente)
grafo.add_node("herramientas", ToolNode(herramientas))
grafo.set_entry_point("agente")
grafo.add_conditional_edges("agente", decidir_siguiente)
grafo.add_edge("herramientas", "agente")

agente_compilado = grafo.compile()
```

**Bloque D — LangChain clásico (`create_react_agent`)**

```python
from langchain.agents import create_react_agent, AgentExecutor
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate

# Herramientas del dominio con descripciones en español
@tool
def consultar_notas(estudiante_id: str, asignatura: str) -> str:
    """Consulta las notas de un estudiante en una asignatura específica."""
    return f"Nota de {asignatura}: 8.5 — aprobado"

@tool
def consultar_matricula(estudiante_id: str) -> str:
    """Devuelve el estado actual de matrícula del estudiante."""
    return "Matrícula activa — semestre 2026-1 — 18 créditos"

herramientas = [consultar_notas, consultar_matricula]

# Prompt ReAct estándar adaptado al dominio
prompt = ChatPromptTemplate.from_template(
    "Eres un asistente universitario. Responde preguntas de estudiantes.\n"
    "Herramientas disponibles:\n{tools}\n"
    "Nombres de herramientas: {tool_names}\n\n"
    "Pregunta: {input}\n"
    "Razonamiento previo: {agent_scratchpad}"
)

modelo = ChatOpenAI(model="gpt-4o", temperature=0)

# Construcción del agente y del ejecutor con límite de iteraciones
agente = create_react_agent(modelo, herramientas, prompt)
ejecutor = AgentExecutor(
    agent=agente,
    tools=herramientas,
    max_iterations=5,          # límite defensivo
    handle_parsing_errors=True,
    verbose=True,
)

def responder(mensaje: str) -> str:
    resultado = ejecutor.invoke({"input": mensaje})
    return resultado["output"]
```

Comparando los cuatro bloques, la API de Pydantic AI resulta la más concisa: el decorador `@agente.tool` sobre una función tipada es todo lo necesario para registrar una herramienta, y el ciclo de ejecución queda implícito en `agente.run()`. LangGraph es la opción más explícita en cuanto a flujo: el grafo de estados, los nodos y las aristas son visibles en el código, lo que facilita el razonamiento sobre el comportamiento del agente pero añade boilerplate considerable. LangChain clásico es la más opinionada de las tres: impone el formato de prompt ReAct, gestiona el scratchpad de razonamiento y encapsula el ciclo en `AgentExecutor`, lo que reduce las decisiones de diseño pero también reduce el control fino sobre lo que ocurre en cada iteración.

#### 5.1.6 Criterios de éxito

El Paso 1 se considera exitoso cuando se cumplen las tres condiciones siguientes:

- **Paridad de casos de uso.** El agente ReAct resuelve correctamente todos los escenarios que el flujo determinista original resolvía — sin regresiones en funcionalidad ni en coherencia de respuestas para el vocabulario y las preguntas habituales de los usuarios de esa intención.
- **Métricas comparables.** La latencia media por interacción, el costo en tokens por sesión y la tasa de respuestas correctas sobre un conjunto canónico de casos de prueba son comparables a los del flujo original, con márgenes explícitamente acordados antes del despliegue.
- **Batería de tests de regresión.** Existe un conjunto de 20 a 30 casos de prueba documentados para esa intención — alineado con la recomendación del auditor en la auditoría previa — que se ejecuta de forma automatizada contra ambas implementaciones (agente y flujo original) antes de cualquier decisión de retirar el flujo determinista. Esta batería no es opcional: es el mecanismo que convierte la evaluación de calidad de una opinión en una medición.


### 5.2 Paso 2 — Generalizar a agente único con skills

#### 5.2.1 Cuándo dar este paso

El criterio de entrada al Paso 2 no es temporal, sino estructural. Cuando se hayan refactorizado **tres o cuatro intenciones** siguiendo el patrón del Paso 1, sucederá algo predecible: el equipo notará que el código de cada agente es esencialmente idéntico. El prompt de sistema sigue el mismo esquema, el ciclo ReAct es el mismo, el límite de iteraciones es el mismo. Lo único que varía de un agente a otro son las herramientas disponibles y el texto que describe el dominio de esa intención.

Esa convergencia es la señal. Cuando el patrón se repite con pocas variaciones en cuatro intenciones distintas, mantener N instancias de código casi idéntico deja de ser una decisión de diseño y se convierte en deuda técnica. Es el momento de dar el salto: consolidar N agentes convergentes en un único agente generalista, y trasladar lo que los diferenciaba — el conocimiento de dominio — a documentos declarativos llamados **skills**.

Si el equipo llega al Paso 2 después de refactorizar solo dos intenciones y ya ve la convergencia con claridad, puede anticiparlo. Si después de cuatro intenciones el código todavía diverge significativamente entre agentes, conviene investigar por qué antes de generalizar.

#### 5.2.2 Diseño: agente generalista con registro de skills

El cambio conceptual central del Paso 2 es que el **clasificador de intenciones desaparece como componente de código** y su función es absorbida por el agente. El agente no recibe la intención del usuario ya clasificada: recibe el texto del usuario directamente, consulta un registro de skills disponibles, decide cuál activar y actúa en consecuencia.

Un **skill** es un archivo Markdown con tres partes fijas:

- **`description`** (frontmatter YAML): una o dos oraciones que describen cuándo este skill es relevante — el criterio de activación. El agente lee estas descripciones para decidir qué skill cargar, de manera análoga a como Claude Code selecciona skills del repositorio de la sesión.
- **`body`** (cuerpo del Markdown): guía narrativa de cómo abordar el problema — no código, sino instrucciones en lenguaje natural que amplían el contexto del agente para ese dominio. Describe qué información buscar, en qué orden, qué considerar ante casos ambiguos.
- **`tools`** (frontmatter YAML, lista): el subconjunto de herramientas relevantes para este dominio.

**Activar un skill** significa dos cosas concretas en el ciclo del agente: (1) cargar el `body` del skill como contexto adicional en el prompt del sistema, y (2) restringir las herramientas disponibles para esta invocación al conjunto declarado en `tools`. El agente no pierde acceso al resto de su lógica; simplemente opera dentro del foco que el skill le da.

Este diseño mantiene la separación de responsabilidades que el equipo ya conoce del clasificador: el agente sabe *cómo* razonar y actuar; el skill sabe *qué* hacer en un dominio particular. Lo que cambia es el mecanismo de despacho: en lugar de un módulo de clasificación con lógica fija, es el propio agente quien hace la selección de manera flexible sobre descripciones declarativas.

#### 5.2.3 Qué se gana

**Añadir una nueva intención cuesta escribir un Markdown.** Cero código nuevo. Cero reentrenamiento del clasificador. Cero modificaciones al agente central. Un desarrollador crea el archivo `nueva_funcionalidad.md`, escribe la descripción de activación, la guía narrativa y la lista de herramientas, versiona el archivo con el resto del proyecto y la funcionalidad está disponible en el próximo despliegue. El costo marginal de cada intención nueva cae de horas a minutos.

**Las intenciones empiezan a poder componerse.** Cuando un usuario hace una pregunta que cruza dos dominios — "¿cuándo es mi próximo examen de historia y qué nota saqué la última vez?" — el agente puede activar dos skills simultáneamente, cargar ambos contextos y responder de forma integrada. La arquitectura de flujos deterministas del Paso 0 no tiene mecanismo para esto; la del Paso 2 lo hereda de la naturaleza flexible del ciclo ReAct.

**El conocimiento de dominio queda declarativo y revisable por no-técnicos.** El `body` de un skill es texto en español. El área educativa de la UBE puede revisar si la guía para responder preguntas de historia es correcta, si falta algún caso borde, si el tono es el adecuado — sin entender LangGraph ni Pydantic AI. Esta propiedad no es menor: en el modelo de flujos deterministas, el conocimiento de dominio vive en código Python; aquí vive en documentos versionados que el equipo completo puede auditar.

#### 5.2.4 Qué se pierde

La honestidad intelectual exige señalar tres costos reales que el Paso 2 introduce.

**Determinismo.** Los flujos del Paso 0 garantizan la misma secuencia de tool calls en cada ejecución dado el mismo input. En el Paso 2 esa garantía desaparece: el agente puede tomar caminos diferentes ante la misma pregunta, dependiendo de la temperatura del modelo, del historial de la conversación y de cómo el skill guía su razonamiento. Para la mayoría de las intenciones esto no es un problema — la respuesta correcta puede llegar por varios caminos. Pero hay casos, como los que involucran validaciones de seguridad, donde la secuencia de acciones importa tanto como el resultado.

**Predictibilidad de costo.** Un flujo determinista tiene un número fijo y conocido de llamadas al modelo por interacción. Un agente ReAct puede hacer dos iteraciones o siete, dependiendo de la complejidad de la pregunta y de cómo el modelo interprete el contexto del skill. El costo por interacción se vuelve una distribución, no un valor fijo. Para un chatbot universitario con tráfico razonablemente predecible esto es manejable, pero el equipo debe monitorizar el promedio y el percentil 95.

**Predictibilidad de comportamiento ante casos extremos.** Un flujo determinista falla de maneras conocidas y reproducibles. Un agente puede fallar de maneras novedosas: activar el skill equivocado, interpretar la guía narrativa de forma inesperada, entrar en un bucle si las herramientas devuelven resultados que el skill no anticipó.

Las mitigaciones disponibles son tres y no son opcionales: **límites duros de iteración** por invocación (el mismo parámetro del Paso 1, ahora en el agente central), **caps de costo por sesión** configurados en la capa de infraestructura, y **telemetría agresiva** — cada invocación al agente debe registrar qué skill se activó, cuántas iteraciones realizó, qué herramientas llamó y cuál fue el costo en tokens. Sin esa telemetría, la operación del Paso 2 es ciega.

#### 5.2.5 Tecnología

La elección de biblioteca del Paso 1 no cambia en el Paso 2. Si el equipo eligió Pydantic AI, el agente generalista es el mismo agente del Paso 1 con su set de herramientas expandido y una capa de carga de skills añadida. Si eligió LangGraph, el grafo de estados existente se extiende con un nodo de selección de skill antes del ciclo ReAct.

Los skills viven como archivos `.md` con frontmatter YAML en una carpeta del repositorio — por convención, `skills/` en la raíz del proyecto del chatbot. Al estar en el repositorio, son versionados con el resto del código: el historial de cambios de un skill es legible en `git log`, los cambios de contenido son revisables en pull requests, y el rollback de un skill es tan simple como revertir un commit.

El **cargador de skills** es el único componente nuevo de código que este paso introduce. Es un módulo de aproximadamente 30 líneas que lee el directorio de skills, parsea el frontmatter de cada archivo, construye una representación interna de cada skill y la expone al agente al inicio de cada sesión. No hay magia: es lectura de archivos y parsing de YAML.

#### 5.2.6 Código ilustrativo

**Bloque A — Ejemplo de un skill Markdown (`responder_historia.md`)**

```markdown
---
description: >
  Activar cuando el estudiante pregunta sobre contenidos, fechas, eventos
  o personajes de la asignatura de Historia. También aplica para preguntas
  sobre el programa del curso o bibliografía recomendada.
tools:
  - buscar_documentos
  - consultar_notas
  - done
---

# Skill: Responder preguntas de Historia

El dominio de este skill cubre la asignatura de Historia tal como aparece
en el programa académico de la UBE. Las preguntas suelen ser de dos tipos:
preguntas de contenido (fechas, eventos, conceptos) y preguntas de seguimiento
académico (nota del estudiante, estado de evaluaciones pendientes).

Para preguntas de contenido, usa primero `buscar_documentos` con términos
específicos del tema mencionado. Si el documento encontrado es suficiente
para responder, responde directamente. Si la pregunta combina contenido con
datos del estudiante (por ejemplo, "¿aprobé el tema de la Revolución Francesa?"),
consulta también `consultar_notas` con la asignatura y el período correspondiente.

Mantén un tono académico y preciso. Si la información en los documentos es
insuficiente para responder con certeza, indícalo explícitamente antes de
dar una respuesta aproximada. No inventes datos de notas ni fechas de evaluación.
```

**Bloque B — Cargador de skills en Python (~25 líneas)**

```python
import os
import yaml
from pathlib import Path
from dataclasses import dataclass

@dataclass
class Skill:
    nombre: str
    description: str
    tools: list[str]
    body: str

def cargar_skills(directorio: str = "skills") -> list[Skill]:
    """Lee todos los archivos .md del directorio de skills y los parsea."""
    skills = []
    for ruta in Path(directorio).glob("*.md"):
        contenido = ruta.read_text(encoding="utf-8")

        # Separar frontmatter YAML del cuerpo Markdown
        if contenido.startswith("---"):
            _, fm_raw, body = contenido.split("---", 2)
            frontmatter = yaml.safe_load(fm_raw)
        else:
            raise ValueError(f"Skill sin frontmatter YAML: {ruta.name}")

        skills.append(Skill(
            nombre=ruta.stem,
            description=frontmatter["description"].strip(),
            tools=frontmatter.get("tools", []),
            body=body.strip(),
        ))
    return skills

def seleccionar_skill(skills: list[Skill], mensaje_usuario: str, agente) -> Skill | None:
    """El agente lee las descripciones y elige el skill más relevante."""
    menu = "\n".join(f"- {s.nombre}: {s.description}" for s in skills)
    prompt = (
        f"Dado el siguiente mensaje del usuario:\n\n\"{mensaje_usuario}\"\n\n"
        f"¿Cuál de estos skills es el más relevante? Responde solo con el nombre.\n\n{menu}"
    )
    nombre_elegido = agente.clasificar(prompt)  # llamada ligera al modelo
    return next((s for s in skills if s.nombre == nombre_elegido), None)
```

El patrón de uso es directo: al inicio de cada conversación se llama a `cargar_skills()`, se obtiene la lista de `Skill` disponibles, y antes de invocar el ciclo ReAct se llama a `seleccionar_skill()` para determinar qué contexto adicional y qué herramientas activar. El agente recibe entonces el `body` del skill concatenado a su prompt de sistema y el subconjunto de `tools` declarado en el frontmatter.

---

### 5.3 Paso 3 — Recuperación selectiva de determinismo

#### 5.3.1 Por qué este paso existe

El Paso 2 resolvió el problema de escalabilidad en ancho, pero lo hizo a un costo que se identificó con honestidad en la sección anterior: perdimos los flujos deterministas. Para la mayor parte de las interacciones del Chatbot UBE esa pérdida es aceptable — preguntar por una nota, consultar el estado de una matrícula o buscar información en un documento de historia no requiere una secuencia garantizada de acciones. El agente puede llegar al resultado correcto por distintos caminos.

Sin embargo, hay un conjunto reducido de funcionalidades donde la secuencia de pasos no es solo una cuestión de eficiencia sino de corrección. Un proceso que consulta datos sensibles antes de verificar la identidad del usuario, o que acepta una matrícula sin validar previamente los prerrequisitos, no solo es ineficiente si se ejecuta en el orden equivocado: es incorrecto. El Paso 3 recupera exactamente esa propiedad — determinismo de secuencia — para los casos que lo necesitan, sin renunciar a la flexibilidad agéntica que el Paso 2 introdujo.

La distinción clave con la arquitectura del Paso 0 es que el determinismo se recupera **encima del agente**, no en lugar de él. Los pasos de la secuencia no son llamadas directas al modelo de lenguaje con prompts fijos: son invocaciones completas al agente con todo su ciclo ReAct, sus herramientas y sus skills activos. El determinismo opera en el nivel de la secuencia de invocaciones; la flexibilidad opera dentro de cada invocación.

#### 5.3.2 Diseño: flujos como secuencias de instrucciones sobre el agente

En el Paso 2, un skill es un único archivo Markdown. En el Paso 3, un skill que requiere flujo determinista se convierte en una **secuencia ordenada de instrucciones**, donde cada instrucción es también un Markdown pero representa un paso discreto del proceso. El orquestador ejecuta esos pasos en orden estricto, pasando el resultado de cada uno como contexto del siguiente.

La arquitectura resultante tiene tres capas:

1. **Orquestador** — componente de 50-100 líneas que toma una lista de paths a archivos Markdown de instrucciones y los ejecuta en secuencia.
2. **Instrucción** — un Markdown con estructura similar al skill del Paso 2, pero más acotado: describe un único paso del proceso (por ejemplo, "verificar identidad del estudiante" o "validar prerrequisitos de matrícula").
3. **Agente** — el mismo agente generalista del Paso 2, invocado por el orquestador en cada paso con el contexto de la instrucción actual más el output acumulado de los pasos anteriores.

Esta arquitectura replica la estructura de los flujos deterministas del Paso 0, pero con una diferencia fundamental: lo que antes era una secuencia de llamadas al modelo de lenguaje con prompts cableados es ahora una secuencia de invocaciones al agente completo. Cada paso tiene acceso al ciclo ReAct, a las herramientas y a la capacidad de razonar sobre situaciones que el programador no anticipó. El agente puede, dentro del ámbito de un paso, hacer tres tool calls o una, según la complejidad real de la situación — pero no puede saltarse el paso siguiente ni ejecutarlos fuera de orden.

#### 5.3.3 Cuándo aplicarlo

Este paso es una herramienta selectiva, no una dirección general. La regla es sencilla: aplicar flujo determinista solo cuando la secuencia de acciones sea una propiedad de **corrección o seguridad**, no una preferencia de eficiencia.

Los casos que lo justifican son aquellos con validaciones de seguridad intermedias que bloquean pasos posteriores: verificación de identidad del estudiante antes de devolver datos académicos, validación de prerrequisitos antes de confirmar una matrícula, autorización antes de ejecutar una acción irreversible. En estos casos, un agente que decida saltarse un paso de validación por eficiencia no comete un error de calidad — comete un error de lógica de negocio o seguridad.

Los casos que **no** lo justifican son todos los demás. Preguntas de contenido académico, consultas de estado, búsquedas en documentos: el agente sin orquestador determinista los resuelve bien, y añadir la capa de orquestación solo introduce complejidad sin ganancia real.

Una heurística útil: si la respuesta a "¿importa el orden en que el agente hace las cosas?" es "sí, y de lo contrario el sistema es inseguro o incorrecto", aplicar el Paso 3. En cualquier otro caso, confiar en el agente del Paso 2.

#### 5.3.4 Tecnología

El orquestador es el único componente de código nuevo que este paso requiere. Su tamaño razonable es de 50 a 100 líneas: un bucle que itera sobre una lista de instrucciones, invoca al agente en cada paso con el contexto acumulado y captura el output para pasarlo al siguiente paso.

LangGraph es una opción natural si ya está en el stack del equipo desde el Paso 1: su modelo de grafo de estados encaja directamente con la noción de pasos ordenados que se alimentan mutuamente. Sin embargo, si el equipo eligió Pydantic AI, un loop Python es completamente suficiente — no hay necesidad de introducir LangGraph solo para este componente. La complejidad de un orquestador de cuatro o cinco pasos no justifica una dependencia adicional.

#### 5.3.5 Código ilustrativo

**Pseudocódigo Python del orquestador determinista (~20 líneas)**

```python
from pathlib import Path
from dataclasses import dataclass

@dataclass
class ResultadoPaso:
    paso: int
    instruccion: str
    output: str
    exitoso: bool

def ejecutar_flujo(
    instrucciones: list[str],   # lista de paths a archivos .md
    contexto_inicial: str,      # mensaje original del usuario
    agente,                     # instancia del agente generalista (Paso 2)
    max_iter_por_paso: int = 5,
) -> list[ResultadoPaso]:
    """Ejecuta una secuencia determinista de instrucciones sobre el agente."""
    resultados = []
    contexto_acumulado = contexto_inicial

    for indice, path_instruccion in enumerate(instrucciones):
        instruccion = Path(path_instruccion).read_text(encoding="utf-8")

        # Cada paso recibe el texto de la instrucción más el historial acumulado
        prompt_paso = (
            f"=== Paso {indice + 1} de {len(instrucciones)} ===\n"
            f"{instruccion}\n\n"
            f"=== Contexto acumulado ===\n{contexto_acumulado}"
        )

        output = agente.run(prompt_paso, max_iterations=max_iter_por_paso)

        resultados.append(ResultadoPaso(
            paso=indice + 1,
            instruccion=path_instruccion,
            output=output,
            exitoso=True,  # en producción: validar output antes de continuar
        ))

        # El output de este paso alimenta el contexto del siguiente
        contexto_acumulado += f"\n\n--- Resultado del paso {indice + 1} ---\n{output}"

    return resultados
```

El punto crítico del orquestador está en la línea de validación marcada con el comentario: en producción, antes de continuar al siguiente paso, el orquestador debe verificar que el output del paso actual satisface el criterio de éxito definido para ese paso. Si el agente no pudo verificar la identidad del estudiante, el flujo no debe continuar al paso de consulta de datos sensibles — debe detenerse y devolver un error controlado. La implementación de esa validación es específica del dominio de cada flujo y no puede ser genérica.

---

### 5.4 Cuadro síntesis de la migración

La tabla siguiente consolida los tres pasos en una vista única de esfuerzo, impacto y garantías.

| Paso | Duración aprox. | Disrupción | Reversibilidad | Entrega |
|---|---|---|---|---|
| **1** — Refactorizar UNA intención como agente ReAct | 2–3 semanas | Mínima — afecta 1 de 13 flujos; el resto permanece sin cambios | Total — si el agente no satisface los criterios de éxito, el flujo original se reactiva sin modificar | Agente ReAct funcionando en producción para una intención, con batería de tests de regresión y benchmark side-by-side |
| **2** — Agente generalista + skills declarativos | 4–6 semanas | Media — el clasificador central se reemplaza; todos los flujos refactorizados en el Paso 1 migran al nuevo modelo | Parcial — el código del agente generalista es el nuevo baseline; volver al clasificador requiere reescribir el dispatcher, aunque los flujos deterministas originales aún existen en el historial de git | Sistema unificado con N skills Markdown versionados, un agente central y telemetría operativa |
| **3** — Recuperación selectiva de determinismo | 2–3 semanas | Mínima — es aditivo; el agente del Paso 2 no se modifica | Total — el orquestador es una capa sobre el agente; eliminarlo devuelve exactamente el comportamiento del Paso 2 | Flujos deterministas reintroducidos para las intenciones que lo requieren, construidos sobre el agente generalista |


## 6. Comparación visual: los cuatro diagramas en perspectiva

Los cuatro diagramas distribuidos a lo largo de este reporte no son ilustraciones independientes: son cuatro fotogramas de una misma progresión. Leerlos en secuencia — Diagrama 1, Diagrama 2, Diagrama 3, Diagrama 4 — es seguir el eje que atraviesa todo el análisis: **¿cuánto cuesta añadir una intención nueva?** El costo marginal de crecer en ancho es la métrica que diferencia a los cuatro arquetipos y la que justifica la hoja de ruta propuesta. Esta sección invita a leer los diagramas como conjunto, no de forma aislada, para que la propuesta de migración tenga una imagen mental clara detrás.

**Diagrama 1 — Arquetipo A: enrutador + flujos deterministas** (sección 3.2). Muestra el estado actual del Chatbot UBE: un clasificador de intenciones en la raíz que enruta hacia N flujos deterministas independientes. Ante la pregunta de costo marginal, la respuesta es directa y estructuralmente cara: añadir una intención nueva requiere un flujo nuevo desde cero — nuevas ramas de código, nuevas herramientas cableadas, reentrenamiento del clasificador. La anotación del diagrama lo hace explícito. Este es el punto de partida.

**Diagrama 2 — Arquetipo B: agente puro** (sección 4.2). Muestra el extremo opuesto: un único ciclo agéntico con acceso simultáneo a todas las herramientas. El costo marginal de añadir una intención nueva es mínimo — en teoría basta con añadir una herramienta y el agente la descubrirá. Pero el diagrama también revela el precio: no hay enrutamiento, no hay determinismo, no hay garantías sobre la secuencia de acciones. Lo que se gana en flexibilidad se pierde en trazabilidad. Por eso este arquetipo se presenta como destino conceptual, no como paso inmediato.

**Diagrama 3 — Arquetipo C: híbrido enrutador + agentes especializados** (sección 4.3). Muestra la etapa de transición: el clasificador permanece, pero cada flujo determinista se reemplaza por un mini-agente ReAct con sus herramientas propias. Añadir una intención nueva sigue requiriendo una rama nueva, pero el interior de esa rama ya no es un script fijo — es un ciclo iterativo con capacidad de razonamiento. El costo marginal baja un escalón, el riesgo operativo permanece acotado. Este es el arquetipo que corresponde al Paso 1 de la hoja de ruta.

**Diagrama 4 — Arquetipo D: agente generalista + skills** (sección 4.4). Muestra el destino de la migración propuesta: un agente central con un registro de skills declarativos. El clasificador de intenciones desaparece como componente de código; su función la absorbe el agente al evaluar las descripciones de los skills disponibles. Añadir una intención nueva cuesta escribir un archivo Markdown. El costo marginal colapsa — y eso es exactamente lo que el análisis de escalabilidad de la sección 3.4 pedía resolver.

---

## 7. Riesgos y mitigaciones

Una propuesta de arquitectura que no nombra sus riesgos no es honesta: es publicidad. Esta sección enumera los riesgos reales de la migración propuesta y las mitigaciones concretas disponibles. Ninguna mitigación elimina el riesgo; todas lo reducen a niveles manejables si se aplican con disciplina.

### 7.1 Riesgos técnicos

- **Imprevisibilidad del agente.** Un agente ReAct puede decidir invocar herramientas en órdenes inesperados, hacer más iteraciones de las previstas ante formulaciones ambiguas del usuario, o devolver respuestas coherentes pero incorrectas sin señal de error. A diferencia de un flujo determinista, los modos de fallo son variados y no siempre reproducibles. *Mitigación:* límites duros de iteración configurados como parámetro del agente (recomendado: cinco iteraciones para el Paso 1); fallback explícito al flujo determinista original mientras ambas implementaciones coexisten en staging; telemetría desde el primer día — cada invocación debe registrar el número de iteraciones, las herramientas llamadas y el resultado.

- **Costo por interacción.** El costo computacional de un flujo determinista es fijo y predecible: N llamadas al modelo por interacción, siempre las mismas. Un agente puede usar dos iteraciones o siete dependiendo de la pregunta. El costo por interacción se convierte en una distribución, no en un valor fijo, y esa distribución puede tener cola larga si no se acota. *Mitigación:* caps de tokens por sesión configurados en la capa de infraestructura; uso de modelos más ligeros para la selección de skills (operación de clasificación simple) y del modelo más capaz solo en el ciclo ReAct; revisión periódica del percentil 95 de costo por interacción contra el promedio del flujo original.

- **Degradación de calidad respecto al flujo determinista actual.** El riesgo más silencioso: el agente puede resolver los casos canónicos correctamente durante el desarrollo y fallar en producción ante variaciones de lenguaje, formulaciones inesperadas o combinaciones de contexto que el flujo original manejaba de forma mecánica. *Mitigación:* el Paso 1 no se considera exitoso hasta que exista una batería de 20 a 30 tests de regresión ejecutados en paralelo contra el flujo original y el agente, con resultados comparables en latencia, precisión y coherencia. El benchmark side-by-side no es opcional — es la única forma de convertir "parece funcionar" en "funciona".

### 7.2 Riesgos organizacionales

- **Equipo sin experiencia agéntica.** El Chatbot UBE fue construido con un patrón que el equipo conoce bien y puede depurar con confianza. Los patrones agénticos introducen ciclos iterativos, razonamiento no lineal y modos de fallo difíciles de reproducir en tests unitarios clásicos. Un equipo que afronta esto sin preparación tiende a sobreconfiar en el comportamiento del agente durante el desarrollo y a subestimar la complejidad operativa en producción. *Mitigación:* el Paso 1 está diseñado deliberadamente como entorno de aprendizaje acotado. El mini-agente de una sola intención es lo suficientemente pequeño para ser entendido en su totalidad por el desarrollador que lo construya. La experiencia acumulada en el Paso 1 — depuración, telemetría, criterios de éxito — es el capital que hace viable el Paso 2.

- **Pérdida de control percibido.** Los flujos deterministas tienen una propiedad psicológica importante: cualquier desarrollador puede leerlos y predecir qué hará el sistema ante cualquier input. Con agentes, esa legibilidad directa desaparece. El equipo puede percibir que el sistema "hace cosas solas" y sentir que ha perdido el control, incluso cuando el comportamiento real es correcto. Ese malestar puede generar resistencia a la migración o, peor, decisiones apresuradas de volver al flujo determinista ante el primer comportamiento inesperado. *Mitigación:* los skills del Paso 2 son la respuesta a este riesgo. El conocimiento de dominio — qué debe hacer el agente y en qué circunstancias — vive en archivos Markdown versionados y legibles por cualquier miembro del equipo, incluidos los no técnicos. El control no desaparece: se traslada del código al texto declarativo. La telemetría operativa hace visible qué skill se activó y qué herramientas llamó el agente en cada interacción, restaurando la trazabilidad por observación en lugar de por inspección del código.

### 7.3 Riesgos de migración

- **Tentación de saltar directamente al Paso 2.** Una vez comprendido el arquetipo D — agente generalista con skills — la arquitectura del Paso 1 puede parecer un rodeo innecesario. El equipo puede sentir la tentación de implementar el agente generalista directamente, sin pasar por el período de aprendizaje acotado que el Paso 1 proporciona. Ese movimiento tiene un nombre en la práctica de proyectos de software: *big-bang migration*. Implica reemplazar simultáneamente el clasificador, todos los flujos deterministas y el modelo de código, sin ninguna referencia funcionando contra la cual comparar. Si algo falla — y en una migración de ese tamaño algo siempre falla — el diagnóstico es exponencialmente más difícil porque no hay un baseline estable al cual volver. *Mitigación explícita: el Paso 1 no es opcional.* No es un refinamiento gradualista ni una precaución excesiva: es la única forma de construir la experiencia, la telemetría y los criterios de éxito que harán al Paso 2 manejable. Un equipo que haya pasado por el Paso 1 llega al Paso 2 con un agente ya probado, con una batería de tests ya escrita y con la confianza operativa para desplegar. Un equipo que salte al Paso 2 directamente llega con ninguna de esas tres cosas.

---

## 8. Recomendaciones concretas y siguientes pasos

### 8.1 Acciones inmediatas — próximas 2 semanas

- **Confirmar el entendimiento de la sección 3.1.** Antes de cualquier trabajo de implementación, el equipo UBE debe revisar la descripción de la arquitectura actual y señalar qué está correcto, qué está incompleto y qué está mal. Si los "agentes" actuales sí tienen ciclo iterativo propio, parte del análisis cambia. Esta confirmación no es un trámite: es la base sobre la que se apoya toda la propuesta.
- **Seleccionar el candidato para el Paso 1.** Aplicar los tres criterios de la sección 5.1.2 sobre el conocimiento real del equipo: sencillez de herramientas, bajo riesgo operativo, volumen suficiente para generar datos. Proponer un candidato concreto — no una categoría, sino una intención específica del sistema.
- **Decidir el stack tecnológico.** Pydantic AI o LangGraph. Nuestra recomendación está en la sección 5.1.4; la decisión final corresponde al equipo y debe tomar en cuenta la experiencia existente con LangChain y la preferencia del desarrollador que liderará el Paso 1. Esta decisión bloquea el inicio del diseño del agente.
- **Definir la batería de tests de regresión.** Documentar 20 a 30 casos de prueba representativos para la intención candidata, con inputs reales de producción cuando sea posible. Esta batería debe existir antes de que el agente se escriba, no después — es lo que permite evaluar la paridad con el flujo original de forma objetiva.

### 8.2 Hitos del primer mes

- **Paso 1 desplegado en staging.** El agente ReAct de la intención candidata está funcionando en un entorno de staging con acceso a las mismas herramientas que el flujo original, con telemetría básica activa y con el límite de iteraciones configurado.
- **Benchmark side-by-side completado.** La batería de tests de regresión se ha ejecutado contra el flujo original y contra el agente. Los resultados están documentados con métricas comparables de latencia, costo en tokens y precisión sobre los casos canónicos.
- **Decisión informada sobre continuar al Paso 2.** Con el benchmark en mano, el equipo tiene base objetiva para decidir si el patrón agéntico produce resultados comparables al flujo original y si la experiencia acumulada justifica escalar al Paso 2. Esta no es una decisión de autorización — es una decisión técnica informada. Si los resultados no son comparables, el diagnóstico de por qué no lo son es en sí mismo conocimiento valioso que guiará la corrección.

### 8.3 Dependencias con la auditoría previa

Este reporte se centra en arquitectura de agentes y evolución del sistema de intenciones. **No sustituye ni reemplaza las recomendaciones de la auditoría previa** (`auditoria_ube_v2`). Los dos análisis son complementarios y sus acciones deben ejecutarse en paralelo, no en secuencia.

Las siguientes recomendaciones de la auditoría son **bloqueantes** para cualquier trabajo en producción, con independencia de la migración arquitectónica:

- Corrección de la configuración de seguridad: CSRF tokens, `ALLOWED_HOSTS`, forzado de HTTPS.
- Cobertura de tests sobre el sistema actual, incluyendo tests de integración para los flujos existentes.
- Evaluación de la migración de Django 3.2 a una versión con soporte activo.

Estas acciones no compiten con la hoja de ruta de este reporte: son prerequisitos de infraestructura que deben resolverse independientemente de la decisión sobre arquitectura de agentes.

Un punto de confluencia que merece énfasis particular: la batería de tests del clasificador de intenciones sugerida por el auditor se vuelve **más urgente**, no menos, con este plan de migración. En la auditoría, esos tests eran una recomendación de calidad general. En el contexto de este reporte, son el *baseline* contra el cual se medirá cada refactorización del Paso 1. Sin esa batería documentada y ejecutable antes de la migración, no hay forma de distinguir entre "el agente mejoró la calidad" y "el agente se comporta diferente al flujo original de formas que aún no hemos detectado". Son la misma recomendación con doble urgencia.

### 8.4 Lo que ofrecemos como asesoría

El alcance de este reporte es analítico: describe el problema, propone una hoja de ruta y entrega los criterios para tomar decisiones informadas. La implementación es responsabilidad del equipo UBE. Sin embargo, ofrecemos acompañamiento técnico en las etapas críticas:

- **Selección del candidato del Paso 1.** Revisión conjunta de los criterios sobre los 13 flujos actuales para identificar el mejor punto de entrada. Una sesión de una hora con el equipo es suficiente para esta decisión.
- **Code review del primer agente ReAct.** Revisión del diseño del agente antes de su despliegue en staging: estructura del ciclo ReAct, definición de herramientas, prompt del sistema, límites defensivos y telemetría básica.
- **Revisión de los primeros skills.** Cuando el equipo llegue al Paso 2 y empiece a escribir los primeros archivos Markdown de skills, revisión del esquema adoptado para asegurar que las descripciones de activación son suficientemente discriminativas y que el `body` narrativo guía al agente de forma efectiva.
- **Sesiones de Q&A según necesidad.** Disponibilidad para sesiones técnicas a demanda durante el Paso 1 — en particular para depuración de comportamientos inesperados del agente y para la interpretación de los resultados del benchmark side-by-side.

---

## 9. Apéndices

### 9.1 Apéndice A — Glosario

| Término | Definición |
|---|---|
| **ReAct** | *Reasoning + Acting*. Patrón agéntico donde el modelo de lenguaje alterna entre razonar (producir un pensamiento sobre el siguiente paso) y actuar (invocar una herramienta), observando el resultado de cada acción antes de la iteración siguiente. El ciclo termina cuando el agente invoca la herramienta de terminación explícita o alcanza el límite de iteraciones. |
| **Skill** | Documento Markdown con frontmatter YAML que encapsula el conocimiento de dominio de una intención concreta. Contiene una descripción de activación (cuándo es relevante este skill), un cuerpo narrativo (cómo abordar el problema en lenguaje natural) y un listado de herramientas disponibles para ese dominio. No es código ejecutable: es conocimiento declarativo. |
| **Herramienta (tool)** | Función Python que el agente puede invocar durante su ciclo ReAct. Recibe argumentos tipados, ejecuta una operación concreta — consulta a base de datos, búsqueda en documentos, llamada a API externa — y devuelve un resultado que el agente incorpora a su razonamiento. La herramienta `done` es la terminación explícita estándar. |
| **Clasificador de intenciones** | Componente que recibe el mensaje del usuario y predice una etiqueta de intención de un conjunto cerrado predefinido. En la arquitectura actual del Chatbot UBE, es el dispatcher raíz que enruta hacia los flujos deterministas. En la arquitectura propuesta, desaparece como componente de código independiente y su función es absorbida por el mecanismo de selección de skills del agente generalista. |
| **Agente generalista** | Agente ReAct único que sirve para múltiples dominios, especializado en tiempo de ejecución mediante la activación dinámica de skills. A diferencia de los agentes especializados del arquetipo C, no tiene herramientas ni prompt cableados para un dominio específico: su comportamiento de dominio lo aporta el skill activado en cada interacción. |
| **Ciclo agéntico** | La secuencia iterativa de operaciones de un agente ReAct: recibir el estado actual (historial de mensajes y observaciones previas), producir un razonamiento, decidir una acción (invocar una herramienta o terminar), ejecutar la acción y observar el resultado. El ciclo se repite hasta que el agente termina o se alcanza el límite de iteraciones. |
| **Flujo determinista** | Secuencia predefinida de operaciones sobre el modelo de lenguaje: el código especifica exactamente qué llamadas se hacen, en qué orden y con qué parámetros. Dado el mismo input, siempre produce la misma secuencia de acciones. En la arquitectura actual del Chatbot UBE, cada intención tiene su propio flujo determinista. En el Paso 3 de la migración, ciertos flujos deterministas se recuperan *encima* del agente generalista para casos donde la secuencia de acciones es una propiedad de corrección o seguridad. |

### 9.2 Apéndice B — Referencias

- **Pydantic AI** — biblioteca Python para construcción de agentes con tipado fuerte y primitivas de bajo nivel. Documentación: `https://ai.pydantic.dev`
- **LangGraph** — framework de grafos de estado para agentes y flujos multi-paso, parte del ecosistema LangChain. Documentación: `https://langchain-ai.github.io/langgraph`
- **LangChain** — `AgentExecutor` y `create_react_agent` son los componentes relevantes para implementaciones ReAct clásicas con este framework. Documentación: `https://python.langchain.com`
- **Patrón de skills** — el diseño de conocimiento de dominio como archivos Markdown activables dinámicamente por el agente está inspirado en el modelo de gestión de capacidades especializadas de Claude Code (Anthropic). La referencia no es a una publicación técnica sino a un patrón observable en herramientas de agentes de segunda generación: separar el motor de razonamiento del conocimiento de dominio mediante documentos declarativos evaluables por el propio agente.
- **Cliente empresarial previo en Cuba** — experiencia del asesor con un chatbot de arquitectura jerárquica determinista que alcanzó un techo de complejidad análogo al descrito en la sección 3.4. Las lecciones de ese proyecto — en particular la aceleración del costo marginal pasados los 15-20 flujos y la dificultad de composición entre dominios — son la fuente empírica de las advertencias de escalabilidad de este reporte. Referencia interna, no publicada.
