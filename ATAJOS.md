# MouthClick: controles y atajos

El menú principal se organiza en cinco páginas con Anterior/Siguiente y
Alt + flecha izquierda/derecha. Perfil y cámara están en la primera; luego
gestos, movimiento, ayudas y atajos. No requiere desplazamiento con scroll.

El filtro del cursor reduce gradualmente el movimiento cerca del límite de la
zona muerta y evita redondear siempre hacia arriba/izquierda. La zona muerta
existente sigue ajustándose desde Sensibilidades; no se cambiaron los perfiles.

## Inicio directo y configuración

La configuración de Octavio ahora se llama Por Defecto. Se conserva como base:
guardar cambios desde esa base crea Personalizado 1, Personalizado 2, etc.
Los perfiles personalizados se pueden actualizar normalmente. También podés
escribir un nombre nuevo desde el menú inicial.

El lanzador y la entrada principal impiden abrir una segunda instancia nueva.
Las versiones anteriores ya abiertas deben cerrarse una vez para aplicar esto.
Liberar se retiró de la burbuja; Esc y F10 siguen disponibles como atajos.

Abrir MouthClick.vbs inicia con el perfil marcado como predeterminado. Si todavía
no hay uno marcado, usa Octavio si existe. Sin ninguno de ellos, muestra el menú.
Al guardar y comenzar desde el menú, ese perfil pasa a ser el predeterminado.
Configurar MouthClick.vbs siempre abre el menú para editar o elegir un perfil;
usalo con la sesión anterior cerrada. No se configuró el inicio con Windows.

## Gestos de cejas (experimentales)

En Configurar MouthClick, asigná acciones a Levantar las cejas y Fruncir el ceño.
Por defecto están en Nada. Al comenzar mantené el rostro relajado y los ojos
abiertos unos segundos. Sostené la expresión brevemente y volvé a neutral antes
de repetirla. K recalibra ojos y cejas. Si pierde la cara, recalibra las cejas.
Son detectores heurísticos: necesitan prueba con la cámara y expresiones de cada
persona; todavía no hay validación con usuarios. No agregan otro modelo de IA.

Al pausar se liberan los botones, se cancela el menú contextual y se repite la
limpieza tras 200 ms. Los gestos y el clic derecho no actúan mientras está pausado.

La ventana inicial abre maximizada. Sensibilidades se divide en cuatro páginas con dos grupos de ajustes por página;
usá Anterior / Siguiente o Alt + flecha izquierda / derecha para recorrerlas.
Los cambios se prueban en vivo. Guardar en perfil los conserva; Cerrar sin
guardar restaura los valores con los que se abrió el panel.

| Tecla | Acción |
| --- | --- |
| F1 / F2 | Bajar / subir sensibilidad vertical (Y). |
| F3 / F4 | Bajar / subir sensibilidad horizontal (X). |
| F5 / F6 | Hacer el guiño más sensible / más estricto. |
| F7 | Centrar el cursor. |
| F8 | Activar / desactivar autoclick por permanencia. |
| F9 | Mostrar / ocultar teclado en pantalla. |
| F10 | Liberar botones del mouse y arrastre; enviar Escape. |
| F11 | Pausar / continuar el control facial. |
| F12 | Salir de la aplicación. |
| Esc | Liberar botones del mouse y arrastre. |
| R | Volver a detectar el punto facial seleccionado. |
| K | Recalibrar el guiño. |

**Liberar (Esc)** suelta un clic sostenido o arrastre y envía Escape para cancelar
menús o acciones de la aplicación activa. El control facial sigue funcionando.

**Pausar** pide confirmación; hasta confirmar, el control facial sigue activo.
Una vez confirmado, suelta los botones y detiene el control facial, los gestos y el
autoclick. Para retomar, usá F11 o el botón Continuar con un mouse u otro
dispositivo de entrada.

**Salir de la app** pide confirmación antes de cerrar MouthClick. F11 y F12
también piden confirmación (continuar con F11 es inmediato).
Para conservar ajustes del panel,
presioná Guardar en perfil antes de salir.

M y B ya no activan funciones globales al escribir. La burbuja permanece visible
y en primer plano; Contraer reduce su tamaño sin ocultarla.
La vista de cámara permanece oculta; la cámara sigue capturando
para detectar la cara. Los atajos de sensibilidad cambian la sesión actual:
abrí Sensibilidades y guardá para conservarlos en el perfil.

Estos cambios están en el código fuente. Reiniciá desde Abrir MouthClick.bat
para probarlos; los ejecutables anteriores no se actualizaron.

## Modos de la burbuja

Para mover la burbuja con la cara, hacé clic en el encabezado: seguirá al cursor.
Repetí un gesto de clic para fijarla, sin activar la ventana que quede debajo.
Con mouse físico también podés mantener presionado y arrastrar el encabezado.
Los modos activos mantienen el fondo rojo incluso al pasar y retirar el cursor.
Pausar suelta los botones y envía una sola vez Escape para cerrar menús abiertos.

Arrastre OFF / ON activa un modo temporal. Al activarlo, el gesto que el perfil
asigna a Click izquierdo toma el objeto; repetirlo lo suelta. El modo sigue
activo para arrastrar otro objeto. Volv? al bot?n Arrastre para desactivarlo.
Desactivar el modo tambi?n suelta cualquier objeto sostenido. Liberar/F10
suelta el objeto sin desactivar el modo. El autoclick por permanencia no act?a
sobre el escritorio mientras Arrastre est? activo, para evitar soltar sin querer.

Oficina OFF / ON activa gui?o izquierdo = Ctrl+C (copiar), gui?o derecho =
Ctrl+V (pegar) y boca = clic izquierdo. Primero seleccion? el texto u objeto
que quer?s copiar, y ubic? el foco donde quieras pegar. Los atajos se env?an
a la aplicaci?n activa. Desactivar Oficina restaura los gestos del perfil.

Sobre la burbuja, teclado, ajustes y confirmaciones de MouthClick, los gestos
activos producen un clic izquierdo normal para poder operar sus botones.
Arrastre y Oficina son excluyentes y no modifican el perfil guardado.

Sensibilidades abre ocupando la pantalla, con controles propios de Minimizar,
Restaurar/Maximizar y Cerrar. Cerrar equivale a Cerrar sin guardar.
