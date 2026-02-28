🖥️ Monitor de Procesos INTERACTIU Temps Real + Modbus TCP
Model de processos per a sistemes GNU/Linux que genera un graf interactiu PPID→PID. El sistema permet realitzar anàlisis jeràrquiques en temps real, detectar visualment la creació/eliminació de processos i exposar les dades mitjançant un servidor industrial Modbus TCP amb auto-detecció de versions.

Comenzando 🚀
Estas instrucciones te permitirán obtener una copia del proyecto en funcionamiento en tu máquina local para propósitos de desarrollo y pruebas.

Mira Despliegue para conocer cómo poner en marcha el sistema en entornos de monitorización.

Pre-requisitos 📋
Para ejecutar este monitor necesitas un sistema Linux (Kali Linux, Debian o Ubuntu) con Python 3.8+ y las cabeceras de interfaz gráfica para Tkinter.

Instalación 🔧
Sigue estos pasos para configurar tu entorno de desarrollo:

Obtener el código fuente:

Instalar las librerías de Python:
El proyecto requiere networkx para la lógica de grafos, matplotlib para el renderizado y pymodbus para la comunicación industrial.

Ejecutar la aplicación:
Lanza el script principal para abrir la interfaz interactiva.

Ejemplo de uso (Demo):
Al iniciar, pulsa el botón "Temps Real". Si abres una terminal nueva, verás aparecer un nodo en verde (🟢) en el graf. Si cierras un programa, el nodo cambiará a rojo (🔴) antes de desaparecer, permitiendo un seguimiento visual del ciclo de vida de los procesos.

Ejecutando las pruebas ⚙️
El sistema incluye un mecanismo de auto-detecció que verifica la integridad y compatibilidad de las librerías al arrancar.

Analice las pruebas end-to-end 🔩
Estas pruebas verifican que el motor de inferencia jeràrquica detecta correctamente la relación entre el proceso padre (PPID) y el hijo (PID).

Y las pruebas de estilo de codificación ⌨️
El código utiliza un bloque de detección progresiva para asegurar que el servidor Modbus funcione en múltiples versiones de pymodbus (desde la 3.0 hasta la 4.x+). Verifica la sintaxis con:

Despliegue 📦
Para desplegar el servidor Modbus de forma remota:

Configura la IP en el campo correspondiente (por defecto 0.0.0.0).

Pulsa "Iniciar TCP".

Asegúrate de que el puerto 5020 esté abierto en el firewall de tu sistema.

Construido con 🛠️
 - El lenguaje de programación principal utilizado para toda la lógica del sistema.

 - Motor de grafos dirigidos complejos para la jerarquía de procesos.

 - Utilizado para la visualización y el renderizado interactivo de los nodos.

 - Implementación del protocolo Modbus TCP Server.

Autores ✒️
Sergi Balsells - Trabajo Inicial, Lógica de Grafos y Servidor Modbus 

Licencia 📄
Este proyecto está bajo la Licencia MIT - mira el archivo  para detalles.

Expresiones de Gratitud 🎁
Comenta a otros sobre este proyecto si te ha servido para auditar procesos 📢.

Da las gracias públicamente 🤓.

¡Disfruta analizando la jerarquía de Linux! 
