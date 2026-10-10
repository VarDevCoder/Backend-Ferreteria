# SAIL — Material de prospección (octubre de 2026)

Para salir a buscar los primeros clientes **esta semana**: a quién ir, dónde están, una lista inicial,
cuánto cobrar y cómo responder las objeciones con honestidad. Complementa el [backlog](BACKLOG.md), al
que remiten los códigos REL-xx.

> **Fuentes y límites.** Normativa, mercado y directorios se consultaron con un buscador web. Desde el
> entorno de trabajo **no se pudieron abrir** las páginas de los directorios ni de la DNIT (bloqueo de red),
> así que la lista de la sección 3 sale de lo que esos directorios muestran en los resultados de búsqueda.
> Puede haber locales cerrados o mudados: **verificar cada uno en Google Maps antes de ir** (método en 3.3).
> Solo se usaron datos públicos de negocios (nombre comercial, ciudad o barrio, página pública). No se
> incluyen teléfonos ni datos de personas.

---

## Resumen en 8 líneas

1. **A quién primero:** ferreterías **chicas y medianas de barrio** del **Gran Asunción y Central**, con
   **una caja**, que **fían** a clientes y contratistas y hoy llevan el stock en cuaderno, Excel o de memoria.
2. **Por qué ellas:** SAIL ya resuelve su día (caja rápida con lector, cuenta corriente y deudores, stock
   con kardex, no vendible, compras y envíos) y lo que falta (SIFEN, IVA por producto, listas, varias
   cajas) les pesa menos: casi todas son **pequeños contribuyentes no designados** como facturadores
   electrónicos y pueden seguir facturando con talonario o con el facturador gratuito de la DNIT.
3. **A quién no todavía:** las designadas por la DNIT (RG 21/2024 y RG 52/2026), las de 2 o más cajas o
   sucursales, mayoristas que necesitan listas de precios y las de frontera que venden en dólares.
4. **Canales:** visita en persona con la demo en una tablet, recomendación de **distribuidores** que ya
   visitan ferreterías, de **contadores** que llevan a muchos comercios chicos, y una lista armada con
   **Google Maps**, contactando por el WhatsApp público del negocio, uno a uno.
5. **Precio recomendado:** **Gs. 199.000/mes** (1 caja) y **Gs. 449.000/mes** (hasta 3 cajas), con
   **implementación de Gs. 790.000**. Para los primeros 10 clientes, **precio fundador de Gs. 149.000/mes
   por 12 meses** a cambio de opinión y testimonio. La licencia Windows (**Gs. 5.900.000** con 1 año de
   actualizaciones; renovación **Gs. 1.200.000/año**) conviene ofrecerla como **preventa** porque todavía
   no existe el instalador.
6. **La objeción n.º 1 será la factura electrónica**: decir la verdad (todavía no; está en el plan) y
   calificar rápido si el comercio está obligado.

---

## 1. Segmentos: a quién le sirve SAIL hoy

### 1.1 Qué tiene SAIL hoy y qué falta

| Hoy (listo para mostrar) | Falta (ver backlog) |
|---|---|
| Caja rápida con lector de código de barras, atajos de teclado, total y vuelto en vivo, ticket | **Factura electrónica SIFEN** (REL-01): el ticket dice "comprobante interno" |
| Pago mixto: efectivo, débito, crédito, transferencia, **QR**, cheque y "a cuenta" en la misma venta | **IVA por producto** 10 % / 5 % / exento (REL-02): hoy un IVA para toda la empresa |
| **Cuenta corriente**: límite de crédito por cliente, cobros, deudores con antigüedad (0-30, 31-60, 61-90, +90) | **Listas de precios** por tipo de cliente (REL-07) |
| Stock con **kardex**, ajustes y alertas de stock bajo | **Varias cajas** al mismo tiempo (REL-09) |
| **Mercadería no vendible** y **reclamos** al proveedor | Devoluciones y anulaciones de ventas (REL-05) |
| Compras: cotización a proveedores y órdenes de compra; encargos de clientes; envíos | Importar productos desde Excel desde la pantalla (REL-04): **hoy lo hacemos nosotros** como parte de la implementación |
| Reportes de ventas (por medio de pago, por día, más vendidos con utilidad estimada) | Guaraníes y dólares (REL-18), cobro de pedidos y logística completa (REL-11/12) |
| Usuarios con 4 roles (dueño, encargado, vendedor, depósito); tope de descuento por rol | Versión instalada en Windows (REL-29) |
| Apariencia Windows 11 (tema claro/oscuro), uso en celular y tablet | Funcionar sin internet |

### 1.2 Segmentos, en orden de prioridad

| Prioridad | Segmento | Cómo reconocerlo | Por qué |
|---|---|---|---|
| **1 — ir ya** | **Ferretería de barrio chica o mediana, 1 caja** (1-6 empleados, 500-5.000 artículos) que **fía** y lleva stock en cuaderno o Excel | Local a la calle en zona residencial; cuaderno de "fiado" en el mostrador; factura con talonario; dueño atendiendo; pocas o ninguna reseña en Google | Es donde SAIL más cambia el día: control de caja, de lo fiado y del stock. Lo que falta casi no les afecta: no suelen estar designados para SIFEN y venden casi todo al 10 %. Precio accesible. |
| **1 — ir ya** | **Ferretería con contratistas y reparto** (corralón chico: cemento, varillas, caños) en Central | Camioneta propia; clientes "obra"; venta grande a cuenta | La cuenta corriente con límite, los envíos y el stock no vendible (bolsas rotas) les sirven mucho. Ojo: **todavía no se cobran pedidos por el sistema** (REL-11): venderlo como caja + cuenta corriente + stock. |
| **2 — después de la primera tanda** | Ferretería mediana con **2-3 cajas** o mayorista | Varias cajas, cola de clientes, lista de precios mayorista | Necesitan varias cajas (REL-09) y listas (REL-07). Se puede mostrar la demo y anotarlos como "cuando salga". |
| **2** | **Frontera** (Ciudad del Este, Pdte. Franco, Hernandarias, Encarnación) | Precios o cobros en dólares | Mercado grande, pero piden dólares (REL-18) y queda lejos para dar soporte presencial. |
| **3 — no ahora** | Ferreterías **designadas facturador electrónico** (RG 21/2024 y RG 52/2026) | Medianas/grandes, varias sucursales; el contador lo sabe; listas publicadas por la DNIT | Hoy están obligadas a emitir factura electrónica y SAIL no la emite. Volver cuando exista REL-01. |
| **No apuntar** | Cadenas y home centers (Ferrex, Nissei, Porter, Ferremarket, Lincoln, Laferré...) | Muchas sucursales, tienda online | Tienen ERP, compras centralizadas y SIFEN. Sirven como referencia de precios y para entender el mercado, no como clientes. |

**Dato de contexto.** La DNIT designó por grupos a **medianos y grandes contribuyentes**: RG 21/2024,
grupos 11 a 18 (unos 4.054 contribuyentes, de marzo de 2025 a diciembre de 2026) y RG 52/2026, grupos 19
a 24 (unos 3.000, de junio de 2026 a septiembre de 2027). Al resto (la gran mayoría de los comercios
chicos) la factura electrónica todavía no se le exige; muchos la usan igual con el **facturador gratuito
e-Kuatia'i** (de los más de 50.000 facturadores electrónicos, el 88,6 % son pequeños contribuyentes). Por
eso el segmento 1 puede usar SAIL hoy y seguir facturando como lo hace. **Antes de cerrar, preguntar
siempre**: "¿la DNIT le avisó que tiene que facturar electrónico?" (el aviso llega por el buzón Marandu).

---

## 2. Dónde están y cómo llegar

### 2.1 Zonas, en orden

1. **Gran Asunción y Central** (Asunción, Fernando de la Mora, San Lorenzo, Luque, Lambaré, Capiatá,
   Limpio, Mariano Roque Alonso, Ñemby, Villa Elisa): la mayor densidad de ferreterías y cerca para dar
   soporte en persona durante el primer mes. **Empezar acá.**
2. **Ciudad del Este, Presidente Franco y Hernandarias:** muchas ferreterías, comercio activo, uso de
   dólares (esperar REL-18 o venderles solo caja y stock).
3. **Encarnación:** ciudad en crecimiento, también con comercio de frontera.
4. Otras capitales departamentales (Coronel Oviedo, Caaguazú, Villarrica): más adelante, con soporte
   remoto.

### 2.2 Gremios, cámaras, ferias y organismos

- **No se encontró una cámara específica de ferreteros en Paraguay** (en Argentina existe CAFARA). Vale
  preguntar en las primeras visitas si los dueños se agrupan en algún grupo de WhatsApp o asociación local.
- **CAPACO — Cámara Paraguaya de la Industria de la Construcción** ([sitio](https://www.capaco.org.py/),
  [notas en La Nación](https://www.lanacion.com.py/negocios/2023/04/22/principal-preocupacion-es-la-situacion-economica-de-empresas-constructoras-senala-capaco/)):
  agrupa constructoras, que son los grandes clientes de las ferreterías. Canal indirecto (eventos, revista).
- **Constructecnia** ([Infonegocios](https://infonegocios.com.py/amp/default/constructecnia-tendra-nueva-sede-y-un-campo-ferial-de-50-000-m2),
  [La Nación 2024](https://www.lanacion.com.py/negocios/2024/05/25/constructecnia-resaltan-el-potencial-de-la-industria-nacional-de-la-construccion/)):
  feria de construcción; allí exponen distribuidores y fabricantes que venden a ferreterías.
- **Expo Ferretera & Terminaciones** ([ABC, 2022](https://www.abc.com.py/nacionales/2022/08/10/invitan-a-la-primera-expo-ferretera-y-terminaciones-en-centro-de-convenciones-mariscal/)):
  hubo una primera edición en 2022 (Grupo Paraguay Eventos y Emprendimientos, el mismo organizador de
  Constructecnia). No se encontró fecha 2026: consultar al organizador y, si la hay, ir como visitante o
  con un stand chico.
- **Misión comercial argentina de construcción y ferretería en Asunción** (15 y 16 de septiembre de 2026,
  [Cancillería argentina](https://cancilleria.gob.ar/es/argentinatradenet/noticias/mision-comercial-de-los-sectores-de-construccion-y-refrigeracion),
  [ABC](https://www.abc.com.py/negocios/2026/09/14/argentina-vuelve-a-la-carga-ahora-apunta-a-construccion-y-ferreteria/)):
  ya pasó, pero muestra quiénes son los importadores locales que reciben a esos proveedores.
- **Viceministerio de MIPYMES (MIC)**: organiza capacitaciones y eventos para pequeñas empresas
  ([Última Hora, jul/2026](https://www.ultimahora.com/mic-capacita-en-tecnologia-a-1-000-emprendedores-mipymes);
  según el viceministro hay unas 450.000 mipymes y solo ~40.000 formales,
  [La Nación](https://www.lanacion.com.py/politica_edicion_impresa/2025/05/26/de-450000-mipymes-solo-40000-son-formales-dice-viceministro/)).
  Ofrecer una charla gratuita "Ordená tu caja y tu fiado" en sus eventos.
- **Cámaras de comercio locales** (Ciudad del Este, Encarnación): no se encontraron sus sitios oficiales en
  la búsqueda; buscarlas en Facebook o preguntar en la municipalidad.

### 2.3 Distribuidores y mayoristas: el mejor canal

Los vendedores de los distribuidores **visitan a las mismas ferreterías todas las semanas** y conocen al
dueño. Propuesta: un **mes de abono de comisión por cada cliente** que recomienden (o un descuento en su
propio SAIL), y material simple para dejar en el mostrador. Por dónde empezar:

- **FISAE — Ferretería Industrial S.A.E.**, importadora y distribuidora de herramientas, Asunción
  ([sitio](https://www.fisae.com.py/index_new.php)).
- **Ferretería Internacional S.A.**, Asunción ([Facebook](https://www.facebook.com/ferreteriainternacionalpy/)).
- Distribuidores por zona: [BuscoInfo — distribuidores de ferreterías en Asunción](https://www.buscoinfo.com.py/buscar/distribuidores-ferreterias/asuncion)
  y [en todo el país](https://www.buscoinfo.com.py/buscar/distribuidores-ferreterias/todo-el-pais-todo-el-pais).
- Preguntar en cada visita: "¿quién le trae la mercadería?". Los 3-4 nombres que más se repitan son el
  canal.

**Contadores:** un estudio contable lleva decenas de comercios chicos y es quien les habla de la DNIT.
Ofrecerles acceso de solo lectura a los reportes de sus clientes y la misma comisión por recomendación.
(Contexto: [encuesta a 142 contadores sobre la factura electrónica](https://revistas.uni.edu.py/index.php/rseisa/article/view/667).)

### 2.4 Grupos y páginas de comercios

- Directorios con fichas públicas de ferreterías por ciudad: **[Yagua.com](http://yagua.paraguay.com/ferreterias-66/ciudad/asuncion-223)**
  y **[BuscoInfo](https://www.buscoinfo.com.py/buscar/ferreterias)** (ver los links por ciudad en 3.1).
- Listado público de comercios adheridos de un banco, con rubro "Ferreterías e iluminación"
  ([Sudameris Club, 2020](https://www.sudamerisclub.com.py/wp-content/uploads/2020/09/Listado-de-comercios.pdf)):
  viejo, pero útil para saber qué ferreterías aceptan tarjeta.
- **Facebook e Instagram**: muchas ferreterías publican ofertas en su página. Buscar "ferretería" + ciudad
  en Facebook (páginas) y en Marketplace. Comentar o escribir **desde la página de SAIL** al Messenger del
  negocio, nunca a perfiles personales.
- Grupos de Facebook de comercios o emprendedores de cada ciudad: publicar contenido útil (por ejemplo
  "cómo controlar el fiado") y no avisos repetidos.

### 2.5 Google Maps + WhatsApp Business: armar la lista en una hora

**Google Maps (40 min, ~50 ferreterías):**
1. Buscar `ferretería` en cada ciudad de la zona 1 (por ejemplo "ferretería Luque") y recorrer la lista.
2. Por cada local, anotar en una planilla: nombre comercial, ciudad/barrio, link de Maps, web o Facebook si
   tiene, cantidad de reseñas, horario y una nota rápida.
3. **Clasificar por tamaño** con lo que se ve: 10-150 reseñas y fotos de un local con 1 mostrador = segmento
   1; más de 300 reseñas, varias cajas o sucursales = segmento 2 o cadena; sin fotos ni reseñas = verificar
   que exista.
4. Guardarlas en una lista de Maps ("Prospectos SAIL") para planificar la ruta de visitas del día
   (8-10 visitas por mañana en una misma zona).

**WhatsApp Business (20 min de preparación):**
1. Usar un número de empresa (no el personal) con perfil completo: logo de SAIL, descripción, horario y
   link a una demo o video corto.
2. Crear **etiquetas**: Prospecto, Contactado, Demo agendada, Prueba, Cliente, No interesado.
3. **Respuestas rápidas**: presentación de 3 líneas, precio, "qué pasa con la factura electrónica".
4. Escribir **solo al número comercial que el negocio publica** (Maps, Facebook), **uno por uno**, con un
   mensaje personalizado y que pida permiso: "Hola, soy … de SAIL. Ayudamos a ferreterías de Luque a
   controlar caja, fiado y stock. ¿Le puedo mostrar en 10 minutos en su local esta semana?". Nada de
   envíos masivos ni listas compradas: WhatsApp bloquea las cuentas que mandan mensajes no solicitados
   ([Cliengo](https://guiawabusiness.cliengo.com/evitar-bloqueos), [AWS](https://docs.aws.amazon.com/es_es/social-messaging/latest/userguide/whatsapp-best-practices.html)),
   y si alguien dice que no, no se le vuelve a escribir.
5. Lo que mejor funciona en el rubro sigue siendo **ir en persona** a la hora tranquila (media mañana o
   media tarde) con la demo abierta en una tablet.

---

## 3. Lista inicial de prospectos

### 3.1 Lista (48 ferreterías, solo datos públicos de negocios)

Columna "Segmento": estimación con lo que muestra el directorio. **Verificar en Maps antes de visitar.**
Las fuentes son directorios públicos y pueden estar desactualizados.

| # | Nombre comercial | Ciudad / zona | Web o página pública | Segmento estimado | Fuente |
|---|---|---|---|---|---|
| 1 | Ferretería Quinta Avenida S.A. | Asunción | [ferrequinta.com.py](https://ferrequinta.com.py/) | 1-2 (verificar tamaño) | Web propia |
| 2 | Casa Bento (Ferretería Bento) | Asunción | [casabento.com.py](https://casabento.com.py/) | 2 | Web propia / Yagua |
| 3 | Ferretería Internacional S.A. | Asunción | [Facebook](https://www.facebook.com/ferreteriainternacionalpy/) | 2 (o canal) | Facebook / Yagua |
| 4 | Gómez Ferretería | Asunción | [Yagua](http://yagua.paraguay.com/ferreterias-66/ciudad/asuncion-223) | 1 | Yagua |
| 5 | Ferretería Ferrar | Asunción | [Yagua](http://yagua.paraguay.com/ferreterias-66/ciudad/asuncion-223) | 1 | Yagua |
| 6 | Semar S.R.L. | Asunción | [Yagua](http://yagua.paraguay.com/ferreterias-66/ciudad/asuncion-223) | 1-2 | Yagua |
| 7 | Ferretería Jericó | Asunción | [Yagua](http://yagua.paraguay.com/ferreterias-66/ciudad/asuncion-223) | 1 | Yagua |
| 8 | Ferretería Manduvirá | Asunción | [Yagua](http://yagua.paraguay.com/ferreterias-66/ciudad/asuncion-223) | 1 | Yagua |
| 9 | Ferretería Kokela | Asunción | [Yagua](http://yagua.paraguay.com/ferreterias-66/ciudad/asuncion-223) | 1 | Yagua |
| 10 | RC Ferretería | Asunción | [Yagua](http://yagua.paraguay.com/rc-ferreteria-2865.html) | 1 | Yagua |
| 11 | Ferretería San Agustín | Asunción | [Yagua](http://yagua.paraguay.com/san-agustin-ferreteria-24948.html) | 1 | Yagua |
| 12 | Ferretería Ñu Guazú | Asunción | [Yagua](http://yagua.paraguay.com/-u-guazu-ferreteria-10815.html) | 1 | Yagua |
| 13 | Ferretería Santaní | Asunción | [Yagua](http://yagua.paraguay.com/santani-ferreteria-13444.html) | 1 | Yagua |
| 14 | Ferretería San José | Asunción | [Yagua](http://yagua.paraguay.com/san-jose-ferreteria-25535.html) | 1 | Yagua |
| 15 | Casa Modiga S.A. | Asunción | [Yagua](http://yagua.paraguay.com/ferreterias-66/ciudad/asuncion-223) | 2 | Yagua |
| 16 | Carpicenter S.A. | Fernando de la Mora | [Yagua](http://yagua.paraguay.com/ferreterias-66/ciudad/fernando-de-la-mora-169) | 2 | Yagua |
| 17 | El Astro S.R.L. | Fernando de la Mora | [Yagua](http://yagua.paraguay.com/ferreterias-66/ciudad/fernando-de-la-mora-169) | 1 | Yagua |
| 18 | Ferretería Inter | Fernando de la Mora | [Yagua](http://yagua.paraguay.com/ferreterias-66/ciudad/fernando-de-la-mora-169) | 1 | Yagua |
| 19 | Ferretería Meka | Fernando de la Mora | [Yagua](http://yagua.paraguay.com/ferreterias-66/ciudad/fernando-de-la-mora-169) | 1 | Yagua |
| 20 | Ferretería Caapucú | Fernando de la Mora (Zavala Cue) | [Yagua](http://yagua.paraguay.com/ferreterias-66/ciudad/fernando-de-la-mora-169) | 1 | Yagua |
| 21 | Leo S.A. Ferretería | Fernando de la Mora | [BuscoInfo](https://www.buscoinfo.com.py/buscar/ferreterias/fernando-de-la-mora-) | 1-2 | BuscoInfo |
| 22 | Ferretería El Industrial | Fernando de la Mora | [BuscoInfo](https://www.buscoinfo.com.py/buscar/ferreterias/fernando-de-la-mora-) | 1 | BuscoInfo |
| 23 | Ferretería La Sanlorenzana | San Lorenzo | [BuscoInfo](https://www.buscoinfo.com.py/buscar/ferreterias/san-lorenzo) | 1-2 | BuscoInfo |
| 24 | El Chavo Ferretería | San Lorenzo | [BuscoInfo](https://www.buscoinfo.com.py/buscar/ferreterias/san-lorenzo) | 1 | BuscoInfo |
| 25 | San Pedro S.R.L. (ferretería y materiales) | San Lorenzo | [Yagua](http://yagua.paraguay.com/materiales-de-construccion-68/ciudad/san-lorenzo-181) | 1 (corralón) | Yagua |
| 26 | Mbachio Ferretería | Lambaré | [Yagua](http://yagua.paraguay.com/ferreterias-66/ciudad/lambare-174) | 1 | Yagua |
| 27 | Del Sur Pinturería y Ferretería | Lambaré | [Yagua](http://yagua.paraguay.com/ferreterias-66/ciudad/lambare-174) | 1 | Yagua |
| 28 | Jec Ferretería | Luque | [BuscoInfo](https://www.buscoinfo.com.py/buscar/ferreterias/luque) | 1 | BuscoInfo |
| 29 | Santo Domingo Ferretería | Luque | [BuscoInfo](https://www.buscoinfo.com.py/buscar/ferreterias/luque) | 1 | BuscoInfo |
| 30 | Ferretería Estrella de Luque | Luque | [BuscoInfo](https://www.buscoinfo.com.py/buscar/ferreterias/luque) | 1 | BuscoInfo |
| 31 | Ferretería Porvenir | Luque | [Sudameris Club (2020)](https://www.sudamerisclub.com.py/wp-content/uploads/2020/09/Listado-de-comercios.pdf) | 1 | Listado de comercios |
| 32 | El Taita | Luque | [Sudameris Club (2020)](https://www.sudamerisclub.com.py/wp-content/uploads/2020/09/Listado-de-comercios.pdf) | 1 | Listado de comercios |
| 33 | Ferretería La Paraguaya | Mariano Roque Alonso | — | 1 | Directorio (buscador) |
| 34 | Ferretería Panorama | Mariano Roque Alonso | [Sudameris Club (2020)](https://www.sudamerisclub.com.py/wp-content/uploads/2020/09/Listado-de-comercios.pdf) | 1 | Listado de comercios |
| 35 | Electrifer | Mariano Roque Alonso | [Sudameris Club (2020)](https://www.sudamerisclub.com.py/wp-content/uploads/2020/09/Listado-de-comercios.pdf) | 1 | Listado de comercios |
| 36 | Ferre Center | Limpio | [BuscoInfo](https://www.buscoinfo.com.py/rubro-zona/limpio/ferreterias/PRD1000213/zz11012) | 1 | BuscoInfo |
| 37 | El Portal Ferretería | Limpio | [BuscoInfo](https://www.buscoinfo.com.py/rubro-zona/limpio/ferreterias/PRD1000213/zz11012) | 1 | BuscoInfo |
| 38 | Solea Ferretería | Ñemby | [BuscoInfo](https://www.buscoinfo.com.py/buscar/ferreterias/%C3%B1emby-central) | 1 | BuscoInfo |
| 39 | Ferretería María Auxiliadora | Ñemby | [Sudameris Club (2020)](https://www.sudamerisclub.com.py/wp-content/uploads/2020/09/Listado-de-comercios.pdf) | 1 | Listado de comercios |
| 40 | Ferretería Monte Cristo | Villa Elisa | [Sudameris Club (2020)](https://www.sudamerisclub.com.py/wp-content/uploads/2020/09/Listado-de-comercios.pdf) | 1 | Listado de comercios |
| 41 | Ferretería 1122 | Capiatá | — | 1 | Directorio (buscador) |
| 42 | Ferretería Ferrati | Ciudad del Este | [BuscoInfo](https://www.buscoinfo.com.py/local/ferreteria-ferrati/LOC755830001) | 2 (frontera) | BuscoInfo |
| 43 | Ferretería Federal | Ciudad del Este | [BuscoInfo](https://www.buscoinfo.com.py/rubro-zona/cde/ferreterias/PRD1000213/z00001) | 2 (frontera) | BuscoInfo |
| 44 | Ferretería San Carlos | Presidente Franco | [BuscoInfo](https://www.buscoinfo.com.py/neg/ferreter%C3%ADa_san_carlos-presidente_franco--alto_paran%C3%A1-76861001) | 2 (frontera) | BuscoInfo |
| 45 | Ferretería La Tuerca | Hernandarias | [BuscoInfo](https://www.buscoinfo.com.py/buscar/ferreterias/hernandarias) | 2 (frontera) | BuscoInfo |
| 46 | Ferretería Tosca | Hernandarias | [BuscoInfo](https://www.buscoinfo.com.py/buscar/ferreterias/hernandarias) | 2 (frontera) | BuscoInfo |
| 47 | La Japonesita S.R.L. | Encarnación | [BuscoInfo](https://www.buscoinfo.com.py/buscar/ferreterias/encarnaci%C3%B3n) | 2 (frontera) | BuscoInfo |
| 48 | Guaraní Ferretería | Encarnación | [BuscoInfo](https://www.buscoinfo.com.py/buscar/ferreterias/encarnaci%C3%B3n) | 2 (frontera) | BuscoInfo |

Más nombres en los mismos directorios para completar la ruta: en Asunción (Norma, Victoria, CGC,
Ferretería Industrial S.R.L.), Ciudad del Este (Ferretería Rocky), Presidente Franco (Mafer, Ferretería
Central, San Blas Ferretería), Hernandarias (Ferretería El Trébol, Integral Ferretería, Super Pilar S.A.) y
Encarnación (La Paz Ferretería, Ferretería Paraná, Lumar Ferretería).

### 3.2 Referencia, no prospectos (cadenas y grandes)

[Ferrex](https://infonegocios.com.py/y-ademas/ferrex-la-chilena-que-llega-al-pais-para-complementar-el-segmento-de-las-ferreterias)
(Asunción), [Nissei](https://nissei.com/py/electrodomesticos-muebles/ferreteria), [Porter](https://porter.com.py/),
[Laferré](https://www.laferre.com.py/) (San Lorenzo, Fernando de la Mora, Luque),
[Ferremarket](https://www.ferremarket.com.py/sucursales) (Mariano Roque Alonso, San Lorenzo, Ñemby),
Lincoln S.A. y Petersen. Sirven para comparar precios y surtido; no son el cliente de SAIL hoy.

### 3.3 Si hay que rehacer o ampliar la lista (método de 1 hora)

1. Abrir los directorios por ciudad de 3.1 y Google Maps (`ferretería` + ciudad) en dos pestañas.
2. Copiar a la planilla **solo**: nombre comercial, ciudad/barrio, link de Maps y web o red social del
   negocio. No copiar nombres de dueños ni teléfonos personales; para contactar, usar el número comercial
   que muestra el propio negocio.
3. Confirmar en Maps que el local existe (fotos recientes, horario, reseñas del último año).
4. Clasificar el segmento con la regla de 2.5 y ordenar por zona para armar rutas.
5. Meta: 50 locales en Central, 10 visitas por mañana, 2 mañanas por semana.

---

## 4. Precios sugeridos (en guaraníes)

### 4.1 Base para calcular

| Referencia | Valor | Fuente |
|---|---|---|
| Dólar (BCP, 3/8/2026) | ~Gs. 5.960 por US$ | [Infobae/EFE](https://www.infobae.com/america/agencias/2026/08/03/la-moneda-paraguaya-se-aprecia-mas-de-un-10-frente-al-dolar-en-lo-que-va-de-2026/) |
| Salario mínimo desde julio de 2026 | Gs. 3.044.000/mes | [ABC](https://www.abc.com.py/economia/2026/06/26/reajuste-del-salario-minimo-estos-son-los-pagos-por-hora-dia-y-jornada-nocturna/), [Bloomberg Línea](https://www.bloomberglinea.com/latinoamerica/como-queda-el-salario-minimo-en-paraguay-tras-el-reajuste-del-5-anunciado-por-pena/) |
| Odoo Standard (por usuario) | US$ 25-31/mes ≈ Gs. 150.000-185.000 **por usuario** | [ERP Research](https://www.erpresearch.com/pricing/odoo) |
| Loyverse (POS gratis + inventario avanzado + empleados) | US$ 25 + US$ 5/mes ≈ Gs. 180.000 | [xpay](https://www.xpay.sh/saas-pricing/loyverse-pos/) |
| Alegra POS | desde ~US$ 30 ≈ Gs. 180.000 | [Capterra](https://www.capterra.es/software/1024697/alegra-pos) |
| Sistemas paraguayos con SIFEN (FactPy, Alysoft, eVENDÉ, Yo Facturo) | no publican montos | [BACKLOG, sección 6](BACKLOG.md#6-competencia-y-estándar-del-rubro) |
| Facturador e-Kuatia'i de la DNIT | gratis (sin stock ni caja) | [DNIT](https://www.dnit.gov.py/web/e-kuatia) |

**Lógica.**
- Una ferretería chica no debería pagar por el sistema más de lo que pierde por mes en fiado no cobrado o
  en faltantes de caja. Un plan de ~Gs. 200.000 es **6-7 % de un salario mínimo**: el costo de unas
  horas de un empleado.
- Las alternativas extranjeras cuestan Gs. 150.000-200.000 por mes **sin** cuenta corriente paraguaya ni
  soporte local, y Odoo cobra por usuario.
- Hoy **SAIL no emite factura electrónica**: el precio tiene que estar por debajo de lo que costará un
  sistema local con SIFEN, y subir cuando lo tenga (mantener el precio fundador a los primeros).
- La implementación **se cobra aparte** porque la carga del catálogo hoy la hacemos nosotros (REL-04
  todavía no está en pantalla) y es la mayor parte del trabajo de cada alta.

### 4.2 Tabla de precios

| Concepto | Qué incluye | Rango | **Recomendado** |
|---|---|---|---|
| **Plan Mostrador** (nube, mensual) | 1 caja, hasta 4 usuarios, todos los módulos, copias de seguridad, soporte por WhatsApp en horario comercial | Gs. 150.000 – 250.000 | **Gs. 199.000/mes** (≈ US$ 33) |
| **Plan Comercio** (nube, mensual) | Hasta 3 cajas, hasta 10 usuarios, soporte prioritario. *Las 3 cajas simultáneas llegan con REL-09; hasta entonces, ofrecerlo como "Mostrador + usuarios extra" al mismo precio que Mostrador* | Gs. 350.000 – 550.000 | **Gs. 449.000/mes** (≈ US$ 75) |
| Pago anual (cualquier plan) | 12 meses por adelantado | 10-17 % de descuento | **2 meses gratis** (paga 10) |
| **Precio fundador** (primeros 10 clientes) | Plan Mostrador, a cambio de opinión mensual y permiso para usar su nombre como referencia | Gs. 120.000 – 150.000 | **Gs. 149.000/mes por 12 meses** |
| **Implementación y carga inicial** (una vez) | Configuración, carga del catálogo desde su Excel o lista (hasta 3.000 artículos), clientes con saldo inicial, usuarios, 2 capacitaciones en el local (caja y encargado), acompañamiento la primera semana | Gs. 500.000 – 1.500.000 | **Gs. 790.000**; artículos extra o carga desde papel: **Gs. 150.000 cada 500 artículos** |
| **Licencia perpetua Windows** | 1 caja instalada en la PC del local, 1 año de actualizaciones y soporte, copias de seguridad automáticas | Gs. 4.500.000 – 7.000.000 (≈ 24-30 meses del plan nube) | **Gs. 5.900.000** (≈ US$ 990) + **Gs. 1.500.000 por caja adicional**. *Todavía no existe el instalador (REL-29): venderla solo como **preventa con seña** y fecha comprometida* |
| **Renovación anual** de actualizaciones y soporte (Windows) | Nuevas versiones (incluido SIFEN cuando salga) y soporte | 15-25 % de la licencia | **Gs. 1.200.000/año** (≈ 20 %). Si no renueva, sigue usando su versión. |
| Factura electrónica (cuando salga REL-01) | Emisión de FE, NC y remisión | depende del costo por documento del proveedor | Incluida hasta un tope de documentos/mes en cada plan; definir cuando se elija el proveedor |

**Recomendación para esta semana:** salir con **Plan Mostrador a Gs. 199.000**, **precio fundador a Gs.
149.000 por 12 meses** para los primeros 10 e **implementación de Gs. 790.000** (que se puede bajar a Gs.
490.000 si el cliente entrega su lista en Excel limpia). No prometer fechas de SIFEN ni de Windows sin
confirmarlas con el equipo.

---

## 5. Las 10 objeciones más probables (y respuestas honestas)

| # | Objeción | Respuesta honesta |
|---|---|---|
| 1 | **"¿Hace factura electrónica?"** | "Todavía no. Hoy SAIL entrega un comprobante interno y usted sigue facturando como ahora (talonario o el facturador gratuito de la DNIT). La factura electrónica es lo próximo que estamos haciendo y los clientes fundadores la reciben sin costo extra." **Calificar:** "¿La DNIT ya le avisó que tiene que facturar electrónico?" Si dice que sí, **no venderle hoy**: anotar y volver cuando esté. |
| 2 | **"Ya tengo sistema."** | "¿Qué es lo que más le cuesta con el que tiene? ¿El fiado, el cierre de caja, saber qué falta?" Mostrar solo eso en la demo. Si su sistema ya factura electrónico y está conforme, no insistir: no ganamos nada cambiándolo hoy. |
| 3 | **"Es caro."** | "Son Gs. 199.000 por mes, unos Gs. 6.600 por día. ¿Cuánto fiado se le queda sin cobrar o cuánto le falta en la caja por mes?" Ofrecer el precio fundador y el pago anual. Si la ferretería es muy chica (dueño solo, sin fiado), probablemente **no es cliente todavía**. |
| 4 | **"¿Y si se corta internet?"** | "SAIL funciona en la nube: sin internet no se puede vender en el sistema. Lo que recomendamos es tener los datos del celular como respaldo (compartir internet a la PC). Los datos no se pierden, quedan guardados en el servidor." **No decir que funciona sin conexión.** La versión instalada en Windows está en el plan. |
| 5 | **"¿Quién me carga los productos?"** | "Nosotros, en la implementación: usted nos pasa su lista (Excel, la del proveedor o una foto de la lista de precios) y la dejamos cargada con el stock inicial. Después, las altas nuevas son de a una o por planilla." |
| 6 | **"Mis empleados no saben usar computadora."** | "La caja se usa como una calculadora: se escanea o se escribe el nombre, Enter, y F9 para cobrar. Le capacitamos en el local y la primera semana estamos por WhatsApp." Mostrar una venta completa en 10 segundos. |
| 7 | **"Tengo dos cajas" / "Tengo sucursal."** | "Hoy SAIL maneja una caja por empresa; varias cajas al mismo tiempo están en desarrollo." Si tiene 2 cajas que trabajan a la vez, **ser claro**: le conviene esperar; anotar para cuando salga. |
| 8 | **"Vendo distinto al mayorista y al contratista."** | "Hoy hay un precio por producto y el encargado puede hacer descuento o cambiar el precio en la venta (el vendedor no). Las listas de precios por tipo de cliente están en camino." |
| 9 | **"¿Mis datos están seguros? ¿Quién los ve?"** | "Cada ferretería tiene su propia base de datos, con usuario y contraseña por empleado y permisos por rol. Hacemos copias de seguridad y, si un día se va, le entregamos sus datos en Excel." (Compromiso a cumplir: dejar por escrito la exportación y el respaldo.) |
| 10 | **"¿Y si ustedes desaparecen?" / "¿Quién me atiende?"** | "Soporte por WhatsApp en horario comercial y visita si hace falta en Central. Sus datos son suyos y se los entregamos cuando quiera. Sin contrato de permanencia: si no le sirve, deja de pagar." |

**Una más que conviene tener lista:** "¿Calcula el IVA del 5 %?" — "Hoy toma un IVA para toda la empresa
(el 10 %, que es casi todo lo de ferretería). El IVA por producto está en el plan." En ferretería lo que no
es 10 % es poco; si el cliente vende mucho al 5 % o exento, anotarlo.

---

## 6. Qué conviene que el equipo tenga antes de la primera visita

- **Una demo pública** con datos de ferretería (la demo existe; confirmar que esté cargada en producción:
  `SEED_DEMO=true` en Vercel) y un **usuario de demo** que se pueda resetear.
- **Script de importación** de productos y clientes desde Excel, aunque sea interno (base de REL-04).
- **Respaldo y exportación** de los datos de cada cliente (promesa de la objeción 9).
- Un **video de 60 segundos** de una venta con lector, una venta a cuenta y el cierre de caja, para mandar
  por WhatsApp.
- Un **contrato simple** de 1 página (plan, precio, soporte, datos del cliente, sin permanencia).
