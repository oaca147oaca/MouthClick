# Rediseño visual de MouthClick

Aplicación de escritorio Windows en Python 3.11, Tkinter/ttk y OpenCV. El punto de entrada del ejecutable es `mouthclick_mvp_opticalflow.py`, según `release.ps1` y `MouthClick.spec`. También existen las variantes `mouthclick.py` y `cameramause.py`.

El repositorio estaba limpio antes de empezar. No hay WPF, XAML, ViewModels, diccionarios de recursos ni assets oficiales de marca. La interfaz y los callbacks estaban definidos directamente en cada script. La configuración persistente usa `profiles.json`; los controles de cámara, gestos, cursor y entradas usan OpenCV, MediaPipe, PyAutoGUI, pynput y APIs de Windows.

## Archivos

Modificados:
- `mouthclick_mvp_opticalflow.py`: pantalla de configuración, estilos de teclado/burbuja y badges en la imagen de cámara.
- `mouthclick.py`: pantalla de configuración.
- `cameramause.py`: pantalla de configuración.
- `.gitignore`: excluye los artefactos de verificación `.visual-build/`.

Nuevos:
- `mouthclick_ui.py`: paleta, tipografía, tarjetas redondeadas, campos, botones, opciones, layout adaptable, foco y estados.
- `verify_visual.py`: verificación aislada de UI, sin seguimiento, entradas ni persistencia real.
- `VISUAL_REDESIGN.md`: este informe.

## Diseño

Fondo casi negro, superficies navy, tarjetas con bordes discretos, texto claro, rojo Teletón en la acción principal. Identidad textual Teletón Labs sin inventar un logo. Las tarjetas pasan de dos columnas a una según el ancho y la escala de texto. Botón de inicio fijo fuera del scroll; foco visible, controles amplios y desplazamiento automático al navegar con Tab. El título conserva el comportamiento nativo de Windows y solicita chrome oscuro cuando el sistema lo admite.

Se conservaron comboboxes y checkboxes nativos para mantener su interacción por teclado; no se sustituyeron por sliders ni interruptores con otra semántica. No se agregaron animaciones continuas. Los estados de configuración, selección de punto, control activo y pausa incluyen texto explícito.

## Funcionalidad conservada

Callbacks originales de selección de perfil, inicio y cierre; valores, nombres y formatos persistentes; todas las acciones de boca/guiños; sensibilidad X/Y en la variante óptica; estabilización, zoom, autoclick, punto de control, cámara, teclado, accesos rápidos y atajos existentes. Los algoritmos, hooks, temporizadores, calibración, servicios de entrada, instalador y perfiles no se modificaron.

La vista de cámara conserva sus dimensiones y coordenadas; el badge se dibuja después de los cálculos. El teclado conserva los comandos y comportamiento de no activación de ventana. Se ajustó su geometría al tamaño solicitado por los controles y se corrigieron targets que sobresalían en la burbuja.

## Verificación

- Compilación Python antes de editar y después de cada fase, sin errores.
- PyInstaller del estado original completado, antes de integrar el rediseño en los scripts.
- Comparación de resultados y perfiles guardados contra las versiones de Git: tres variantes, perfil inicial y cambio de perfil.
- Comparación AST: todas las funciones y clases no visuales permanecen iguales.
- Nueve pruebas de layout: ventanas de 1080×740, 860×600 y 620×480, con escalas Tk equivalentes a 100%, 125% y 150%. Verifican botón de inicio visible, ancho de campos y desplazamiento al enfocar controles.
- Captura inspeccionada: `.visual-build/preview.png`.
- Repetir pruebas: `py -3.11 verify_visual.py`, desde la raíz del repositorio. Abre y cierra ventanas de prueba, usa cámaras y guardado simulados. No mueve el cursor.

La simulación de escala de Tk no sustituye una prueba física con cambios de DPI entre monitores de Windows. No se verificó una sesión clínica con cámara, gestos ni métodos de acceso alternativos. La apariencia de los controles nativos y su exposición a lectores de pantalla dependen de Tk/Windows.

## Límites y pendientes

Agregar un asset oficial cuando esté disponible. Validar con usuarios la navegación, el teclado flotante y el tamaño de controles en sus monitores y ayudas de acceso. La vista OpenCV conserva sus indicadores técnicos y su renderizador original; no se integró en una nueva ventana para evitar modificar seguimiento y coordenadas de selección. Los botones y campos conservan bordes nativos; las tarjetas sí tienen esquinas redondeadas.

Se mantuvo el comportamiento preexistente de cerrar la configuración: las variantes `mouthclick.py` y óptica pueden continuar hacia el control con sus valores actuales. Cambiar ese comportamiento requiere un cambio funcional independiente.

No se regeneró el instalador ni se modificaron los releases existentes. No se hicieron commits.

## Compilación final

PyInstaller completó el ejecutable final con 0 errores. Se comprobó que el ejecutable empaquetado abre la ventana MouthClick · Teletón Labs; el proceso de prueba se cerró sin iniciar el control. Ejecutable: `.visual-build/final/dist/MouthClick/MouthClick.exe`. Debe conservarse toda su carpeta, incluido `_internal`; contiene una copia de los perfiles existentes.

Ambas compilaciones registran los mismos 325 avisos de análisis de módulos de PyInstaller: 0 avisos nuevos y 0 eliminados. Incluyen dependencias opcionales o específicas de otras plataformas (`grp`, `pwd`, `posix`, `fcntl`, `termios`), símbolos de NumPy y módulos de pruebas de COM/MediaPipe recogidos por la configuración existente. No todos equivalen a fallos de ejecución. Listados completos: `.visual-build/baseline/work/MouthClick/warn-MouthClick.txt` y `.visual-build/final/work/MouthClick/warn-MouthClick.txt`.

## Ajuste de inicio y accesos flotantes

El teclado comienza oculto, incluso durante su construcción, para dejar libre la selección manual del punto de seguimiento. Se abre desde Teclado en la burbuja o con F9. La burbuja conserva las siete acciones existentes y ahora usa un panel navy redondeado, títulos descriptivos, targets amplios, hover, foco y acento rojo para Teclado. Se ubica inicialmente junto al borde derecho y limita su geometría a la pantalla. Puede moverse desde el encabezado y contraerse explícitamente.

Verificación aislada de ventanas: teclado oculto al inicio, burbuja visible con su ventana madre oculta, apertura/cierre del teclado desde el botón, siete targets dentro del panel y contracción correcta. Captura: `.visual-build/bubble-preview.png`. Compilación Python y `git diff --check` correctos. Este ajuste se aplica al código que abre `Abrir MouthClick.bat`; el ejecutable de la compilación anterior no se regeneró para este cambio.
