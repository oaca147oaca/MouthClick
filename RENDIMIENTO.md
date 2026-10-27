# Revisión de uso prolongado y encuadre

## Cambios

- Captura en un hilo que conserva solamente el cuadro más reciente. Un consumidor
  lento descarta cuadros antiguos en lugar de acumular demora. Al cerrar se detiene
  el hilo y se libera la cámara.
- Cola de atajos limitada a 64 eventos; las teclas ajenas a los atajos no se encolan.
  Si se llena, se reemplaza el evento más antiguo para conservar el más reciente.
- La guía de posición dibuja como máximo 10 veces por segundo y conserva una sola
  imagen de Tk. No escribe fotos ni video; cerrar la guía elimina esa imagen.
- La primera sesión requiere guardar desde el menú (`setup_complete`). Un perfil
  incluido de fábrica sin esa marca ya no evita la configuración inicial.

## Comprobación sintética

`py -3.11 verify_runtime_soak.py`: cámara simulada 640×480, MediaPipe real sobre
cuadros negros y guía de Tk oculta; consumidor con demora añadida. Sin cámara
real, rostro real, control del mouse ni escritura de imágenes.

En la ejecución de dos minutos se procesaron 3.533 cuadros. Entre los segundos
20 y 120, la memoria privada pasó de 523,55 a 523,48 MiB y el conjunto residente
de 126,64 a 126,75 MiB. Tk mantuvo cinco imágenes (cuatro internas y una de la guía).
La captura se detuvo correctamente al cerrar.

Esto descarta crecimiento sostenido en ese recorrido de prueba, pero no demuestra
que se haya resuelto la lentitud observada por la persona: todavía corresponde
probar con su cámara, su rostro y varios minutos de uso en su computadora.

## Guía de posición

El óvalo se pone verde según centro, tamaño aparente de la cara, inclinación
lateral y visibilidad geométrica de los ojos. Es una heurística de encuadre, no
una medición precisa del ángulo vertical ni una garantía de detectar guiños.
Si la cámara queda baja, hay que elevarla hacia la altura de los ojos y luego
recalibrar con el rostro relajado. La guía incluye un botón para ello.

No se generó un instalador nuevo con estos cambios.
