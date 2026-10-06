# BACKEND Y API

Este documento explica las decisiones del backend. El código no lleva comentarios, así que el porqué de cada decisión está aquí.

## Capas

```text
api/           Recibe la petición HTTP y valida los datos (schemas).
services/      Lógica de negocio y control de permisos.
repositories/  Consultas a la base de datos.
models.py      Tablas (SQLAlchemy). Debe coincidir con BASE-DE-DATOS-ARQUILA/migrations/.
```

Los errores de negocio son excepciones propias (`errors.py`) que `main.py` convierte en respuestas HTTP:

| Código | Significado |
|---|---|
| 401 | No hay sesión o la sesión no es válida. |
| 404 | El recurso no existe o pertenece a otro usuario. |
| 409 | Conflicto: correo o nombre ya usados. |
| 413 | El archivo supera el tamaño máximo. |
| 415 | Tipo de archivo no admitido. |
| 400 | El enlace de recuperación de contraseña no es válido o caducó. |
| 422 | Los datos enviados no son válidos. |
| 429 | Demasiados intentos fallidos de inicio de sesión. |

## Patrón Adapter

El backend habla con dos servicios externos: el de IA y el de correo. Cada uno tiene su propia forma de llamarse, distinta de lo que la aplicación necesita. Para que los servicios de la aplicación no dependan de esas librerías, cada servicio externo se usa a través de un adaptador: una clase que ofrece la interfaz que la aplicación espera y la traduce a las llamadas de la librería.

| Interfaz que usa la aplicación | Adaptador | Qué adapta |
|---|---|---|
| `Assistant.reply(system, messages)` devuelve un texto | `OllamaAssistant` en `app/ai.py` | Un modelo local servido por Ollama, por HTTP: elige el modelo, envía la conversación, limpia la respuesta y convierte los fallos en `AIUnavailableError`. |
| `Mailer.send(recipient, subject, body)` | `SmtpMailer` en `app/mailer.py` | La librería `smtplib`: construye el mensaje, abre la conexión cifrada, se identifica y envía. |
| `Mailer.send(recipient, subject, body)` | `ConsoleMailer` en `app/mailer.py` | La consola del servidor, para desarrollo sin correo configurado. |

`AuthService` y `ConversationService` solo conocen las interfaces `Mailer` y `Assistant`. Gracias a eso:

- cambiar de proveedor de IA o de correo significa escribir otro adaptador, sin tocar los servicios;
- las pruebas sustituyen el adaptador por uno simulado y no llaman a ningún servicio real.

Las interfaces se declaran con `typing.Protocol`: cualquier clase que tenga el método con esa forma sirve, sin necesidad de heredar. Los adaptadores tienen sus pruebas en `tests/test_adapters.py`.

## Autenticación

- El registro y el inicio de sesión crean una sesión y la entregan en una cookie `HttpOnly` con `SameSite=Lax`. Al ser `HttpOnly`, el código de la página no puede leerla; al ser `SameSite=Lax`, otros sitios no pueden usarla para enviar peticiones de escritura.
- En la base solo se guarda el hash SHA-256 del identificador de sesión, de modo que una copia de la base no permite suplantar sesiones.
- Las contraseñas se guardan con Argon2id (librería `argon2-cffi`, con sus parámetros por defecto: 64 MiB de memoria, 3 pasadas y 4 hilos) y una sal aleatoria por contraseña. Es el algoritmo que recomienda OWASP como primera opción.
- Las cuentas creadas antes de este cambio tienen la contraseña guardada con `scrypt`. Siguen funcionando: en el primer inicio de sesión correcto, el backend vuelve a guardar la contraseña con Argon2id. Lo mismo ocurre si más adelante se endurecen los parámetros.
- Un inicio de sesión fallido devuelve el mismo mensaje exista o no el correo y realiza la misma verificación de contraseña en ambos casos, para no revelar qué cuentas existen.
- La sesión dura 7 días y se elimina del servidor al cerrar sesión.
- En producción hay que definir `COOKIE_SECURE=1` para que la cookie solo viaje por HTTPS.
- `SameSite` se puede cambiar con `COOKIE_SAMESITE` (`lax`, `strict` o `none`). `none` solo hace falta si la interfaz y la API están en sitios distintos: el navegador exige entonces HTTPS, así que la cookie se marca `Secure` aunque `COOKIE_SECURE` valga `0`. Con `none` se pierde la protección de `SameSite` frente a peticiones de escritura desde otros sitios; las peticiones con cuerpo JSON siguen bloqueadas por CORS, pero la subida de archivos y el cierre de sesión no llevan esa barrera.

- Tras 5 intentos fallidos con el mismo correo en un minuto, el inicio de sesión responde 429 hasta que los intentos salen de esa ventana de tiempo. Un inicio de sesión correcto borra la cuenta de fallos. El control usa la cola de `app/data_structures` (ver `05_COMPLEJIDAD.md`) y vive en memoria, igual que el historial de deshacer.
- El control recuerda como máximo 10 000 correos a la vez; al llegar a ese número descarta los que ya caducaron, para que no pueda crecer sin límite.
- El límite se cuenta por correo, no por dirección IP: alguien que conozca un correo puede bloquear su inicio de sesión durante un minuto escribiendo contraseñas falsas.

### Recuperación de contraseña

- «Olvidé mi contraseña» pide un correo. Si existe una cuenta, se genera un enlace válido 30 minutos y de un solo uso; la respuesta es la misma exista o no la cuenta, para no revelar qué correos están registrados.
- En la base solo se guarda el hash del identificador del enlace. Pedir un enlace nuevo invalida el anterior.
- Al cambiar la contraseña se cierran todas las sesiones abiertas de esa cuenta.
- El correo se envía por SMTP si están definidas `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD` y `SMTP_FROM`. Si `SMTP_HOST` no está definida, el mensaje con el enlace se escribe en la consola del servidor: sirve para desarrollo, pero en producción hay que configurar el correo.
- `APP_URL` indica la dirección de la aplicación que se pone en el enlace.
- Se atienden como máximo 3 solicitudes por correo cada 15 minutos; las demás se ignoran sin avisar, con la misma respuesta. Usa el mismo control basado en la cola que el inicio de sesión.
- El envío real por SMTP no está probado: las pruebas usan un envío simulado.

## Permisos

Todo lo que pertenece a un proyecto exige sesión y que el proyecto sea del usuario. Un proyecto ajeno responde 404, igual que uno inexistente, para no revelar qué identificadores existen. La comprobación está centralizada en `services/base.py`.

## Archivos

- Se guardan en disco, en la carpeta indicada por `UPLOAD_DIR`, con un nombre aleatorio. El nombre original solo se guarda como texto para mostrarlo; nunca decide dónde se escribe el archivo.
- El tipo se detecta por los primeros bytes del contenido, no por la extensión ni por lo que declare el navegador. Se admiten PDF, PNG, JPEG y WebP, hasta 20 MB.
- Al eliminar un archivo se desvincula de forma explícita de los planos y elevaciones que lo usaban. No se depende de `ON DELETE SET NULL` porque SQLite, que se usa en las pruebas, solo lo aplica si se activan las claves foráneas.
- Al eliminar un proyecto se borran también sus archivos del disco.
- El botón «Ver», en la pestaña Archivos y junto al archivo adjunto de un plano o una elevación, abre el archivo dentro de la aplicación en una ventana superpuesta (`FRONTEND-ARQUILA/src/components/FileViewer.tsx` y `Modal.tsx`): las imágenes se muestran ajustadas a la ventana y los PDF con el lector del navegador. La ventana usa el elemento `<dialog>` del navegador, así que se cierra con Escape, con el botón «Cerrar» o pulsando fuera, y tiene un enlace para abrir el archivo en otra pestaña.

## Deshacer eliminaciones

- Se guarda un historial por proyecto de los terrenos, planos, elevaciones y materiales eliminados, con un máximo de 20 entradas.
- El historial usa la lista doblemente enlazada de `app/data_structures` (ver `05_COMPLEJIDAD.md`).
- Vive en memoria: se pierde al reiniciar el servidor y no se comparte entre varios procesos.
- Al restaurar se inserta una fila nueva con los mismos datos; el identificador cambia porque el anterior pudo haberse reutilizado.
- Si al restaurar hay un conflicto (por ejemplo, ya existe un material con ese nombre), se responde 409 y la entrada se conserva.
- Si el archivo adjunto de un plano ya no existe, el plano se restaura sin archivo.

## Recomendaciones automáticas

`POST /projects/{id}/recommendations/generate` revisa los terrenos y materiales con reglas fijas (`services/recommendation_rules.py`) y reemplaza las recomendaciones automáticas anteriores, sin tocar las manuales. No usa IA; se guardan con origen `system`.

Las reglas son orientativas (por ejemplo, avisar cuando la pendiente es de 15 % o más) y no sustituyen un estudio técnico. Los textos están en español porque se muestran al usuario.

Cada recomendación lleva una prioridad: `high`, `medium` o `low`. Cada regla fija la suya (una pendiente fuerte o un suelo arcilloso son de prioridad alta; un material con cantidad cero, baja) y las manuales la eligen al crearse, con `medium` por defecto. La pantalla las ordena de mayor a menor prioridad. La prioridad la validan el esquema (422) y la base de datos (`CHECK`).

## Asistente de IA

- El proveedor de IA es un modelo local servido por [Ollama](https://ollama.com), que es gratuito y no necesita clave. Se usa a través de su adaptador.
- `GET /assistant/status` dice quién responderá ahora: `ollama` (con el nombre del modelo) o `rules` si no hay IA disponible. La pestaña Asistente lo muestra en la línea «Ahora responde». Se comprueba al abrir la pestaña; si Ollama se enciende o se apaga después, la línea no cambia hasta volver a entrar, aunque cada respuesta sigue llevando su origen real.
- En cada pregunta se envían los datos del proyecto y los últimos 20 mensajes de la conversación. Los totales de costo van ya calculados, para que el modelo los cite en lugar de calcularlos.
- La pestaña ofrece cuatro preguntas sugeridas que se envían con un clic. Son texto fijo del frontend y siguen el mismo camino que una pregunta escrita. Si hay un elemento seleccionado en el modelo 3D de ese proyecto, aparece antes una quinta pregunta sobre él, con su tipo, nombre, medidas y plano escritos en el texto, porque el backend no le pasa al asistente los cuartos ni los componentes.
- Cada llamada tiene un tiempo máximo de espera: 120 segundos para la respuesta y 1 segundo para conectar con Ollama. Si se agota el tiempo, el asistente contesta con las reglas.
- La llamada real a la IA no está cubierta por pruebas automáticas: las pruebas usan un asistente simulado y un servidor de Ollama simulado, de modo que no necesitan red. Cubren también los tiempos de espera agotados.

### Privacidad

Qué sale del equipo depende de quién responde:

- **Ollama.** El modelo corre en el propio equipo: nada sale de él.
- **Reglas.** Se calculan en el backend, sin llamar a ningún servicio.

La pestaña del asistente indica en «Ahora responde» cuál de los dos está activo.

### Modelo local con Ollama

No hay que configurar nada en `.env`. Pasos, una sola vez:

1. Instalar Ollama desde https://ollama.com.
2. Descargar un modelo: `ollama pull llama3.2` (unos 2 GB). Los modelos más pequeños, como `llama3.2:1b`, se inventan cifras del proyecto.

Con Ollama encendido, el asistente lo encuentra en `http://127.0.0.1:11434` y usa el primer modelo instalado. Dos variables opcionales cambian eso: `OLLAMA_MODEL` fija el modelo y `OLLAMA_URL` la dirección.

- La velocidad y la calidad de las respuestas dependen del equipo y del modelo; un modelo pequeño responde peor que uno grande.
- Probado el 3 de octubre de 2026 con Ollama 0.35.1 y `llama3.2:1b` (1,3 GB): la conexión funciona y las respuestas quedan guardadas con origen `ai`. La primera respuesta tardó cerca de un minuto, mientras se cargaba el modelo; las siguientes, unos dos segundos. Pero ese modelo no es fiable con los datos: acertó la pendiente del terreno y se inventó el costo total de los materiales y el nombre de un plano. Con un modelo tan pequeño, las reglas dan cifras más fiables.
- Probado el mismo día con `llama3.2` (2 GB) y las mismas tres preguntas: acertó la pendiente, el costo total y el detalle de los materiales, y el plano registrado. Es el modelo recomendado; se fija con `OLLAMA_MODEL=llama3.2`. Sigue siendo un modelo pequeño y redacta con alguna imprecisión.
- Los modelos pequeños fallan al hacer cuentas: en un proyecto con ocho materiales, `llama3.2` dio bien el costo total pero señaló como más caro un material que no lo era, con una cifra mal multiplicada. Por eso el backend no le deja calcular: los datos que recibe llevan ya el costo de cada material, el total y el nombre del más caro, con los materiales ordenados de mayor a menor costo, y las instrucciones le piden citar esas cifras tal cual. Con ese cambio, la misma pregunta se respondió bien.
- Si Ollama no está encendido o no tiene modelos, el backend lo detecta en un segundo como máximo y contesta con las reglas. Después no vuelve a intentar la conexión durante 30 segundos.
- Algunos modelos escriben su razonamiento entre etiquetas `<think>`; el adaptador lo quita de la respuesta.

### Respaldo por reglas

Si el proveedor no está disponible (Ollama apagado o sin modelos), o la llamada a la IA falla (error del servicio o de red), el asistente no devuelve un error: contesta con reglas fijas (`services/assistant_rules.py`) sobre los datos del proyecto.

- Las reglas buscan palabras clave en la pregunta y reconocen tres temas: terreno (área, pendiente, desnivel, suelo), materiales y costos, y planos y elevaciones. Una pregunta puede tocar varios temas. Si no reconoce ninguno, resume el proyecto y dice sobre qué puede responder.
- Reutilizan los avisos de `services/recommendation_rules.py`, para que el asistente y las recomendaciones automáticas digan lo mismo.
- Cada mensaje del asistente guarda su origen en el campo `source`: `ai` si lo escribió la IA, `rules` si salió de las reglas. Los mensajes del usuario lo tienen vacío. La interfaz marca las respuestas por reglas con la etiqueta «Respuesta por reglas».
- No entienden el lenguaje: solo comparan palabras. Sirven para que el asistente sea útil sin IA, no para sustituirla.

## Esquemas del terreno

La pestaña Terreno dibuja cinco esquemas en SVG por cada terreno (`FRONTEND-ARQUILA/src/components/TerrainDiagrams.tsx` y `Terrain3D.tsx`), sin librerías adicionales:

- **Vista superior**: el contorno del lote a escala.
- **Curvas de nivel**: el lote visto desde arriba con una línea cada cierto desnivel y franjas más oscuras cuanto más alto está el terreno. El intervalo entre curvas se elige de una lista de valores redondos (0,1 m, 0,25 m, 0,5 m, 1 m, 2 m…) para que salgan como mucho seis. Como el terreno se modela como un plano inclinado, las curvas son rectas paralelas al frente.
- **Vista frontal**: el lote visto desde el frente, que es su lado más bajo. Conserva el ancho y convierte la profundidad de cada vértice en altura (`profundidad × pendiente / 100`), así que un lote rectangular se ve como una franja de ancho por desnivel.
- **Vista lateral**: el perfil del terreno, una línea con la pendiente real. El desnivel se calcula como `largo × pendiente / 100`.
- **Vista 3D**: el lote como una superficie inclinada según la pendiente, que se puede girar con un control. Es una proyección calculada a mano: cada vértice se rota alrededor del eje vertical y se proyecta con una inclinación fija de 30°.

La vista 3D tiene cuatro capas que se pueden mostrar u ocultar: superficie, plano base (el nivel de referencia), límites (contorno y aristas verticales) y medidas. No hay capas de construcción, vegetación ni vías, porque el proyecto no guarda esos datos.

### Lotes no rectangulares

Un terreno puede tener una lista de vértices `x y` en metros, guardados en la tabla `terrain_points` con su posición en el contorno. Si los tiene, los esquemas dibujan ese polígono; si no, usan el rectángulo de ancho por largo.

- Se aceptan entre 3 y 50 vértices, y deben encerrar un área mayor que cero.
- El área se calcula con la fórmula del área de Gauss (o «del cordón»), recorriendo los vértices una vez: O(n). Está en `app/services/geometry.py` y en `FRONTEND-ARQUILA/src/utils/geometry.ts`.
- No se comprueba que el contorno no se cruce a sí mismo.
- Al deshacer la eliminación de un terreno se recuperan sus datos, pero no sus vértices.

Simplificaciones: la superficie es un plano inclinado y se asume que la pendiente va en el sentido del largo (el eje `y`). El ancho y el largo son opcionales; si faltan, el esquema muestra qué dato falta. El área se guarda aparte porque un lote real puede no ser rectangular; el formulario la propone como ancho por largo si se deja vacía.

## Plano de implantación

La pestaña Planos dibuja, debajo de la lista de planos, un plano de implantación en SVG por cada terreno (`FRONTEND-ARQUILA/src/components/SitePlan.tsx`). Usa solo los datos del terreno:

- **Límite del terreno**: el contorno del lote a escala, con una cota en cada lado. La longitud de cada lado y hacia dónde queda el exterior se calculan recorriendo los vértices una vez: O(n) (`edges` en `FRONTEND-ARQUILA/src/utils/geometry.ts`).
- **Área edificable**: el rectángulo que queda al descontar un retiro igual en los cuatro lados. El retiro se elige con un control (de 0 a 10 m; al abrir vale 3 m, o menos si el lote es estrecho, para que siempre quede área edificable) y el plano muestra el área resultante.
- **Acceso**: una marca en el frente del lote.
- **Norte**: una flecha cuya dirección se elige con un control.
- **Leyenda** y botón **Descargar plano (SVG)**. El archivo descargado lleva sus colores dentro, así que se ve igual fuera de la aplicación.
- Botón **Imprimir o guardar como PDF**: abre la impresión del navegador con el plano solo, en una hoja A4 horizontal. Para obtener el PDF se elige «Guardar como PDF» como impresora. No usa ninguna librería.

Simplificaciones:

- El retiro y el norte no se guardan: el proyecto no tiene esos datos y vuelven a su valor inicial al recargar.
- El acceso se asume por el frente, el lado más bajo, igual que en la vista frontal del terreno.
- El área edificable solo se calcula en lotes rectangulares. En un lote con vértices se dibujan el contorno y las cotas, sin área edificable.
- No se dibujan vivienda, áreas verdes, andenes ni parqueadero, porque el proyecto no guarda esos datos.

## Cuartos

Un cuarto pertenece a un plano y se gestiona en la pestaña Modelo 3D (`FRONTEND-ARQUILA/src/components/RoomsPanel.tsx`). Las rutas siguen el mismo patrón que los planos: `POST` y `GET /projects/{id}/rooms`, y `GET`, `PATCH` y `DELETE /rooms/{id}`.

- Un cuarto es una caja: nombre, posición (`x_m`, `y_m`), ancho, largo y alto, en metros. La posición es la esquina del cuarto medida desde la esquina de origen del primer terreno del modelo.
- El plano de un cuarto debe ser del mismo proyecto; si no, se responde 404, igual que con el archivo de un plano.
- Las medidas deben ser mayores que cero. Lo validan el esquema (422) y la base de datos (`CHECK`).
- Al eliminar un plano o un proyecto se eliminan sus cuartos.

Simplificaciones:

- Los cuartos no entran en el historial de deshacer; por eso la interfaz pide confirmación antes de eliminar uno. Al deshacer la eliminación de un plano se recupera el plano, pero no sus cuartos.
- No se comprueba que un cuarto quede dentro del terreno ni que dos cuartos no se solapen.
- No hay puertas ni ventanas.

## Componentes estructurales

Las columnas, vigas y muros se gestionan en la pestaña Modelo 3D (`FRONTEND-ARQUILA/src/components/ComponentsPanel.tsx`), con las rutas `POST` y `GET /projects/{id}/components` (con filtro opcional `?kind=`) y `GET`, `PATCH` y `DELETE /components/{id}`.

- Un componente es una caja, igual que un cuarto, más un tipo (`kind`): `column`, `beam` o `wall`. Reutiliza la posición y las medidas del cuarto, así que no hay una tabla ni un formulario distinto por tipo. El formulario propone medidas habituales al elegir el tipo (columna de 0,3 × 0,3 × 3 m, viga de 4 × 0,3 × 0,4 m, muro de 4 × 0,2 × 3 m).
- El tipo lo validan el esquema (422) y la base de datos (`CHECK`).
- Valen las mismas reglas que en los cuartos: el plano debe ser del proyecto, las medidas deben ser mayores que cero y los componentes se eliminan con su plano o su proyecto.

Simplificaciones:

- Una caja solo puede ir alineada con los ejes: no hay muros ni vigas en diagonal. Un muro a lo largo de `y` se escribe con el ancho pequeño y el largo grande.
- No hay cálculo estructural (cargas, secciones, materiales): los componentes se registran y se dibujan, nada más.
- No entran en el historial de deshacer, igual que los cuartos.

## Proyectos de ejemplo

La página Proyectos ofrece cuatro ejemplos: Casa Familiar Andina, Vivienda compacta, Edificio multifamiliar y Oficina profesional. `GET /templates` los lista y `POST /templates/{id}/projects` crea un proyecto del usuario con su terreno, un plano por nivel, los cuartos de cada nivel y cuatro columnas en las esquinas de cada planta. El frontend abre el proyecto recién creado en la pestaña Modelo 3D.

- Los ejemplos están definidos en el código (`app/services/project_templates.py`), no en la base de datos: son pocos, fijos e iguales para todos los usuarios. Cada fila de cuartos se escribe con una función que los coloca uno a continuación del otro, así que no hay coordenadas repetidas a mano.
- El proyecto se crea en una sola transacción: si algo falla, no queda un proyecto a medias.
- Como el nombre de un proyecto es único por usuario, si ya existe se añade un número: «Vivienda compacta (2)».
- El proyecto creado es uno normal: se edita, se borra y se consulta igual que los demás.
- Una prueba comprueba, para cada ejemplo, que los cuartos caben en el lote y no se solapan.

Simplificaciones: solo «Vivienda compacta» trae materiales (ocho, con cantidad y costo); los demás ejemplos no. Ninguno trae elevaciones ni archivos, y las distribuciones son esquemáticas (filas de cuartos rectangulares), no planos de una obra real.

## Modelo 3D

La pestaña Modelo 3D muestra el proyecto en tres dimensiones con Three.js. Los datos salen de `GET /projects/{id}/structure` (`app/services/structure_service.py`), que arma la respuesta con los terrenos, los planos, los cuartos y los componentes estructurales del proyecto, en metros.

- **Terrenos**: cada terreno con contorno (vértices, o ancho y largo) es una losa. Los terrenos se colocan uno al lado del otro sobre el eje `x`, separados 5 m, porque cada uno guarda sus coordenadas desde su propio origen.
- **Niveles**: un plano es un nivel si tiene cuartos o componentes, o si su campo Nivel es un número (`0`, `1`, `-1`, `0.5`). Así un plano de implantación o de detalles, con el nivel vacío o con texto, no se apila como si fuera un piso. Los niveles se apilan en el orden en que se crearon los planos, no por el número. Un plano con cuartos muestra sus cuartos (`kind: "room"`). El nivel mide lo que su cuarto, columna o muro más alto, o 3 m si no tiene ninguno. Mientras el proyecto no tenga ningún cuarto ni componente, cada nivel se dibuja como un volumen de 3 m (`kind: "volume"`) sobre el área edificable del primer terreno rectangular, con el mismo retiro inicial del plano de implantación (3 m, o menos si el lote es estrecho). En cuanto hay un cuarto o un componente, los volúmenes dejan de dibujarse: un nivel vacío conserva sus 3 m de altura, pero queda en blanco, para no mezclar cuartos reales con un volumen de relleno.

- **Componentes**: las columnas y los muros se apoyan en el piso de su nivel. Una viga se cuelga del techo: su base es la altura del nivel menos el alto de la viga.

En el frontend, `FRONTEND-ARQUILA/src/three/structureViewer.ts` arma la escena y no depende de React; `StructureViewer.tsx` la crea al montar, la destruye al desmontar y dibuja encima los paneles flotantes. Tres módulos vecinos se reparten el resto: `cameraRig.ts` (controles, límites y vuelos de la cámara), `postprocessing.ts` (resplandor) y `vegetation.ts` (árboles). Decisiones del visor:

- **Dibujo bajo demanda**: la escena solo se vuelve a dibujar cuando algo cambia (la cámara, la selección, una capa, el tamaño). En reposo no gasta GPU.
- **Cámara**: cambiar de vista, hacer zoom con los botones o enfocar un elemento (doble clic o el botón «Enfocar») mueve la cámara con una transición; arrastrar la cancela, y con «reducir movimiento» activado en el sistema el cambio es inmediato. El punto que orbita la cámara no puede alejarse del modelo.
- **Resplandor**: en el modo oscuro el contorno de la selección y el borde del lote llevan un color más brillante que el blanco, y un pase de `UnrealBloomPass` hace brillar solo lo que supera ese umbral. En el modo claro el pase no se crea y se dibuja directo al lienzo.
- **Árboles**: todos comparten tres mallas instanciadas (tronco y dos copas), así que cuestan tres llamadas de dibujo sin importar cuántos haya.

- El eje `y` del plano pasa a ser `-z` en la escena. Así la altura queda en `y` y el modelo no sale reflejado.
- Las losas se generan por extrusión del contorno, que corrige el sentido de los vértices; por eso las caras quedan hacia afuera aunque el lote se haya escrito en sentido horario.
- Las sombras usan `PCFShadowMap`, que en la versión instalada de Three.js ya filtra los bordes; `PCFSoftShadowMap` se retiró de la librería y solo producía un aviso en la consola. La luz del sol lleva además `shadow.radius` para suavizar el borde.
- **Iluminación**: una luz direccional hace de sol y proyecta las sombras, una `HemisphereLight` rellena con el color del cielo y del suelo, y un mapa de entorno (`RoomEnvironment` procesado con `PMREMGenerator`) da los reflejos que necesitan el vidrio y el metal; sin él un material metálico se ve negro. En el modo oscuro se suman dos luces puntuales de acento, cian `#00F0FF` y magenta `#FF007F`, a lados opuestos del modelo; en el modo claro están apagadas (`accent` en `SCENE_PALETTES`).
- **Geometría de un cuarto**: ya no es una caja maciza. `FRONTEND-ARQUILA/src/three/roomGeometry.ts` arma cuatro muros con espesor (20 cm, o menos en cuartos pequeños) extruyendo el alzado de cada lado con un hueco por ventana o puerta, más una losa de piso y otra de techo, y los une en una sola geometría. En cada vano van un marco metálico oscuro y un vidrio translúcido (`opacity` 0,4, `roughness` 0,1, `metalness` 0,8) o la hoja de la puerta. Las líneas de arista son las doce de la caja exterior más el rectángulo de cada vano. Los volúmenes y los componentes siguen siendo cajas.
- **Relieve**: los materiales rugosos (concreto, ladrillo, revoque, piedra y, más suave, madera) llevan una textura de ruido generada por código al crear el visor (`buildGrain`, 128 × 128 px, sin archivos de imagen), que se usa como mapa de rugosidad y de relieve (`roughnessMap` y `bumpMap`). El vidrio y el acero quedan lisos. Para que el grano tenga el mismo tamaño en una columna y en un muro largo, las coordenadas de textura se reescriben en metros (`applyMetricUVs`). En los modos Tipo, Coste y Alertas el relieve se quita.
- Los planos `near` y `far` de la cámara y la cámara de sombras de la luz se ajustan al tamaño del modelo. Junto con `polygonOffset` en los materiales evita el parpadeo entre caras que coinciden (z-fighting) y las sombras recortadas.
- La cámara se encuadra solo la primera vez y con el botón «Restablecer vista». Al agregar o editar un cuarto el modelo se reconstruye, pero la cámara se queda donde el usuario la dejó.
- **Selección**: un clic sobre un cuarto lo selecciona con un rayo desde la cámara (`Raycaster`). Si el puntero se movió más de 4 px entre pulsar y soltar se considera un giro de cámara y no una selección. El elemento seleccionado no lo guarda la escena sino el estado compartido (`FRONTEND-ARQUILA/src/state/appState.ts`), así que la lista de niveles y el inspector muestran siempre lo mismo que el modelo; la lista permite además seleccionar con el teclado.
- **Materiales**: los cuartos usan `MeshPhysicalMaterial` en color ladrillo con una capa de barniz (`clearcoat`) muy suave; los volúmenes y los componentes usan `MeshStandardMaterial`, los componentes con la rugosidad alta del hormigón. El terreno es verde.
- **Material de superficie**: el inspector tiene un selector «Material» para el elemento seleccionado, con siete opciones: concreto, ladrillo, revoque, vidrio arquitectónico, acero, madera y piedra. El catálogo está en `FRONTEND-ARQUILA/src/utils/surfaceMaterials.ts`: cada material es un color, una rugosidad, un brillo metálico y una opacidad (solo el vidrio es translúcido). Un elemento sin elección usa el predeterminado de su tipo: ladrillo para un cuarto, revoque para un volumen y concreto para columnas, vigas y muros. La escena recibe el mapa de elemento a material (`setSurfaces`) y cambia las propiedades del material que ya existe, sin reconstruir el modelo.
  - La elección se guarda en el backend con `PATCH /projects/{id}/structure/{kind}/{element_id}/surface` y cuerpo `{"surface": "glass"}`; responde 204. `kind` es `room`, `volume`, `column`, `beam` o `wall`. Va en la columna `surface` (migración `008_element_surfaces.sql`) de `rooms` o de `structural_components`; la de un volumen va en `plans`, porque un volumen es un plano sin cuartos. La columna admite nulo, que significa «el predeterminado del tipo», y la respuesta de `GET /projects/{id}/structure` trae el campo `surface` en cada elemento. Responde 404 si el elemento no existe, no es de ese tipo o no es de ese proyecto, y 422 si el material o el tipo no están en la lista.
  - El visor cambia el modelo al instante y guarda después: si la petición falla, vuelve al material anterior y lo avisa en el inspector. Es `PATCH` y no `PUT` porque la configuración de CORS del backend solo admite `GET`, `POST`, `PATCH` y `DELETE`.
  - Es un dato visual: no interviene en el coste ni en la lista de Materiales del proyecto, que son partidas de presupuesto.
  - En los modos Tipo, Coste y Alertas manda el color del modo; el color y la transparencia del material solo se ven en Realista.
- **Color**: el panel «Color» ofrece cuatro modos. La escena solo recibe un mapa de elemento a color (`setColors`); los cálculos están en `FRONTEND-ARQUILA/src/utils/elementColors.ts`.
  - Realista: los colores de los materiales anteriores.
  - Tipo: un color por cuarto, volumen, columna, viga y muro.
  - Coste: una rampa de azul a rojo según el coste estimado de cada elemento, que también aparece en el inspector. Es un reparto: el costo total de los materiales del proyecto se divide entre los elementos según su volumen, porque un material no guarda a qué elemento pertenece. Los cuartos se llevan casi todo, ya que su volumen es el del espacio y no el del muro.
  - Alertas: cada elemento toma el color de la prioridad más alta entre las recomendaciones que lo mencionan por su nombre exacto (`C1` no coincide con `C10`); los demás quedan en gris. El inspector lista esas recomendaciones. Una recomendación que no nombra el elemento no se enlaza.
- **Estado compartido**: `appState.ts` es un almacén pequeño, sin librerías (`useSyncExternalStore`), que guarda del proyecto abierto sus materiales, sus recomendaciones, el elemento seleccionado, el modo de color y el material de superficie de cada elemento. El visor lo lee y lo recarga al abrirse; los paneles de Materiales y de Recomendaciones publican en él su lista cada vez que cambia; el asistente lee de él la selección. Al cambiar de proyecto se vacía, salvo el modo de color; los materiales de superficie se vuelven a leer de la respuesta de `structure`. Como las pestañas del proyecto se muestran de una en una, el cambio se ve al volver a Modelo 3D. Los demás paneles siguen cargando sus datos con `useAsync`.
- **Elementos decorativos**: para que el modelo se lea como una edificación, el visor añade ventanas, una puerta, un techo a dos aguas y árboles. No son datos del proyecto: se calculan al dibujar y no se guardan ni se pueden seleccionar. Las ventanas y la puerta son vanos reales en el muro: se ve el interior a través del vidrio.
  - Ventanas: en las caras de un cuarto que dan al exterior de su nivel (las que coinciden con el borde del rectángulo que envuelve el nivel), una cada 3 m. La puerta reemplaza la primera ventana del frente en la planta baja. La regla está en `FRONTEND-ARQUILA/src/utils/openings.ts` y la comparten las plantas y las fachadas generadas.
  - Techo: sobre el nivel más alto. Por defecto es a dos aguas, con la cumbrera a lo largo del lado mayor; el selector «Cubierta» de la barra inferior lo cambia a plana, que es una losa con un pretil de 50 cm alrededor. La elección es del proyecto: se guarda con `PATCH /projects/{id}/structure/roof` y cuerpo `{"roof": "flat"}` (responde 204; 422 si no es `gable` ni `flat`) en la columna `roof` de `projects` (migración `009_project_roof.sql`), y `GET /projects/{id}/structure` la devuelve en el campo `roof`. El visor cambia la cubierta al instante y, si no se puede guardar, vuelve a la anterior y lo avisa. Las fachadas y el corte generados leen el mismo campo y dibujan la cubierta plana como una banda.
  - Losas: cada cuarto lleva en su parte alta el canto de la losa que lo cubre, 12 cm por fuera de los muros, para que los pisos se lean desde fuera. Se oculta con los cuartos.
  - Árboles: en el fondo y en un costado de cada terreno, donde no haya cuartos ni componentes. Cada uno es un tronco cilíndrico con dos copas facetadas, y su tamaño varía según su posición.
  - Suelo y cielo: un disco de suelo alrededor del terreno recibe las sombras, y una cúpula pasa del color del horizonte al del cielo. Una niebla del mismo color que el horizonte desvanece el suelo y la cuadrícula a lo lejos, de modo que no se ve dónde terminan.
- **Cámara**: cuatro vistas (isométrica, frontal, lateral y superior), botones para acercar y alejar, el porcentaje de zoom y pantalla completa. El zoom se calcula comparando la distancia de la cámara con la distancia de encuadre.
- **Capas**: cuatro casillas muestran u ocultan cuartos, techo, árboles y cuadrícula. Al ocultar los cuartos queda a la vista la estructura; un elemento oculto tampoco se puede seleccionar con un clic.
- Al cambiar de modelo o salir de la pestaña se liberan geometrías, materiales, el mapa de sombras, los eventos y el contexto WebGL (`dispose`).
- Three.js se carga solo al abrir la pestaña (`lazy` en `ProjectDetailPage.tsx`), para no aumentar la carga inicial.
- Los paneles flotantes (vistas, niveles, inspector, color y barra inferior) usan los mismos colores que el resto de la aplicación (clases `.structure-stage` y `.hud` en `styles.css`). El cielo, la niebla, el suelo y la cuadrícula de la escena cambian con el modo claro u oscuro (`setPalette`); el elemento bajo el cursor se resalta en azul y el seleccionado lleva un contorno cian `#00F0FF` de 3 px (`LineSegments2`), en todos los modos de color y sin teñir el elemento, para que se vea su material o el color del dato. Ese contorno y las dos luces de acento del modo oscuro son el único neón de la aplicación. En pantallas estrechas los paneles pasan debajo del modelo.

Simplificaciones: la pendiente del terreno no se representa. En un lote con vértices no se dibuja el volumen de un plano sin cuartos, igual que en el plano de implantación; los cuartos sí se dibujan siempre.

## Plantas generadas y ocupación del lote

La pestaña Planos muestra, entre la lista de planos y el plano de implantación, dos paneles que se calculan en el frontend con la respuesta de `GET /projects/{id}/structure`. No guardan nada ni añaden rutas.

- **Plantas generadas** (`FRONTEND-ARQUILA/src/components/FloorPlan.tsx`): una planta en SVG por cada nivel del modelo, sobre una retícula, con los cuartos a escala, su nombre y su área. El frente del lote queda abajo, igual que en el plano de implantación. Cada planta se descarga en SVG con sus colores dentro. Lleva:
  - **Ejes**: una línea por cada borde de cuarto, con burbujas de letras (A, B, C…) arriba y de números (1, 2, 3…) a la izquierda. Los ejes salen de ordenar las coordenadas de los bordes y quitar las repetidas.
  - **Cotas**: la distancia entre cada par de ejes seguidos y, encima, la medida total. Una cota de un tramo muy corto no se escribe para que los textos no se monten.
  - **Muros**: línea gruesa en las caras exteriores y fina en las interiores.
  - **Ventanas y puerta**: las mismas del modelo 3D, con el arco de apertura de la puerta.
  - Columnas y muros estructurales en blanco, vigas en línea discontinua, peldaños en los cuartos cuyo nombre contiene «escalera», el nivel (`N+2.80`) y una escala gráfica.
- **Ocupación del lote**: huella construida, área construida, área libre, COS y CUS (`buildingIndicators` en `FRONTEND-ARQUILA/src/utils/building.ts`).
  - COS = área de la planta baja ÷ área del lote. CUS = área de todos los niveles ÷ área del lote.
  - El área del lote es la del contorno del primer terreno del modelo, calculada con la fórmula de Gauss; es el mismo terreno sobre el que se colocan los cuartos.
  - Agrupar los cuartos por nivel y sumar sus áreas es un recorrido de la lista: O(n).
  - Los máximos de COS y CUS se escriben en la pantalla, con 0,6 y 1,8 como valores iniciales, y no se guardan, igual que el retiro del plano de implantación: el proyecto no tiene la norma del municipio.

La pestaña Elevaciones añade el panel **Fachadas y corte generados** (`FRONTEND-ARQUILA/src/components/ElevationDrawing.tsx`), con cinco dibujos: fachada frontal, posterior, lateral izquierda, lateral derecha y un corte esquemático.

- Una fachada dibuja cada nivel como un rectángulo con su altura, las ventanas y la puerta de ese lado, el techo y las cotas de nivel. En las fachadas posterior e izquierda el eje horizontal se invierte, porque se miran desde el otro lado.
- El techo se ve como un triángulo cuando se mira de frente a la cumbrera y como un rectángulo cuando se mira de costado.
- El corte pasa por la mitad del ancho de la edificación y muestra, con su nombre, los cuartos que atraviesa.
- El cálculo está en `FRONTEND-ARQUILA/src/utils/elevations.ts` y devuelve una lista de rectángulos en metros; el componente solo los pasa a píxeles.

Las ventanas, la puerta y el techo se calculan en un solo lugar, `FRONTEND-ARQUILA/src/utils/openings.ts`, que usan el modelo 3D, las plantas y las fachadas. Por eso los tres dibujos coinciden: una ventana que se ve en el modelo está en el mismo sitio en la planta y en la fachada.

Simplificaciones: el área de un nivel es la suma de las áreas de sus cuartos, así que dos cuartos solapados contarían dos veces. Las plantas no dibujan mobiliario ni puertas interiores, y solo hay una puerta, la de entrada. Los ejes pasan por los bordes de los cuartos, no por las columnas. El corte no dibuja el terreno inclinado ni la cimentación. Mientras el proyecto no tiene cuartos, los volúmenes de relleno cuentan como área construida.

## Datos numéricos

La API recibe y devuelve áreas, cantidades y costos como números JSON. En la base de datos son `NUMERIC`.

## Rendimiento

Revisión hecha el 3 de octubre de 2026: se contó cuántas consultas a la base de datos hace cada endpoint con pocos datos (2 proyectos de 2 elementos) y con más (20 proyectos de 20 elementos). Si el número crece con los datos, hay una consulta repetida por cada elemento.

- Todas las listas hacen un número fijo de consultas, entre 3 y 5, sea cual sea la cantidad de datos.
- Se corrigió la lista de terrenos, que hacía una consulta más por cada terreno para traer sus vértices: con 20 terrenos pasaba de 6 a 24 consultas. Ahora trae los vértices de todos en una sola consulta y se queda en 5. Una prueba comprueba que el número no cambia al añadir terrenos.
- Se corrigió una espera en el asistente: sin Ollama encendido, cada pregunta perdía un segundo intentando conectar. Ahora, tras un intento fallido, el backend no vuelve a intentarlo durante 30 segundos y responde con las reglas de inmediato. La contrapartida es que, al encender Ollama, el asistente puede tardar hasta 30 segundos en notarlo.
- Generar recomendaciones y eliminar un proyecto sí hacen más consultas cuantos más elementos hay, porque escriben o borran una fila por elemento. Son operaciones poco frecuentes y no se cambiaron.
- El frontend compilado pesa unos 200 kB (62 kB comprimido), sin librerías de gráficos: los esquemas son SVG hechos a mano.

Las medidas se hicieron con una base SQLite en memoria; cuentan consultas, no tiempos reales contra PostgreSQL.

## Seguridad

Lo que protege cada parte está explicado en su sección: contraseñas, sesiones y límite de intentos en «Autenticación», acceso a los datos en «Permisos» y subida de archivos en «Archivos». Esta sección reúne lo que es común a toda la API y el resultado de la revisión del 4 de octubre de 2026.

### Cabeceras de respuesta

Todas las respuestas llevan estas cabeceras, que añade un middleware en `app/main.py`:

| Cabecera | Para qué |
|---|---|
| `X-Content-Type-Options: nosniff` | El navegador respeta el tipo declarado y no intenta adivinar otro. |
| `Referrer-Policy: no-referrer` | Al seguir un enlace no se envía la dirección de origen. |
| `Cache-Control: no-store` | Los datos de un usuario no quedan guardados en la caché del navegador ni de un intermediario. |
| `Content-Security-Policy: frame-ancestors` | Solo la propia aplicación (los orígenes de `CORS_ORIGINS` o `APP_URL`) puede mostrar una respuesta dentro de un marco. |

### Enlace de recuperación

El enlace de recuperación lleva su identificador en la dirección. La aplicación lo lee al abrir y lo quita de la barra de direcciones enseguida, para que no quede en el historial del navegador, y la página declara `referrer` `no-referrer` para que no viaje a otros sitios. Si se recarga la página antes de cambiar la contraseña hay que volver a abrir el enlace del correo.

### Tamaño de los datos

Todos los textos que recibe la API tienen una longitud máxima, las listas de vértices un número máximo de puntos y los archivos un tamaño máximo. La descripción de un proyecto admite hasta 2000 caracteres.

### Dependencias

Revisadas el 4 de octubre de 2026 con `npm audit` (frontend) y `pip-audit` (backend): sin vulnerabilidades conocidas. `pip-audit` señaló una en `pytest` 8, que solo se usa para las pruebas; `requirements-dev.txt` exige ahora `pytest` 9.0.3 o posterior.

### Registro de eventos

El backend escribe en la salida estándar una línea en formato JSON por cada evento (`app/logs.py`), para que se pueda filtrar o enviar a otra herramienta sin interpretar texto libre:

```json
{"time": "2026-10-04T20:54:46.650+00:00", "level": "info", "event": "request", "method": "POST", "path": "/auth/login", "status": 401, "duration_ms": 86.0}
```

| Evento | Cuándo |
|---|---|
| `request` | Cada petición atendida, con método, ruta, código de respuesta y duración. |
| `request_failed` | Una petición terminó con un error no previsto; incluye la traza. |
| `login_failed` | Inicio de sesión con credenciales incorrectas. |
| `login_blocked` | Inicio de sesión rechazado por el límite de intentos. |
| `password_rehashed` | Una contraseña antigua se volvió a guardar con Argon2id. |
| `assistant_fallback` | La IA no respondió y contestaron las reglas; incluye el motivo. |

No se registran contraseñas, correos, cookies ni los parámetros de la dirección: de cada petición solo queda la ruta. `LOG_LEVEL` fija el nivel mínimo (`INFO` por defecto). Para no duplicar líneas, `python -m app.dev` desactiva el registro de accesos propio de Uvicorn.

### Limitaciones conocidas

- El límite de intentos de inicio de sesión se cuenta por correo, no por dirección IP, y vive en memoria: se reinicia al reiniciar el servidor y no se comparte entre varios procesos.
- El registro no tiene límite de solicitudes y responde que un correo ya está registrado, así que permite averiguar si un correo tiene cuenta.
- La documentación automática de la API (`/docs`) queda accesible sin sesión. No muestra datos, solo la lista de operaciones.
- No hay un límite de archivos por proyecto, solo de tamaño por archivo.
- La aplicación no fuerza HTTPS: en un despliegue real debe ir detrás de un servidor que lo haga, con `COOKIE_SECURE=1`.

## Variables de entorno

Se pueden definir en la terminal o en el archivo `.env`, que leen `python -m app.dev`, `python -m app.migrate` y `python -m app.check`. Una variable ya definida en la terminal tiene prioridad sobre el archivo. `.env` está excluido del repositorio porque contiene contraseñas.

| Variable | Uso |
|---|---|
| `DATABASE_URL` | Conexión a la base de datos (obligatoria). |
| `UPLOAD_DIR` | Carpeta de archivos subidos (por defecto `uploads`). |
| `COOKIE_SECURE` | `1` para exigir HTTPS en la cookie de sesión. |
| `COOKIE_SAMESITE` | `lax`, `strict` o `none` (por defecto `lax`). `none` permite usar la sesión desde otro sitio y obliga a HTTPS. |
| `LOG_LEVEL` | Nivel mínimo del registro de eventos: `DEBUG`, `INFO`, `WARNING` o `ERROR` (por defecto `INFO`). |
| `OLLAMA_MODEL` | Modelo local que usa el asistente (por defecto, el primero instalado). |
| `OLLAMA_URL` | Dirección de Ollama (por defecto `http://127.0.0.1:11434`). |
| `APP_URL` | Dirección de la aplicación, para el enlace del correo de recuperación. También es el origen que CORS admite si no se define `CORS_ORIGINS`. |
| `CORS_ORIGINS` | Orígenes que pueden llamar a la API desde el navegador, separados por comas (por defecto, `APP_URL`). |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM` | Servidor de correo para la recuperación de contraseña. |

### Comprobar los servicios externos

Después de escribir la clave de IA o los datos del correo en `.env`, este comando comprueba que funcionan de verdad, sin arrancar el servidor:

```bash
python -m app.check correo@ejemplo.com
```

Hace una pregunta corta al asistente y envía un mensaje de prueba a la dirección indicada. Por cada servicio escribe `OK` o `FAILED` con el motivo (falta la variable, no se pudo conectar). Sin dirección, solo comprueba el asistente. La pregunta al asistente es una llamada real a Ollama, que no cuesta nada.

## Frontend

El menú lateral tiene ocho módulos (`MODULES` en `FRONTEND-ARQUILA/src/components/Sidebar.tsx`); la página de Inicio muestra los mismos como tarjetas, a partir de esa misma lista.

- **Terrenos** y **Materiales** reúnen los datos de todos los proyectos del usuario, con métricas y, en Materiales, el costo por categoría. Son de consulta: el botón «Abrir» lleva a la pestaña correspondiente del proyecto, donde se editan. La API no tiene una ruta que liste terrenos o materiales de todos los proyectos, así que el frontend pide la lista de proyectos y luego la de cada uno en paralelo (`loadAcrossProjects` en `services/api.ts`). Es una petición por proyecto; con muchos proyectos convendría una ruta propia en el backend.
- **Visualización 3D** y **Asistente IA** piden elegir un proyecto y muestran su modelo o su asistente, los mismos componentes de las pestañas del proyecto. Three.js sigue cargándose solo al abrir el modelo.
- **Recorrido interior** es una escena de muestra que no usa los datos de ningún proyecto: un loft de doble altura con entrepiso, escalera, la ciudad al atardecer tras el ventanal y líneas de neón. Vive en `FRONTEND-ARQUILA/src/three/interior/` (`loftScene.ts` la geometría y las luces, `cityBackdrop.ts` el cielo y la ciudad, `textures.ts` las texturas pintadas en un lienzo, `interiorCamera.ts` la cámara) y `InteriorViewer.tsx` dibuja encima la barra de título y la de controles. La geometría es procedural, hecha de cajas fusionadas por material; no hay modelos ni imágenes que descargar. La cámara no sale de las paredes ni entra en el entrepiso, en la escalera o en los muebles grandes.
- **Configuración** muestra la cuenta, permite pedir el enlace de cambio de contraseña y cerrar sesión, e informa del proveedor de IA activo y del estado de la API. No edita el nombre ni el correo ni guarda preferencias, porque la API no tiene rutas para eso.

Los mensajes de error del backend están en inglés. El frontend los traduce al español en `FRONTEND-ARQUILA/src/utils/errors.ts`; un mensaje que no esté en esa lista se muestra tal cual. Si cualquier petición responde 401, la aplicación vuelve a la pantalla de inicio de sesión.

### Estados de carga y de error

- Cada lectura de datos pasa por `useAsync` (`FRONTEND-ARQUILA/src/hooks/useAsync.ts`) y se muestra con `AsyncStatus`: «Cargando…» mientras llega la respuesta, el texto de lista vacía si no hay datos y, si falla, el mensaje de error con un botón «Reintentar» que repite la petición.
- Cada escritura (crear, editar, eliminar) bloquea su botón mientras se envía o muestra «Guardando…», y si falla deja el formulario como estaba y muestra el error. Dentro de un proyecto, una segunda acción se ignora hasta que termina la primera, para no enviar dos veces lo mismo.
- Si el cierre de sesión falla por un problema de red, la aplicación vuelve igualmente a la pantalla de inicio de sesión.

### Pantallas pequeñas

Por debajo de 720 px de ancho el menú lateral pasa a ser una fila desplazable sobre el contenido, las tablas se muestran como fichas con el nombre de cada columna junto a su valor y los controles del modelo 3D se colocan debajo del visor. Comprobado el 4 de octubre de 2026 a 390, 820 y 1280 px en todos los módulos y pestañas: ninguna vista se desborda a lo ancho.

### Accesibilidad

- Todos los campos de formulario tienen su etiqueta (`<label>`), y los botones que solo se distinguen por la fila, como «Editar» o «Eliminar», llevan `aria-label` con el nombre del elemento.
- Los colores de texto cumplen el contraste mínimo de WCAG AA (4,5:1) en el tema claro y en el oscuro. Se midió en el navegador sobre cada vista.
- Toda la aplicación se puede usar con el teclado: los controles son botones y campos nativos, el foco se ve con un contorno, hay un enlace «Saltar al contenido» al principio de la página y las ventanas usan `<dialog>`, que devuelve el foco al cerrarse. En el modelo 3D, la lista de niveles permite seleccionar cada elemento sin usar el ratón.
- Los mensajes de carga y de aviso usan `role="status"` y los de error `role="alert"`, para que un lector de pantalla los anuncie.
- Si el sistema pide reducir el movimiento, se desactivan las transiciones y el desplazamiento suave.
- No se ha probado con un lector de pantalla real.

En desarrollo, Vite reenvía las peticiones `/api/*` al backend en `localhost:8000`, por lo que la cookie de sesión funciona en el mismo origen. Si el frontend se sirve desde otro origen (`VITE_API_URL` con la dirección completa de la API), el backend lo admite por CORS solo si está en `CORS_ORIGINS`; no se usa `*` porque las peticiones llevan la cookie de sesión. Los tipos de `FRONTEND-ARQUILA/src/types/api.ts` reflejan los de `app/schemas.py` y deben mantenerse sincronizados.
