# SAIL: análisis de hardware (lectores, impresoras de tickets y de etiquetas, códigos)

> **Qué es este documento:** un análisis con propuesta, no una implementación. Explica cómo conectar
> SAIL con lectores de código de barras y QR, impresoras térmicas de tickets e impresoras de etiquetas,
> qué códigos conviene usar en una ferretería y en qué orden hacerlo. Está escrito para el dueño (en
> términos sencillos) y para el equipo (con el detalle técnico).
>
> **Base:** rama `claude/intelligent-ramanujan-l97zgv` (backend `fe28c39`, frontend `bc15bda`), el
> backlog del relevamiento (`docs/BACKLOG.md` de la rama `docs/relevamiento`: REL-01, REL-14, REL-16,
> REL-17, REL-24, REL-25, REL-29, REL-32) y el estado del proyecto (`docs/ESTADO-DEL-PROYECTO.md` de la
> rama `docs/estado-sail`). Fecha: octubre de 2026. Las fuentes web están al final (sección 10) y
> numeradas entre corchetes, por ejemplo [F3].
>
> **Precios:** son de referencia, sacados de tiendas web paraguayas en 2026. Cambian seguido y no
> siempre se distingue el precio de contado del de cuotas: hay que confirmarlos antes de comprar.

---

## 0. Resumen en una página

**La idea en una frase:** empezar con lo que funciona sin instalar nada (lector que "tipea", cámara del
celular y etiquetas imprimibles desde el navegador) y, recién después, sumar un **"agente de impresión
SAIL"** chico en cada PC de caja para imprimir directo, cortar el papel y abrir el cajón. Ese mismo
agente sirve para la versión en la nube y para la instalada en Windows.

**Recomendación:**

1. **Lectores:** usar lectores **2D USB en modo teclado (HID)**, que leen código de barras y QR.
   SAIL ya los soporta en la caja; faltan detalles: avisar cuando el código escaneado **no existe** (hoy
   puede agregar el primer resultado parecido), escanear en **recepción de compras** y en **conteos**,
   capturar el escaneo aunque el foco no esté en el buscador, y configurar el lector con el **idioma de
   teclado correcto** (si no, el guion de `PROD-00001` llega como `'`).
2. **Cámara:** para conteos y recepción con el celular, escanear con la cámara usando la API nativa
   `BarcodeDetector` donde exista (Android) y una biblioteca **ZXing en WebAssembly** donde no (iPhone,
   Windows). Es un complemento: para la caja, el lector físico es mucho más rápido.
3. **Códigos:** cada producto puede tener **varios códigos** (tabla nueva `producto_codigos`: el EAN-13
   de fábrica, el de la caja con su factor "x12", el del proveedor y uno interno). Para lo que no trae
   código, SAIL genera un **EAN-13 interno con prefijo 2x** (rango que GS1 reserva para uso interno),
   solo con números. La balanza se lee con un **parser configurable** de EAN-13 con peso o precio.
4. **Tickets, fase 1:** seguir con `window.print()`, pero con plantilla de **58 y 80 mm**, márgenes en
   cero y el **corte y el cajón configurados en el driver** de Windows (los drivers de Epson y de la
   mayoría de las marcas lo permiten). Opcional: Chrome/Edge con `--kiosk-printing` para imprimir sin
   diálogo.
5. **Tickets, fase 2:** **agente local** (servicio de Windows que escucha en `127.0.0.1`) que recibe
   el ticket y manda **ESC/POS crudo** por USB (cola de Windows en modo RAW) o por red (puerto 9100):
   impresión instantánea, corte, cajón solo en efectivo y QR nativo. **QZ Tray** queda como alternativa
   comprada si no queremos mantener un agente propio. Descarto WebUSB y Web Serial como camino
   principal (en Windows exigen cambiar el driver de la impresora).
6. **Etiquetas, fase 1:** hoja de etiquetas generada en el navegador (HTML con códigos en SVG) que se
   imprime en hojas A4 autoadhesivas o en la impresora de etiquetas instalada como impresora de Windows.
   **Fase 2:** ZPL (Zebra) o TSPL (TSC/Xprinter) crudo por el agente, para impresión masiva rápida.
7. **SIFEN (fase 3):** el KuDE en ticket de **80 mm** con el **QR obligatorio** (URL de consulta de la
   DNIT con hash SHA-256 y el CSC, Manual Técnico v150, apartado 13.8). El QR lo arma el **backend**
   (necesita el CSC, que es secreto) y la impresora solo lo dibuja.

**Qué comprar para probar (kit de demo, aprox. Gs. 4.000.000):** un lector 2D USB (por ejemplo 3nStar
SC402, ~Gs. 490.000), una térmica de 80 mm Epson TM-T20III o IV (~Gs. 1.160.000–1.370.000) y una
impresora de etiquetas Zebra ZD220/ZD230 de 4" (~Gs. 2.400.000 o US$ 340–355), más rollos de papel y de
etiquetas. Detalle en la sección 7.

**Lo que tiene que decidir el dueño** (detalle en la sección 8): tamaño y tipo de etiqueta (rollo o hoja
A4), si se usa balanza con etiqueta y de qué marca, si los códigos internos nuevos serán EAN-13
numéricos, si el cajón se abre en cada ticket o solo con efectivo, ancho de ticket (recomiendo 80 mm),
agente propio o QZ Tray para la nube, y el presupuesto del kit.

---

## 1. Qué hay hoy en SAIL (lectura del código)

| Pieza | Dónde | Qué hace hoy | Qué falta para hardware |
|---|---|---|---|
| Buscador de la caja | `assets/js/punto-venta.js` (frontend) | Input `#pdv-buscar` con foco permanente. Al recibir **Enter** cancela la búsqueda en vivo, busca ya y agrega el producto seleccionado. Comentario explícito: "el lector tipea el código y manda Enter". | Si el código **no existe exacto**, igual agrega el **primer resultado parecido** (búsqueda por partes del nombre o código). Con un EAN de fábrica que no está cargado puede entrar un producto equivocado o no pasar nada sin aviso. No hay captura del escaneo si el foco está en otro lado (por ejemplo en el campo "Paga con"). No hay cantidad por escaneo (caja x12) ni códigos de balanza. |
| Búsqueda en el backend | `catalogo_repository.py` → `buscar()` | Un **código exacto** (sin distinguir mayúsculas) devuelve solo ese producto; si no, cada palabra tiene que aparecer en nombre o código (`ILIKE`). | Un solo código por producto. No normaliza UPC-A (12 dígitos) contra EAN-13 (13 dígitos con 0 adelante). No interpreta prefijos de balanza. |
| Código del producto | `ProductoModel.codigo` (`String(50)`, único) y `CatalogoService.crear()` | Opcional al crear; si falta, se genera `PROD-00001` (`siguiente_codigo()`, a partir del id máximo). **No se puede cambiar** después. | Ese formato alfanumérico con guion no entra en EAN-13 (sí en Code128) y el guion es el carácter que más se rompe con lectores mal configurados (ver 2.1). |
| Alta de producto | `assets/js/pages/productos.js` | Campo "Código / código de barras" con placeholder "Escaneá o escribí el código". | El Enter del lector intenta enviar el formulario (lo frena la validación de "Nombre" obligatorio, pero aparece un aviso molesto). No se pueden agregar códigos extra. |
| Inventario | `assets/js/pages/inventario.js` | Filtro por código o nombre, en el navegador. | Sin modo escaneo ni conteo (REL-17). |
| Recepción de compras | `orden-compra-detalle` | Recepción manual por línea. | Sin escaneo que sume a la línea (REL-16). |
| Ticket | `assets/js/ticket.js` | Abre una ventana con HTML propio (`width: 72mm`, `@page { margin: 4mm }`, Courier) y llama a `window.print()` al cargar. Lo abre un clic del usuario para que no lo bloquee el navegador. | Ancho fijo pensado para 80 mm (en una de 58 mm, con 48 mm imprimibles, el navegador achica o corta). Sin corte ni cajón controlados. Sin QR ni código de barras. Dice "Comprobante interno — no válido como factura". |
| Hoja del reclamo | `assets/js/pages/reclamo-documento.js` + `GET /reclamos-proveedor/{id}/documento` | Página A4 en tema claro con botón Imprimir (`window.print()`). | Buen modelo para la **hoja de etiquetas A4** (misma técnica). |
| URL del backend | `assets/js/env.js` | En `localhost`/`127.0.0.1` usa `http://127.0.0.1:80NN/api/v1`; si no, el backend de Vercel. | Para la versión instalada habrá que sumar el caso "servidor local en la red de la ferretería" (IP privada) y, para la fase 2, la URL del agente local. |
| Librerías externas | `assets/vendor/` | Fluent se sirve desde `assets/vendor` (sin CDN ni build). | Las librerías nuevas (códigos de barras, escaneo con cámara) también deberían ir **copiadas en `assets/vendor`**, así funcionan en la PWA sin internet y en la versión instalada. |

**Modalidades que conviven** (según el estado del proyecto y REL-29/REL-31):

- **Nube:** frontend en Netlify (HTTPS, PWA instalable desde Chrome o Edge), backend en Vercel. El
  backend **no ve** la red de la ferretería: no puede imprimir en una impresora local.
- **Instalada en Windows:** instalador Inno Setup con Python embebido, PostgreSQL local y servicios con
  WinSW. El backend corre en una PC de la ferretería y **sí puede** hablar con impresoras de red. Pero
  si hay varias cajas, la impresora USB está en **la PC de cada caja**, no en el servidor: por eso la
  pieza que imprime tiene que vivir en cada caja (el "agente").

---

## 2. Lectores de código de barras y QR

### 2.1 Lectores USB o Bluetooth en modo teclado (HID)

**En simple:** el lector se comporta como un teclado: "tipea" el código muy rápido y aprieta Enter. No
hace falta driver ni programa: funciona en cualquier pantalla de SAIL, en la nube y en la instalada, y
también en celulares y tablets por Bluetooth.

**Tipos:**

- **1D (láser o lineal CCD):** leen solo códigos de barras de una dimensión (EAN-13, Code128). No leen QR
  ni la pantalla del celular. Ejemplo: Quanta QTLCB88N, Gs. 255.000 en Tupi [F20].
- **2D (imager):** leen 1D y también QR y DataMatrix, del papel y de pantallas. Son los que conviene comprar
  hoy: la diferencia de precio es chica y SIFEN trae QR en el KuDE. Ejemplos con precio en Paraguay:
  Quanta QTLCQ312 1D/2D cableado ~Gs. 216.000–330.000 (Cellshop, Ofimarket) [F20], Satellite A-SCAN02 2D
  inalámbrico ~Gs. 262.000 (Mega Electrónicos) [F20], 3nStar SC402 2D ~Gs. 490.000 (Nissei) [F20].

**Configuración que hay que pedir o hacer en el lector** (con los códigos de configuración del manual):

| Ajuste | Valor recomendado para SAIL | Por qué |
|---|---|---|
| Sufijo | **Enter (CR)** | Es lo que SAIL espera para "agregar". Algunos vienen con Tab o sin sufijo. |
| Prefijo | Ninguno (fase 1). Opcional en fase 2: un carácter poco usado (por ejemplo `F12` o `~`) | Un prefijo permite reconocer un escaneo aunque el foco esté en otro campo. No es imprescindible si detectamos por velocidad (ver abajo). |
| Idioma de teclado | **El mismo de Windows** (Español Latinoamérica) o, si el lector no lo trae, códigos **solo numéricos** | La mayoría de los lectores vienen emulando un teclado de EE. UU.; si Windows está en español, los símbolos salen cambiados (el `-` de `PROD-00001` llega como `'`) [F18][F19]. Los dígitos y letras no cambian. |
| Simbologías | Activar EAN-13, EAN-8, UPC-A, UPC-E, Code128, QR. Desactivar las que no se usen | Menos lecturas falsas. |
| UPC-A | Transmitir como EAN-13 (con el 0 adelante) si el lector lo permite | Así un mismo producto importado no aparece con 12 o 13 dígitos según el lector. Igual el backend debería normalizar (sección 5). |
| Velocidad entre caracteres | La de fábrica (rápida) | SAIL usa la velocidad para distinguir lector de persona. |
| Pitido y modo | Pitido corto; modo "manual" (gatillo) en caja, "presentación" opcional | |

**Qué ya funciona hoy en SAIL:** en la caja, escanear un código cargado **exacto** agrega el producto en
un paso (lo verifica la búsqueda exacta del backend). Probado en el relevamiento (`04-caja-carrito.png`).

**Qué falta (propuesta para el frontend, sin cambiar reglas de negocio):**

1. **Código no encontrado:** si el texto "parece un código" (solo dígitos de 8, 12, 13 o 14 cifras, o sin
   espacios y largo ≥ 6) y el backend no lo encuentra exacto, **no agregar el primer resultado**: mostrar
   "Código 7891234567895 no registrado" con pitido de error y la opción "asociarlo a un producto" (agrega
   el código a `producto_codigos`, con permiso). Hoy el Enter agrega `resultados[0]` aunque no sea exacto.
2. **Captura global del escaneo:** un escuchador de teclado en `document` que detecte una **ráfaga**
   (caracteres con menos de ~30–50 ms entre sí, al menos 6, terminada en Enter) cuando el foco no está
   en un campo de texto, y la mande al buscador de la caja, al campo de escaneo de la recepción o del
   conteo. Así un escaneo con el foco en "Paga con" no escribe basura. Umbrales configurables.
3. **Cantidad por escaneo:** si el código es de una caja (factor 12), sumar 12; si es de balanza, la
   cantidad sale del código (sección 5.4). Se combina con el `12*` de REL-24.
4. **Formularios:** en campos donde se escanea (alta de producto, asociar código), interceptar el Enter
   para que pase al campo siguiente en vez de enviar el formulario.
5. **Recepción de compras y conteo:** un campo "Escaneá acá" que suma 1 (o el factor) a la línea y
   muestra la última lectura en grande, con sonido de OK o error (REL-16, REL-17).
6. **GS1-128 / DataMatrix (opcional):** algunos códigos de proveedor llevan identificadores de aplicación
   (`(01)` GTIN, `(10)` lote, `(17)` vencimiento). En modo teclado el separador `FNC1`/`GS` (ASCII 29) se
   pierde o llega como otra tecla según el lector. Para una ferretería no es prioritario; si aparece,
   configurar el lector para que reemplace `GS` por un carácter visible y parsearlo en el backend.

**Bluetooth:** útil para depósito (sin cable). En modo HID se empareja como un teclado; en celulares
esconde el teclado en pantalla. Ojo con dos detalles: si se desempareja, las lecturas se pierden (los
buenos lectores tienen "modo memoria"), y la batería.

**Riesgos y cómo probarlo:** probar con el kit (sección 7) en Windows con teclado en Español
Latinoamérica: escanear `PROD-00001` (Code128) con el lector de fábrica y después de configurar el
idioma; escanear un EAN-13 cargado y uno no cargado; escanear con el foco en "Paga con".

### 2.2 Escaneo con la cámara (celular, tablet o webcam)

**En simple:** abrir una pantalla en el celular, apuntar la cámara al código y SAIL lo reconoce. Sirve
para inventario, recepción y consulta de precios sin comprar lectores para todos. Para la caja es más
lento que un lector físico (enfocar, luz, reflejos).

**Opciones técnicas:**

| Opción | Dónde funciona | Comentario |
|---|---|---|
| **`BarcodeDetector` (API nativa)** | Chrome en **Android** (desde la versión 83) y en macOS/ChromeOS; **no** en Chrome/Edge de Windows ni de Linux; Safari (Mac e iPhone) la tiene **desactivada por defecto**; Firefox no la tiene [F11][F12][F13]. | Rápida y sin descargar nada. Hay que preguntar `BarcodeDetector.getSupportedFormats()` y, si viene vacío o no existe, usar el plan B. |
| **ZXing en WebAssembly** (paquete `barcode-detector`, que imita la API nativa usando ZXing-C++ compilado a WASM) [F14] | Todos los navegadores modernos, incluido Safari en iPhone y Edge en Windows | Mismo código para todos: se usa la nativa si existe y el polyfill si no. Pesa ~1 MB (el `.wasm`), se guarda en `assets/vendor` y en la caché de la PWA. |
| `html5-qrcode` | Todos | Popular pero **sin desarrollo activo** (último release en 2023) [F15]. No la recomiendo para algo nuevo. |
| Lectores comerciales (Scanbot, Dynamsoft, STRICH) | Todos | Mejores con códigos dañados o con poca luz, pero con licencia paga. No hace falta para empezar. |

**Requisitos y detalles:**

- La cámara (`getUserMedia`) exige **HTTPS** o `localhost`. La nube (Netlify) ya es HTTPS. La **versión
  instalada** accedida desde un celular por la red local (`http://192.168.x.x`) **no tendrá cámara**
  salvo que el servidor local sirva HTTPS con un certificado confiable: es un punto a resolver en el
  instalador (REL-29) si queremos conteos con celular en la instalada.
- **iPhone:** funciona en Safari (con el polyfill). Como PWA instalada en la pantalla de inicio hay
  errores conocidos de WebKit: vuelve a pedir permiso de cámara al cambiar de página o la cámara se
  congela [F16][F17]. Mitigación: que el escáner sea **una sola página** sin cambiar de ruta mientras está
  abierta, y ofrecer "abrir en Safari" si falla. Para conteos recomiendo **Android** (más barato y sin
  esos problemas).
- **Rendimiento:** leer 5–10 cuadros por segundo de un video de 1280x720 alcanza; en celulares de gama
  baja, limitar la zona de lectura a un rectángulo central (menos píxeles) y pedir la cámara trasera
  (`facingMode: "environment"`). Linterna con `track.applyConstraints({ advanced: [{ torch: true }] })`
  donde exista (Android).
- **Uso recomendado:** **modo continuo** con pitido y vibración, una lectura cada ~1 s para el mismo
  código (que no cuente dos veces el mismo escaneo), y la lista de lo leído visible abajo. En el
  conteo, "escanear y tipear cantidad" es más rápido que escanear 40 tornillos uno por uno.
- **Webcam de PC:** sirve como emergencia, pero las webcams no enfocan de cerca y los EAN-13 chicos
  fallan; QR grandes sí.

---

## 3. Impresoras de tickets térmicas (58 y 80 mm)

### 3.1 Qué impresoras hay en Paraguay

- **Ancho:** 80 mm (72 mm imprimibles, 576 puntos a 203 ppp) o 58 mm (48 mm imprimibles, 384 puntos).
  Para **factura electrónica conviene 80 mm**: el KuDE lleva datos del emisor, totales por tasa de IVA, el
  CDC de 44 dígitos y el QR [F5].
- **Lenguaje:** casi todas hablan **ESC/POS** (el estándar de facto que definió Epson) [F23]. Las
  económicas (Xprinter, ZKTeco, TypStar, 3nStar, genéricas) lo emulan con diferencias menores.
- **Conexión:** USB (la más común), USB + Ethernet (útil para red y puerto 9100), Serial, Bluetooth
  (portátiles). El cajón de dinero se conecta a la impresora con cable **RJ11** y la impresora lo abre con
  un pulso (comando `ESC p`).
- **Precios de referencia en Paraguay (2026):**
  - Epson TM-T20III USB: Gs. 1.170.000 (Nissei), Gs. 1.175.000 (Shopping China), Gs. 1.370.000 contado
    (Tecnoga) [F21]. Epson TM-T20IV-L USB: Gs. 1.161.000 (Nissei) [F22].
  - 3nStar RPT015 USB/LAN: Gs. 1.214.000 (Nissei) [F22].
  - TypStar TYP-80E USB: Gs. 847.000 (Ofimarket); ZKTeco ZKP8003 (ESC/POS): Gs. 680.000
    (Storeinformatica) [F22].
  - Bematech, Xprinter y otras: hay en el mercado, no encontré precio publicado en guaraníes.

### 3.2 Imprimir desde el navegador con `window.print()` (lo que hace SAIL hoy)

**En simple:** SAIL arma el ticket como una página web chiquita y le pide al navegador que la imprima en
la impresora de Windows. Funciona con cualquier impresora que tenga driver, sin instalar nada más.

**Limitaciones y cómo mitigarlas:**

| Limitación | Detalle | Mitigación en fase 1 |
|---|---|---|
| **Diálogo de impresión** | Chrome/Edge muestran la vista previa cada vez. | Atajo de Chrome/Edge con `--kiosk-printing` (imprime directo en la impresora predeterminada) [F25]; en la versión instalada, el instalador puede crear ese acceso directo. El dueño elige la térmica como **impresora predeterminada** de la PC de caja. |
| **Márgenes y escala** | El navegador agrega márgenes, encabezado (fecha, URL) y puede achicar. | CSS `@page { size: 80mm auto; margin: 0 }` (o 58 mm), `body { width: 72mm }` (48 mm en 58) y en el diálogo: Márgenes "Ninguno", Escala 100 %, sin encabezados. Chrome recuerda la elección [F26]. |
| **Largo del papel** | El driver define un largo de página (por ejemplo "Roll Paper 80 x 297 mm"). Si el ticket es más largo, se parte en "páginas"; si es más corto, algunos drivers avanzan papel en blanco. | Elegir en el driver un tamaño de rollo largo (muchos drivers traen "80 x 3276 mm" o "longitud según documento") [F26]. Probarlo con cada marca. |
| **Corte del papel** | `window.print()` no puede mandar el comando de corte. | El driver corta al **final del documento** (opción del driver de Epson y de la mayoría de las marcas). |
| **Cajón** | `window.print()` no puede abrir el cajón. | El driver de Epson (APD) y otros permiten **"abrir el cajón al imprimir"** (al inicio o al final del documento) [F24]. Contra: se abre en **cada** impresión, incluidas reimpresiones y pagos con tarjeta. |
| **Calidad del texto** | El navegador manda una **imagen** (raster); en impresoras lentas o por Bluetooth tarda. | Fuente sin serif y en negrita para totales; evitar grises (salen punteados). |
| **Ventanas emergentes** | `window.open` puede quedar bloqueado. | SAIL ya lo abre desde un clic. Alternativa: imprimir desde un `<iframe>` oculto. |
| **58 mm** | La plantilla actual es de 72 mm de ancho. | Preferencia por PC de caja: "Ancho del ticket: 58 / 80 mm / A4" (en `localStorage` como conveniencia, o por caja cuando exista REL-09). |

**QR y código de barras con `window.print()`:** se dibujan en el navegador como **SVG** (nítidos a
cualquier tamaño) con una librería JavaScript (sección 4.3). Funciona bien: la impresora recibe una
imagen. Para un QR legible en 203 ppp hay que asegurar que cada "cuadradito" (módulo) mida un número
entero de puntos (por ejemplo 3 o 4 puntos = 0,375 o 0,5 mm).

### 3.3 Imprimir ESC/POS "crudo" (impresión directa)

**En simple:** en vez de mandar una imagen por el driver, SAIL le habla a la impresora en su propio
idioma (comandos ESC/POS). Es instantáneo, corta el papel cuando queremos, abre el cajón solo si se cobró
en efectivo e imprime el QR con el generador interno de la impresora.

**Comandos que usaríamos** (referencia de Epson [F23]):

| Qué | Comando ESC/POS |
|---|---|
| Inicializar | `ESC @` (`1B 40`) |
| Alinear, negrita, tamaño doble | `ESC a n`, `ESC E n`, `GS ! n` |
| Página de códigos (acentos, ñ) | `ESC t n` (por ejemplo PC850 o WPC1252, según el modelo) |
| Código de barras (EAN-13, Code128) | `GS h` (alto), `GS w` (ancho), `GS H` (texto), `GS k m n datos` |
| **QR** | `GS ( k`: función 165 (modelo 2), 167 (tamaño del módulo), 169 (corrección de errores L/M/Q/H), 180 (guardar datos), 181 (imprimir) |
| Imagen (logo, o QR como imagen si la impresora no tiene QR nativo) | `GS v 0` (raster) |
| Abrir cajón | `ESC p 0 25 250` (pulso al pin 2; el pin 5 es el segundo cajón) |
| Avanzar y cortar | `GS V 66 n` (corte parcial con avance) |

**Cómo hacer llegar esos bytes a la impresora (opciones):**

| Opción | Cómo funciona | Nube | Instalada | Veredicto |
|---|---|---|---|---|
| **WebUSB** | El navegador habla directo con el USB de la impresora. Solo Chrome/Edge. | Sí (HTTPS) | Sí | **No recomendado:** en Windows hay que **reemplazar el driver** de la impresora por WinUSB (con Zadig) y entonces Windows deja de verla como impresora [F27]. Imposible de pedirle eso a un cliente. |
| **Web Serial** | El navegador habla con un puerto COM. Solo Chrome/Edge de escritorio. | Sí | Sí | Solo sirve para impresoras **seriales** o con driver de "COM virtual". Útil como plan B puntual, no como estándar. |
| **Impresión por red (puerto 9100)** | Se abre un socket TCP a la IP de la impresora y se mandan los bytes. | **No** desde el navegador (los navegadores no abren sockets TCP) ni desde Vercel (no ve la red local). | **Sí, desde el backend local** | Muy simple y robusto **si la impresora tiene red**. En la nube hace falta el agente. |
| **QZ Tray** | Programa de escritorio (Java) que escucha en `wss://localhost:8181`; la página le manda trabajos RAW (ESC/POS, ZPL) o PDF por JavaScript. Windows, Mac y Linux [F28]. | Sí | Sí | Funciona y es conocido. La versión libre muestra **avisos de confianza** en cada conexión; para imprimir sin avisos hay que firmar con un certificado de la licencia paga: **Premium Support US$ 599** (renovaciones más baratas) [F29]. Producto de un tercero. |
| **Agente local propio "SAIL Impresión"** | Servicio chico de Windows (Python, el mismo que embebe el instalador) que escucha en `http://127.0.0.1:<puerto>` y manda RAW a la cola de Windows (`win32print`, tipo de datos RAW) o por TCP 9100. La librería `python-escpos` ya trae los "printers" `Win32Raw`, `Network`, `Serial` y `Usb` y genera QR nativo [F30]. | Sí (con permiso de "red local", ver abajo) | Sí | **Recomendado para la fase 2.** Es nuestro, sin licencias, lo instala el mismo instalador y sirve también para etiquetas (ZPL/TSPL) y, a futuro, para la balanza por puerto serie. |
| SDK del fabricante (Epson ePOS SDK para JavaScript) | La página manda XML/HTTP a la IP de impresoras Epson compatibles. | Sí | Sí | Atado a ciertos modelos de Epson. No como estándar. |

**Atención con Chrome 142+ ("Local Network Access"):** desde Chrome/Edge 142 (fines de 2025), cuando una
página pública (por ejemplo SAIL en Netlify) llama a `127.0.0.1` o a una IP privada, el navegador **pide
permiso** al usuario una vez; si lo niega, la llamada falla [F31]. Afecta por igual a QZ Tray y a un
agente propio. Mitigación: pedir el permiso en la configuración inicial de la caja ("Conectar impresora")
y, en empresas con políticas, preaprobarlo con las directivas `LocalNetworkAccessAllowedForUrls` /
`LoopbackNetworkAllowedForUrls` [F32]; el instalador de Windows puede dejarlas puestas para el origen de
SAIL. Desde una página `https` llamar a `http://127.0.0.1` está permitido en Chrome y Edge (tratan el
"loopback" como origen seguro), así que el agente no necesita certificado propio; en Windows son los
navegadores que vamos a soportar para la caja.

### 3.4 QR y código de barras en el ticket

- **Código de barras del número de venta (Code128):** permite **escanear el ticket** para buscar la venta
  en devoluciones (REL-05) y reimpresiones. Barato y muy útil.
- **QR del KuDE (SIFEN):** obligatorio en la factura electrónica (sección 6, fase 3).
- **QR de pago:** con el estándar de QR interoperable del BCP (EMV QRCPS, obligatorio para los
  proveedores de pago desde el 30/06/2025) y la plataforma central "QR Hub" del SPI [F33], el QR
  **dinámico** con el monto lo genera el proveedor de pago (Bancard, billeteras) por su API; SAIL solo
  tendría que **mostrarlo en pantalla o imprimirlo**. Es parte de REL-32 (P3). Técnicamente es otro QR en
  el ticket o en una segunda pantalla.

### 3.5 Recomendación para tickets

| | Nube (navegador) | Instalada (Windows) |
|---|---|---|
| **Fase 1** | `window.print()` con plantilla 58/80 mm, márgenes 0, corte y cajón por driver, acceso directo con `--kiosk-printing` opcional. QR y barras en SVG. | Igual; el instalador crea el acceso directo de Edge/Chrome con `--kiosk-printing --app=<url>` y deja la térmica como predeterminada. |
| **Fase 2** | **Agente SAIL** en cada PC de caja (o QZ Tray si el dueño prefiere comprar). Fallback automático a `window.print()` si el agente no responde. | **Agente SAIL** incluido en el instalador. Si la impresora es de red y está en la misma LAN que el servidor, el **backend local** puede imprimir directo por 9100 sin agente. |

---

## 4. Impresoras de etiquetas

### 4.1 Tipos y lenguajes

| Familia | Lenguaje | Comentario | Referencia en Paraguay |
|---|---|---|---|
| **Zebra** (ZD220, ZD230, ZD421) | **ZPL** (el más difundido) | El estándar de la industria; muchos programas de etiquetas lo hablan. Driver "ZDesigner" que permite RAW y gráfico [F28]. | ZD220D 4" Gs. 2.393.000 (Shopping China, agotada) [F34]; ZD421 desde US$ 340 y ZD230T desde US$ 355 (comparador Compras Paraguai) [F34]; AGP Etiquetas vende la ZD220T y rollos [F34]. |
| **TSC** (TE200, TE210) | **TSPL** | Buena relación precio/calidad. Algunos modelos emulan ZPL. | Sin precio publicado encontrado. |
| **Xprinter de etiquetas** (XP-420B, XP-470B, XP-365B) | **TSPL** (algunas también ESC/POS) | Muy baratas (US$ 45–70 afuera) [F35]. Calidad y drivers variables. | Sin precio en Gs. encontrado. |
| **3nStar LDT114**, **TypStar TYP-9210**, **Fastrax TDE010U** | Varían (TSPL/EPL/ZPL según modelo) | Marcas que se ven en tiendas paraguayas (Ditech, Ofimarket, Fastrax) [F36]. | Sin precio visible. |
| **Brother QL** (QL-800, QL-810W) | Raster propio (no ZPL) | Muy fácil de usar como impresora de Windows; rollos DK de hasta 62 mm. Ideal para fase 1, no para RAW. | QL-800 Gs. 1.150.000 (Ofimarket) [F36]. |

**Térmica directa vs transferencia térmica:** la **térmica directa** (sin cinta) es más barata y alcanza
para etiquetas de precio que se cambian seguido; se borra con sol y calor. La **transferencia térmica**
(con ribbon) dura años: conviene para etiquetas de producto que quedan pegadas (herramientas en
exhibición). Para góndola, térmica directa.

### 4.2 Etiquetas que usaría una ferretería

| Etiqueta | Tamaño típico | Contenido |
|---|---|---|
| **Producto (pegada al artículo o bolsita)** | **50 x 25 mm** (la más común en rollos), 40 x 30 mm, 38 x 25 mm | Nombre corto (2 líneas), **código de barras** (EAN-13 o interno), precio en Gs. grande, código interno chico. |
| **Góndola / estante** | **70–100 x 30–40 mm** o tira de 100 x 30 mm | Nombre, precio grande, unidad ("por metro", "por kg"), código de barras o QR, fecha de actualización del precio. |
| **Caja / bulto (depósito)** | 100 x 50 mm o 100 x 150 mm | Producto, cantidad por caja, código de la caja (factor), ubicación. |
| **Hoja A4 autoadhesiva** (sin impresora de etiquetas) | Planchas de 65, 40, 24 o 21 etiquetas por hoja | Lo mismo que la de producto, impreso en la láser o chorro de tinta de la oficina. |

**Tamaño mínimo del código:** un EAN-13 al 100 % mide 37,3 x 25,9 mm; se puede achicar hasta ~80 % en
etiquetas de 50 x 25 mm (con 203 ppp, usar un ancho de barra fino de 2 puntos = 0,25 mm). Para códigos
internos largos, Code128 ocupa más ancho que EAN-13: otra razón para usar EAN-13 numérico (sección 5).

### 4.3 Cómo generar los códigos

**Dígito verificador EAN-13** (el que agregaría el backend al generar códigos internos y el que validaría
al cargar un código de fábrica): sumar los 12 primeros dígitos con pesos alternados 1 y 3 empezando por la
izquierda; el dígito es `(10 - (suma % 10)) % 10`.

```python
def digito_ean13(doce: str) -> int:
    suma = sum(int(d) * (3 if i % 2 else 1) for i, d in enumerate(doce))
    return (10 - suma % 10) % 10
# "200000000001" → 2000000000015 ... (el mismo algoritmo vale para EAN-8, UPC-A y GTIN-14 alineando a la derecha)
```

Code128 tiene su propio verificador (módulo 103) que **calcula la librería o la impresora**: no se guarda.

**Dónde dibujar el código:**

| Dónde | Herramienta | Uso |
|---|---|---|
| **Navegador (recomendado para fase 1)** | **bwip-js** (más de 100 simbologías, incluye EAN-13, Code128, QR y DataMatrix; salida SVG o canvas) [F37]. Alternativas: JsBarcode (solo 1D) + una librería de QR. | Hoja de etiquetas HTML, ticket con `window.print()`. Se copia en `assets/vendor`. |
| **Backend (Python)** | `python-barcode` (EAN-13/Code128 en SVG/PNG), `segno` o `qrcode` (QR en SVG/PNG). | PDF del KuDE, etiquetas en PDF si algún día se generan en el servidor, mails/WhatsApp con el KuDE. |
| **La impresora** | ZPL `^BE` (EAN-13), `^BC` (Code128), `^BQ` (QR) [F38]; TSPL `BARCODE` y `QRCODE`; ESC/POS `GS k` y `GS ( k`. | Fase 2: se manda texto y la impresora dibuja el código nítido y rápido. |

**Ejemplo de etiqueta 50 x 25 mm en ZPL (203 ppp: 8 puntos por mm):**

```
^XA
^PW400^LL200
^CF0,22^FO15,10^FB370,2,0,L^FDTornillo autorroscante 8 x 1" (x100)^FS
^FO15,60^BY2^BEN,60,Y,N^FD200000000001^FS
^CF0,40^FO15,150^FB370,1,0,R^FDGs. 25.000^FS
^XZ
```

(`^BE` calcula el dígito verificador; `^FB` corta el nombre en 2 líneas y alinea el precio a la derecha. El equivalente en TSPL usa
`SIZE 50 mm,25 mm`, `TEXT`, `BARCODE ... "EAN13"` y `PRINT 1`.)

### 4.4 Impresión masiva al recibir mercadería

Flujo propuesto:

1. Al **recibir una orden de compra** (o al cambiar precios en lote, REL-04), SAIL arma una **cola de
   etiquetas pendientes**: un renglón por producto con la cantidad sugerida (= unidades recibidas para
   etiqueta de producto, 1 para góndola).
2. Pantalla "Etiquetas" (Inventario → Etiquetas): filtrar por OC, por categoría o "precio cambiado desde
   la última etiqueta"; ajustar cantidades; elegir plantilla (producto 50x25, góndola, hoja A4).
3. **Imprimir:** fase 1 abre una página imprimible (igual que la hoja del reclamo) con todas las
   etiquetas; fase 2 manda un solo trabajo ZPL/TSPL al agente (cientos de etiquetas en segundos, con
   `^PQ` para copias).
4. Marcar como impresas (fecha y precio impreso), así sabemos qué góndolas tienen precio viejo.

---

## 5. Qué códigos usar en una ferretería (y cambios de modelo propuestos)

### 5.1 Reglas simples

1. **Si el producto trae EAN-13 (o UPC) del fabricante, se usa ese.** Es lo más común en herramientas,
   pinturas, adhesivos, eléctricos. No hace falta afiliarse a GS1 para revender: GS1 Paraguay (prefijo
   **784**) asigna códigos a quien **fabrica o fracciona y vende a terceros** (supermercados,
   distribuidores, exportación) [F39][F40].
2. **Si no trae código** (bulonería suelta, cables por metro, productos fraccionados en bolsitas,
   artículos importados sin código), **SAIL genera un EAN-13 interno** con prefijo del rango **20–29**,
   que GS1 reserva para uso interno de la tienda (números de circulación restringida, RCN); no se usa
   fuera del negocio [F41][F42]. Solo números: imprime compacto y no se rompe con la configuración de
   teclado del lector.
3. **Separar rangos** para no chocar con la balanza: por ejemplo **`29` + 10 dígitos de secuencia + dígito
   verificador** para productos internos y **`20`–`28`** reservados para balanza (configurable).
4. Los códigos actuales `PROD-00001` **siguen funcionando** (se migran como código "interno anterior"); a
   los productos que no tengan EAN se les puede generar uno nuevo con un clic y reimprimir la etiqueta.
5. **Varios códigos por producto:** el EAN de la unidad, el **DUN-14/ITF-14 o EAN de la caja** (con
   factor: escanear la caja suma 12 unidades), el código que usa el proveedor en sus facturas y el interno.
6. **QR con datos:** no para vender (el EAN-13 es más rápido de leer), sino para **etiquetas de góndola**
   con un enlace a la ficha (`https://<sail>/p/<codigo>`) para consultar stock o precio con el celular, y
   para etiquetas de **ubicación** del depósito ("Estante A-3") en los conteos (REL-17).

### 5.2 Propuesta de modelo (no implementada)

**Tabla nueva `producto_codigos`** (migración Alembic nueva; no se renombra ni se borra `productos.codigo`):

| Columna | Tipo | Comentario |
|---|---|---|
| `id` | serial PK | |
| `producto_id` | FK `productos.id` (`ON DELETE CASCADE`) | |
| `codigo` | `String(64)`, **único**, indexado | Normalizado: sin espacios; los GTIN se guardan como **GTIN-13** (UPC-A con un 0 adelante) o GTIN-14. |
| `tipo` | enum `EAN13`, `EAN8`, `UPCA`, `GTIN14`, `INTERNO`, `INTERNO_ANTERIOR`, `PROVEEDOR`, `OTRO` | Se deduce al cargar (largo + dígito verificador válido) y se puede corregir. |
| `factor` | `Numeric(14,3)`, default 1 | Unidades del producto que suma un escaneo (caja x12 → 12). Se alinea con REL-14 (unidades y fraccionamiento). |
| `descripcion` | `String(80)` nullable | "Caja x12", "Blíster x2", "Código del proveedor X". |
| `proveedor_id` | FK nullable | Para códigos que solo usa un proveedor. |
| `principal` | bool | El que se imprime en la etiqueta (uno por producto). |
| `activo` | bool | Un código dado de baja no se borra (historial). |
| `created_at` | timestamp | |

**Otros cambios:**

- `productos.codigo` queda como **código interno/SKU** que no cambia (lo usan reportes y referencias);
  la búsqueda por escaneo usa `producto_codigos`. Migración de datos: por cada producto, insertar su
  `codigo` actual en `producto_codigos` (tipo `EAN13`/`EAN8`/`UPCA` si es numérico con dígito válido, si
  no `INTERNO_ANTERIOR`), `principal = true`.
- **Secuencia** para códigos internos (`codigo_interno_seq`) en vez del "id máximo + 1" (evita repetidos
  con operaciones simultáneas).
- **Configuración de balanza** en `empresa` (o tabla `config_balanza`): prefijos (por ejemplo `20,21`),
  largo del PLU (4 o 5), tipo de valor (`PESO` en gramos o `PRECIO` en Gs.), largo y decimales del valor.
  En los productos pesables, el **PLU** se guarda como un código más (tipo `PLU`) o columna
  `productos.plu_balanza` única.
- **Endpoint de escaneo** `GET /productos/escaneo?codigo=...` que devuelve `{producto, cantidad,
  precio_unitario?, origen}`: 1) busca exacto en `producto_codigos` (y en `productos.codigo` mientras dure
  la transición); 2) si es numérico de 12 dígitos prueba con 0 adelante (UPC-A → EAN-13); 3) si empieza
  con un prefijo de balanza, separa PLU y valor; 4) si no, **404 "código no registrado"** (nunca un
  parecido). La búsqueda de texto actual (`/productos/buscar`) sigue para tipear nombres.
- **Etiquetas:** `etiquetas_pendientes` (producto, cantidad, plantilla, origen OC/precio, impresa_en,
  precio_impreso) o, más simple al principio, un campo `productos.precio_etiqueta` para detectar precios
  desactualizados.
- **Validación:** al cargar un EAN, verificar el dígito verificador y avisar si es inválido (error de
  tipeo); no permitir códigos repetidos entre productos (`409`).

### 5.3 Dónde se usa cada código

| Pantalla | Qué hace con el escaneo |
|---|---|
| Caja | Agrega el producto con la cantidad del factor o de la balanza. Código desconocido → aviso, nunca un parecido. |
| Alta/edición de producto | Agregar, quitar y marcar principal; "Generar código interno". |
| Recepción de OC | Suma a la línea de la orden; si el producto no está en la OC, pregunta; código desconocido → "asociar a producto". |
| Conteo (REL-17) | Suma al conteo; con cantidad tipeable. |
| Etiquetas | Escanear para agregar a la cola de impresión. |
| Devoluciones (REL-05) | Escanear el código de barras del ticket para traer la venta. |

### 5.4 Códigos de balanza (EAN-13 con prefijo 2)

**En simple:** la balanza con impresora pesa los clavos, imprime una etiqueta con un código y la caja lo
lee: SAIL sabe qué producto es y cuánto pesó (o cuánto cuesta).

Formatos más comunes (varían por marca y configuración; hay que confirmarlo con la balanza real) [F43][F44]:

```
Peso:   2 0 | P P P P P | W W W W W | C     → prefijo 20, PLU 5 dígitos, peso en gramos (01250 = 1,250 kg)
Precio: 2 | P P P P P | $ $ $ $ $ $ | C     → prefijo 2, PLU 5 dígitos, precio de 6 dígitos (hasta Gs. 999.999)
```

**Detalle importante para Paraguay:** el formato clásico con **precio de 5 dígitos** solo llega a
**Gs. 99.999**: un paquete de clavos de Gs. 120.000 no entra. Por eso recomiendo **código con peso** (SAIL
calcula el precio con su lista, que además respeta descuentos y listas por cliente de REL-07) o, si la
balanza solo hace precio, un formato de **6 dígitos de precio**. El dígito de "control del precio" que
usan algunas balanzas dentro del código también se puede configurar.

---

## 6. Arquitectura propuesta por fases

```
                    NUBE                                          INSTALADA (Windows)
 ┌────────────────────────────────────────┐        ┌──────────────────────────────────────────┐
 │ Navegador / PWA (Netlify, HTTPS)       │        │ Navegador / PWA (servidor local)          │
 │  - lector HID → buscador               │        │  - lector HID → buscador                  │
 │  - cámara (BarcodeDetector / ZXing)    │        │  - cámara (requiere HTTPS en la LAN)      │
 │  - ticket y etiquetas: window.print()  │ F1     │  - ticket y etiquetas: window.print()     │
 │  - fase 2: fetch → 127.0.0.1:<agente>  │ F2     │  - fase 2: fetch → 127.0.0.1:<agente>     │
 └──────────────┬─────────────────────────┘        └───────────┬──────────────────────────────┘
                │ API (HTTPS)                                  │ API (LAN)
        Backend FastAPI (Vercel)                       Backend FastAPI (PC servidor)
        - códigos, escaneo, etiquetas                  - lo mismo + impresión por red 9100 (opcional)
        - SIFEN: XML firmado, CDC, URL del QR          - SIFEN: igual
                                                       
 Agente SAIL (fase 2, en cada PC de caja): servicio de Windows en 127.0.0.1
   → cola de Windows en RAW (USB) · TCP 9100 (red) · COM (serie)  → térmica, etiquetas, cajón
```

### Fase 1: funciona sin instalar nada

**Objetivo:** escanear en todos lados, etiquetas imprimibles y ticket bien formateado, solo con el
navegador y los drivers de Windows.

- **Backend:**
  - Tabla `producto_codigos` + migración de datos + endpoints CRUD de códigos del producto.
  - Endpoint de escaneo (`/productos/escaneo`) con normalización UPC/EAN, factor, balanza configurable y
    404 explícito.
  - Generador de EAN-13 interno con secuencia y dígito verificador; validación de dígito al cargar.
  - Endpoint de etiquetas: datos para imprimir (nombre corto, precio, código principal) por lista de
    productos o por OC recibida; cola `etiquetas_pendientes` (o detección por precio cambiado).
  - Tests: dígito verificador (casos conocidos), normalización, parser de balanza (peso/precio, prefijos),
    unicidad de códigos, escaneo de código desconocido → 404.
- **Frontend:**
  - Caja: "código no registrado" en vez de agregar un parecido; captura global de ráfagas del lector;
    cantidad por factor/balanza; sonido OK/error.
  - Recepción de OC y conteo: campo de escaneo con suma y sonido (REL-16, REL-17).
  - Productos: lista de códigos del producto, "Generar código", Enter del lector no envía el formulario.
  - Escáner con cámara (componente reutilizable `componentes/escaner.js`): `BarcodeDetector` +
    polyfill ZXing-WASM en `assets/vendor`, cámara trasera, modo continuo.
  - Etiquetas: página imprimible (como `reclamo-documento`) con plantillas 50x25, góndola y A4; códigos con
    bwip-js en SVG.
  - Ticket: plantillas 58/80 mm, `@page` con márgenes 0, Code128 del número de venta.
- **Hardware a probar:** lector 2D USB (y uno Bluetooth si se puede), térmica 80 mm con driver,
  impresora de etiquetas instalada como impresora de Windows, hojas A4 autoadhesivas. Celular Android para
  la cámara.
- **Costos aproximados:** lector 2D Gs. 220.000–490.000; térmica 80 mm Gs. 680.000–1.370.000; etiquetas
  Brother QL-800 Gs. 1.150.000 o Zebra ZD220 ~Gs. 2.400.000; hojas A4 de etiquetas (planchas de 65)
  económicas en librerías.
- **Riesgos:** idioma de teclado del lector; drivers de térmicas genéricas que no cortan o dejan papel en
  blanco; la impresora de etiquetas imprime "corrido" si el tamaño de etiqueta del driver no coincide
  (hay que calibrar el sensor de gap); cámara en iPhone como PWA; cámara en la instalada sin HTTPS.
- **Cómo probarlo:** pruebas automáticas del backend; en el navegador (Playwright) que la hoja de
  etiquetas y el ticket generen el SVG del código y el `@page` correcto; con el kit: imprimir 50 etiquetas
  y **escanearlas todas** con el lector y con el celular (lectura al primer intento ≥ 98 %); ticket en 58 y
  80 mm sin cortes; escanear códigos con y sin configurar el idioma del lector.

### Fase 2: impresión directa, corte y cajón

**Objetivo:** ticket instantáneo sin diálogo, corte, cajón solo con efectivo, etiquetas masivas rápidas.

- **Agente SAIL de impresión** (pieza nueva, la arma el líder de Backend con el del instalador):
  - Servicio de Windows (Python embebido, WinSW, igual que el backend instalado) que escucha **solo en
    `127.0.0.1`**. API mínima: `GET /estado` (versión, impresoras de Windows), `POST /imprimir` (`{impresora,
    tipo: "escpos"|"zpl"|"tspl"|"pdf", datos}`), `POST /cajon`.
  - Envía RAW con `win32print` (cola de Windows con tipo de datos RAW: no hay que tocar drivers) o por
    TCP 9100; `python-escpos` para armar ESC/POS (texto, QR nativo, corte, cajón) [F30].
  - Seguridad: CORS solo para los orígenes de SAIL; **token de emparejamiento** (lo genera el agente, se
    pega una vez en "Configuración → Impresoras" de esa PC) para que otra página web no pueda imprimir ni
    abrir el cajón; límites de tamaño.
  - Permiso de "red local" de Chrome 142+: se pide una vez; el instalador puede preaprobarlo por directiva.
- **QZ Tray** como alternativa sin desarrollo propio (licencia ~US$ 599 para impresión silenciosa) [F29].
- **Backend:** plantillas ESC/POS y ZPL/TSPL generadas en el servidor (texto y bytes, testeables) o en el
  frontend (más simple: el frontend ya tiene los datos). Recomiendo **en el frontend para el ticket** (no
  depende de la red) y **en el backend para etiquetas masivas** (plantillas versionadas, una sola fuente).
  En la instalada, opción "impresora de red" que imprime desde el backend por 9100.
- **Frontend:** "Configuración → Impresoras" por PC (agente detectado sí/no, impresora de tickets, de
  etiquetas, ancho, abrir cajón: siempre / solo efectivo / nunca, imprimir ticket: siempre / preguntar /
  nunca, REL-24); botón "Abrir cajón" con permiso; **fallback automático** a `window.print()` si el agente no
  responde.
- **Hardware:** la térmica del kit con el cajón RJ11 (cajón de referencia ~US$ 40–60; no encontré precio
  en Gs.); idealmente una térmica con Ethernet (3nStar RPT015 USB/LAN, Gs. 1.214.000) para probar 9100.
- **Riesgos:** soporte de antivirus/Windows Defender para un servicio que escucha en un puerto; páginas de
  códigos y acentos distintos por marca (probar `ñ`, `á`, `Gs.`); térmicas genéricas que no soportan
  `GS ( k` (QR) → imprimir el QR como imagen `GS v 0`; mantenimiento del agente (actualizaciones).
- **Cómo probarlo:** pruebas unitarias del armado de bytes (comparar con secuencias esperadas); emulador
  de ZPL (Labelary) para ver la etiqueta sin imprimir [F38]; impresora "virtual" que guarda a archivo el
  RAW; con el kit: 100 tickets seguidos, corte y cajón solo en efectivo, desconectar el agente y ver el
  fallback.

### Fase 3: QR del KuDE (SIFEN)

**Qué exige la DNIT (Manual Técnico SIFEN v150 y notas técnicas):**

- El **KuDE** es la representación impresa del documento electrónico; lo genera el sistema del facturador
  y **no puede tener datos que no estén en el XML firmado**, salvo lo que permite el Manual Técnico [F1][F5].
- Lleva el **CDC** (Código de Control, 44 dígitos) y un **código QR** que permite consultar el documento en
  el portal e-Kuatia, aunque todavía no se haya transmitido [F1][F2].
- Para el consumidor final (B2C) se admite impresión en **impresora térmica tipo POS** (formato de cinta,
  "KuDE formato 2"); **no se permite matricial**; el papel tiene que mantener la impresión legible al menos
  **6 meses** [F5][F6].
- **Contenido del QR** (Manual Técnico v150, apartado 13.8; campo `dCarQR`, J002, que va en el XML) [F3][F4]:

  ```
  https://ekuatia.set.gov.py/consultas/qr?          (test: https://ekuatia.set.gov.py/consultas-test/qr?)
    nVersion=150
    &Id=<CDC de 44 dígitos>
    &dFeEmiDE=<fecha de emisión en hexadecimal>
    &dRucRec=<RUC del receptor>   (o &dNumIDRec=<documento> si no tiene RUC)
    &dTotGralOpe=<total>
    &dTotIVA=<total IVA>
    &cItems=<cantidad de ítems>
    &DigestValue=<DigestValue de la firma, en hexadecimal>
    &IdCSC=<id del CSC, por ejemplo 0001>
    &cHashQR=<SHA-256 en hex de (todo lo anterior sin la URL base + el CSC)>
  ```

  El **CSC** (Código de Seguridad del Contribuyente) lo entrega la DNIT y es **secreto**: no va en la URL,
  solo dentro del hash. Por eso **el QR lo arma el backend** (o el proveedor de facturación electrónica que
  se elija en REL-01), nunca el navegador.
- **Tamaño:** estándar ISO/IEC 18004; ancho mínimo de **25 mm** (22 de código + 3 de margen) [F4]. La URL
  ronda los ~400 caracteres, lo que da un QR de versión ~15 (77x77 módulos) con corrección M: a 203 ppp
  con **3 puntos por módulo mide ~29 mm** y con 4 puntos ~38 mm; entra cómodo en 80 mm y también en 58 mm
  (48 mm imprimibles), pero en 58 mm el resto del KuDE queda muy apretado.

**Por fase:**

- **Backend:** (dentro de REL-01) generar el XML, firmarlo, calcular el CDC y la **URL del QR** con el CSC;
  guardar `cdc` y `url_qr` en el documento; endpoint del KuDE en datos (para ticket) y en **PDF A4** (para
  mandar por WhatsApp o mail). Tests con el ejemplo del Manual Técnico (las librerías abiertas `pysifen` y
  otras verifican contra ese ejemplo [F3]).
- **Frontend:** plantilla de KuDE en cinta de 80 mm (y A4) con el QR: en fase 1 como SVG por
  `window.print()`, en fase 2 como QR nativo ESC/POS (`GS ( k`, módulo 3–4, corrección M) por el agente.
  CDC impreso en grupos de 4 dígitos para que se pueda tipear.
- **Hardware:** la térmica de 80 mm del kit; papel térmico de buena calidad (que garantice ≥ 6 meses; los
  rollos baratos se borran antes); el lector 2D para **verificar** que el QR impreso se lee.
- **Riesgos:** el ticket actual muestra datos que no están en el XML (por ejemplo "saldo en cuenta
  corriente"): hay que separar KuDE y comprobante interno o usar los campos de información adicional
  permitidos; papel de mala calidad; QR demasiado chico en impresoras genéricas.
- **Cómo probarlo:** generar KuDE en el ambiente de **test** de SIFEN (`consultas-test`), escanearlo con el
  celular y verificar que el portal muestre el documento; comparar el hash con el ejemplo del manual;
  imprimir en 58 y 80 mm y leer con el lector 2D y con 3 celulares distintos.

---

## 7. Kit de demo y pruebas (lista de compras)

| # | Equipo | Recomendación | Precio de referencia | Dónde (Paraguay) |
|---|---|---|---|---|
| 1 | **Lector 2D USB (HID)** | 3nStar SC402 2D (marca con manual de configuración y soporte local). Opción económica para probar compatibilidad: Quanta QTLCQ312 1D/2D. Opcional: uno **inalámbrico** (Satellite A-SCAN02) para depósito. | SC402 ~Gs. 490.000; QTLCQ312 ~Gs. 216.000–330.000; A-SCAN02 ~Gs. 262.000 [F20] | Nissei, Cellshop, Ofimarket, Mega Electrónicos, Tupi |
| 2 | **Térmica de 80 mm** | **Epson TM-T20III o TM-T20IV** (USB): la referencia de ESC/POS, driver con corte y cajón, buena documentación. Si se quiere probar red/9100, 3nStar RPT015 USB/LAN. | TM-T20III Gs. 1.170.000–1.370.000; TM-T20IV-L Gs. 1.161.000; RPT015 Gs. 1.214.000 [F21][F22] | Nissei, Shopping China, Tecnoga, Compulandia |
| 3 | **Impresora de etiquetas** | **Zebra ZD220d o ZD230d** de 4", térmica directa, 203 ppp, **ZPL** (permite probar fase 1 como impresora de Windows y fase 2 en RAW). Alternativa barata solo fase 1: Brother QL-800. | ZD220D ~Gs. 2.393.000 (agotada en la consulta); ZD230T/ZD421 desde ~US$ 355/340; QL-800 Gs. 1.150.000 [F34][F36] | Shopping China, Tecnocenter, Ditech, AGP Etiquetas, Ofimarket |
| 4 | Insumos | Rollos térmicos 80 mm (x10); etiquetas térmicas 50x25 mm (2 rollos) y una de góndola (por ejemplo 100x30); planchas A4 autoadhesivas. | Rollos de 50x25 (1.000–3.000 etiquetas) ~US$ 5–15 afuera; precio en Gs. a consultar | AGP Etiquetas (Paraguay), librerías y casas de informática |
| 5 | Opcional | **Cajón de dinero RJ11** (para fase 2) y un **celular Android** de gama media para cámara y conteos. | Cajón ~US$ 40–60 de referencia (no encontré precio en Gs.) | Casas de equipamiento POS |

**Total aproximado del kit básico (1 + 2 + 3):** Gs. 3.900.000–4.300.000 con Zebra, o
Gs. 2.600.000–3.000.000 con Brother QL-800 (sin pruebas de ZPL).

**Por qué este kit:** cubre los tres caminos que vamos a soportar (HID, ESC/POS, ZPL) con marcas que son
referencia del mercado; si funciona con estas, después se prueba compatibilidad con las genéricas que
compren los clientes (Xprinter, TypStar, ZKTeco), que emulan los mismos lenguajes.

---

## 8. Decisiones que necesita tomar el dueño

1. **Etiquetas:** ¿impresora de etiquetas en rollo (recomendado) o hojas A4 autoadhesivas en la impresora
   de oficina? ¿Qué tamaños: producto 50x25 mm y góndola 100x30 mm?
2. **Marca de etiquetas:** ¿Zebra/ZPL como estándar soportado (recomendado) o también TSPL (TSC/Xprinter)
   desde el principio?
3. **Códigos internos:** ¿aceptamos que los productos nuevos sin código de fábrica lleven un **EAN-13
   interno numérico** (`29...`) en vez de `PROD-00001`? (Los actuales siguen funcionando.)
4. **Balanza:** ¿se usa (o se va a usar) balanza que imprime etiquetas? ¿Marca y modelo? ¿Código con peso
   (recomendado) o con precio?
5. **Cajón:** ¿se abre en cada ticket (fácil, fase 1) o solo cuando entra efectivo (fase 2)?
6. **Ancho de ticket:** ¿80 mm como estándar (recomendado por SIFEN) y 58 mm solo como compatibilidad?
7. **Impresión directa en la nube:** ¿agente propio SAIL (recomendado: sin licencia, sirve para la
   instalada) o comprar QZ Tray (~US$ 599)?
8. **Celulares para conteo:** ¿Android (recomendado) o también iPhone, sabiendo sus limitaciones en PWA?
9. **SIFEN (REL-01):** ¿integración propia o por un proveedor? Define quién arma el XML, el CSC y el QR.
10. **Presupuesto del kit:** ~Gs. 4.000.000 (con Zebra) o ~Gs. 2.800.000 (con Brother).

---

## 9. Pedidos a otros líderes (para cuando se priorice)

- **Backend:** `producto_codigos`, endpoint de escaneo, generador EAN-13, configuración de balanza,
  etiquetas pendientes (REL-16); agente de impresión (fase 2) junto con el instalador (REL-29); QR del
  KuDE dentro de REL-01.
- **Frontend:** "código no registrado" y captura global en la caja; escaneo en recepción y conteo;
  componente de cámara; página de etiquetas; plantillas 58/80 mm; configuración de impresoras por PC.
- **QA:** casos de prueba con lector real (idioma de teclado), parser de balanza, impresión en 58/80 mm,
  fallback del agente.

---

## 10. Fuentes

SIFEN y normativa:

- [F1] DNIT, e-Kuatia, preguntas frecuentes (KuDE, CDC, QR, consulta pública):
  https://www.dnit.gov.py/web/e-kuatia/preguntas-frecuentes/-/categories/400161 y
  https://www.dnit.gov.py/en/web/e-kuatia/preguntas-frecuentes/-/categories/2705546
- [F2] DNIT, documentación técnica (Manual Técnico v150, notas técnicas, XSD):
  https://www.dnit.gov.py/web/e-kuatia/documentacion-tecnica
- [F3] `pysifen` (código abierto, QR según el apartado 13.8 del Manual Técnico v150, verificado contra el
  ejemplo del manual): https://github.com/josecuev/pysifen (archivos `src/pysifen/qr.py`,
  `docs/normativa-vigente.md`). Otras implementaciones con el mismo armado (`nVersion=150&Id=...&IdCSC=...`
  + SHA-256 con el CSC): https://github.com/TIPS-SA/facturacionelectronicapy-qrgen,
  https://github.com/Juan804041/sifen
- [F4] `pysifen`, `docs/normativa-vigente.md` (ISO/IEC 18004, ancho mínimo 25 mm, URL base de producción
  y de test, orden de parámetros): https://github.com/josecuev/pysifen
- [F5] Yo Facturo, impresoras térmicas en Paraguay y KuDE (B2C en mini impresora POS, papel legible 6
  meses, matricial no permitida, 80 mm recomendado): https://yo-facturo.com/blog/impresora-termica-paraguay/
- [F6] Última Hora, validez de facturas impresas en papel térmico:
  https://www.ultimahora.com/validez-facturas-impresas-papel-termico-n2848084
- [F7] Manual Técnico v141 (estructura del KuDE en cinta de papel), DNIT:
  https://www.dnit.gov.py/documents/20123/420592/Manual+T%C3%A9cnico+Versi%C3%B3n+141.pdf

Navegador, cámara y red local:

- [F11] MDN, Barcode Detection API: https://developer.mozilla.org/docs/Web/API/Barcode_Detection_API
- [F12] Can I use, BarcodeDetector: https://caniuse.com/mdn-api_barcodedetector
- [F13] MDN browser-compat-data (Chrome: solo macOS/ChromeOS en escritorio; Android desde 83) y reporte
  de Windows: https://github.com/mdn/browser-compat-data/issues/9030
- [F14] Polyfill `barcode-detector` (ZXing en WebAssembly):
  https://github.com/gruhn/barcode-detector-polyfill (archivado, continúa en el paquete de Sec-ant) y
  https://www.jsdelivr.com/package/npm/@sec-ant/barcode-detector
- [F15] Scanbot, comparación de escáneres JavaScript de código abierto (html5-qrcode inactivo):
  https://scanbot.io/blog/popular-open-source-javascript-barcode-scanners/
- [F16] WebKit, errores de cámara en apps de pantalla de inicio: https://bugs.webkit.org/show_bug.cgi?id=215884,
  https://bugs.webkit.org/show_bug.cgi?id=275527
- [F17] STRICH, problemas de cámara en PWA de iOS: https://kb.strich.io/article/29-camera-access-issues-in-ios-pwa
- [F31] Local Network Access en Chrome 142: https://blog.openreplay.com/es/chrome-local-network-access-lna-permiso/
  y https://www.dynamsoft.com/web-twain/docs/faq/chromium-142-local-network-access-issue.md
- [F32] Directivas `LocalNetworkAccessAllowedForUrls` / `LoopbackNetworkAllowedForUrls`:
  https://developer.samsung.com/browser/policy/local-network-access-allowed-for-urls.html y
  https://support.okta.com/help/s/article/configure-chrome-to-suppress-the-local-network-access-prompt-for-okta-fastpass

Lectores:

- [F18] Cheqroom, datos escaneados que salen mal (distribución de teclado del lector):
  https://knowledge.cheqroom.com/helpcenter/why-is-my-scanned-data-displayed-incorrectly-in-the-app
- [F19] Zebra, códigos de país/teclado para lectores en modo teclado:
  https://docs.zebra.com/us/en/scanners/general/sx20-series/sp20-prg/c-param-desc-country-codes/r-param-desc-country-code-barcodes-1.html
- [F20] Precios de lectores en Paraguay: Nissei (3nStar SC402) https://nissei.com/py/lector-de-codigo-de-barra-2d-3nstar-sc402-negro ;
  Cellshop (Quanta QTLCQ312) https://cellshop.com.py/4439790-lector-de-codigo-de-barras-quanta-quickscan-pro-1d-2d-qtlcq312-alambrico-1 ;
  Mega Electrónicos (Satellite A-SCAN02) https://megaelectronicos.com.py/producto/1436426/leitor-de-codigo-barra-satellite-a-scan02-2d-preto ;
  Tupi (Quanta QTLCB88N) https://www.tupi.com.py/producto/932195/LECTOR-DE-CODIGO-DE-BARRAS-QUANTA-QTLCB88N-USB-0.3-NG- ;
  Ofimarket https://ofimarket.com.py/categoria-producto/terminales-para-puntos-venta/lectores-de-codigos-de-barras/

Impresoras de tickets:

- [F21] Epson TM-T20III en Paraguay: https://nissei.com/py/impresora-termica-epson-tm-t20iii-001-bivolt ,
  https://www.shoppingchina.com.py/producto/impresora-epson-tm-t20iii-001-usb-bivolt-767041 ,
  https://tecnoga.com.py/producto/impresora-pos-termica-epson-tm-t20iii-001-biv-80mm-250mms-usb-serial-c31ch51001/
- [F22] Térmicas en Paraguay (TM-T20IV, 3nStar RPT015, TypStar, ZKTeco):
  https://nissei.com/py/informatica/impresoras-y-suplementos/termicas ,
  https://ofimarket.com.py/categoria-producto/impresoras/impresoras-termicas/ ,
  https://storeinformatica.com.py/producto/impresora-termica-de-tickets-zkp8003-8-0mm/
- [F23] Epson, referencia de comandos ESC/POS (QR `GS ( k` funciones 165/167/169/180/181, `GS V`, `ESC p`):
  https://download4.epson.biz/sec_pubs/pos/reference_en/escpos
- [F24] Apertura de cajón por el driver de Epson: https://genexis.atlassian.net/wiki/x/BgA_/ y
  https://support.treez.io/en/articles/13454174-selltreez-enable-your-cash-drawer-to-pop-epson-tm-m30
- [F25] Impresión silenciosa con `--kiosk-printing`: https://shoptill-e.com/support/48 ,
  https://galaxy.maropost.com/kb/articles/788-disable-print-preview-of-receipts-in-chrome
- [F26] Configuración de impresión de recibos desde el navegador (márgenes, tamaño de rollo):
  https://support.clubcaddie.com/printing-receipt-cut-off-when-printing-from-the-browser-version ,
  https://docs.oracle.com/en/industries/energy-water/shared/24a/cs-implementation-guide/CS_IMPLEMENTATION_24A/CCS_Receipt_Printing.28.4.html ,
  https://help.foosales.com/?p=502
- [F27] WebUSB con térmicas en Windows (requiere WinUSB con Zadig): https://help.cloudbridal.com/en/article/printing-receipts-with-a-thermal-printer-7t79xf/ y
  https://docs.rs/crate/escpos-rs/latest
- [F28] QZ Tray (impresión RAW ESC/POS y ZPL desde JavaScript): https://qz.io/ , https://qz.io/docs/raw-legacy
- [F29] QZ Tray, licencias y precios: https://qz.io/docs/licensing , https://buy.qz.io/Premium-Support-_p_13.html
- [F30] python-escpos (impresoras `Win32Raw`, `Network`, `Serial`, `Usb`; QR):
  https://python-escpos.readthedocs.io/en/latest/user/printers.html

Etiquetas y códigos:

- [F34] Zebra en Paraguay: https://www.shoppingchina.com.py/producto/etiquetadora-zebra-zd220d-751345 ,
  https://www.comprasparaguai.com.br/busca--zebra/ , https://agppackaging.com.py/producto/impresora-termica-zebra-zd220t-con-y-sin-ribbon/ ,
  https://www.tecnocenter.com.py/seccion2.php?tipo_id=172
- [F35] Xprinter XP-420B (especificaciones y precios de referencia): https://www.xprintertech.com/xp-420b-thermal-label-printer.html
- [F36] Impresoras de etiquetas en tiendas paraguayas: https://ofimarket.com.py/categoria-producto/terminales-para-puntos-venta/impresora-de-etiquetas/ ,
  https://ditech.com.py/impresoras/impresora-3nstar-etiqueta-4-termina-directa-usb-negro ,
  https://www.fastrax.com.py/producto/p/imp-ftx-etiqueta-4--tde010u-termi-direc/cod/11128
- [F37] bwip-js (generación de códigos en el navegador, SVG): https://cdn.jsdelivr.net/npm/bwip-js@4.11.4/README.md
- [F38] ZPL: introducción y visor en línea (Labelary) https://labelary.com/zpl.html ; Zebra, comandos de
  código de barras https://docs.zebra.com/us/en/printers/software/zpl-pg/c-zpl-font-barcodes-fonts-andbar-codes/r-zpl-font-barcodes-bar-code-field-instructions.html
- [F39] Prefijos GS1 por país (784 = Paraguay): https://en.wikipedia.org/wiki/List_of_GS1_country_codes
- [F40] Yo Facturo, códigos de barras en Paraguay y GS1: https://yo-facturo.com/blog/codigos-de-barras-paraguay-gs1/
- [F41] GS1, números de circulación restringida (prefijos 02 y 20–29):
  https://www.gs1.org/docs/barcodes/GSCN-23-006-RCN.pdf y https://www.gs1.org/docs/barcodes/SummaryOfGS1MOPrefixes20-29.pdf
- [F42] biip (documentación de RCN según las especificaciones generales de GS1): https://biip.readthedocs.io/stable/reference/rcn/
- [F43] Yo Facturo, códigos de balanza (peso variable): https://yo-facturo.com/herramientas/codigo-de-balanza-peso-variable/
- [F44] GS1 Suecia, etiquetado de artículos de peso variable: https://gs1.se/en/guides/how-to-guides/barcode-label-items-of-varying-weight/

Pagos con QR:

- [F33] BCP, estándar de pagos con QR (EMV QRCPS):
  https://www.bcp.gov.py/web/institucional/w/bcp-emite-reglamentaci%C3%B3n-para-adoptar-un-est%C3%A1ndar-de-pagos-con-qr-en-paraguay ;
  La Nación, SIP y QR Hub: https://www.lanacion.com.py/negocios/2026/04/27/nace-sip-la-evolucion-de-pagos-del-paraguay/
