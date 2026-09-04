<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
   <h1><img src="https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSwKp1bw03GMEH6TawkZwi6Zhl2oqgRewamLxsXhrH2Gw&s=10" width="40">ReconForense_video (version 1.0)</h1>
    Esta herramienta esta pensada para el análisis forense de videos, soportando los formatos a demanda. Tiene una interfaz interactiva que ayudara a la ejecución de las tareas como:<br>
<br>
* Análisis de autenticidad.<br>
* Detección de posibles manipulaciones.<br>
* Análisis cuadro por cuadro.<br>
* Identificación de frames duplicados<br>
* Extracción de fotogramas.<br>
* Análisis de artefactos.<br>
* Estabilización.<br>
* Corrección de iluminación.<br>
* Mejora de detalles.
* Detección visual de inconsistencias.<br>
* Comparación entre material original y procesado.<br>
* Superposición de video.<br>
* Comparación lado a lado.<br>
* Sustracción de cambios entre original y resultado.<br>
<br>
<img src="https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQcEMIi_JfBTrxIuN4GuDfbFAx4O1EvKtXTYcykS9L2dw&s=10" width="100"><img src="https://thumb.wikimedia.org/wikipedia/commons/thumb/8/82/Gnu-bash-logo.svg/1280px-Gnu-bash-logo.svg.png?utm_source=es.wikipedia.org&utm_campaign=index&utm_content=thumbnail" width="90"><br>
<br>
Recomendable que descargue el repositorio en la ruta /opt/
<p><strong>descargar el repositorio</strong></p>
<pre>sudo git clone https://github.com/Saifer10/ReconForense_Video.git</pre>
Por medio del archivo <strong>install_ReconForensics.sh</strong> se instalan las dependecias que requiere el programa
<p>Permisos de ejecución para el archivo install_ReconForensic.sh:</p>
<pre><code>chmod +x install_ReconForensic.sh</code></pre>
<p>Ejecución del archivo install_ReconForensic.sh:</p>
<pre><code>bash install_ReconForensic.sh</code></pre>
El archivo <strong>Install_ReconForensics</strong> debe instalar los siguientes dependencias<br>
<br>
    *  python3.<br> 
    *  python3-venv.<br>
    *  python3-tk.<br>
    *  python3-opencv.<br>
    *  python3-numpy.<br>
    *  python3-pil.<br>
    *  ffmpeg.<br>
    *  ediainfo.<br>
    *  libimage-exiftool-perl.<br>
    *  hashdeep.<br>
<br>
Una vez instalado las dependencias se otorga permisos a el archivo python <strong>ReconForensic_GUI_v1.py</strong>
<pre><code> chmod +x ReconForensic_GUI_v1.py</code></pre>
<p><strong>Ejecución del archivo ReconForensic_GUI_v1.py</strong>:</p>
<pre><code>Python3 ReconForensic_GUI_v1.py</code></pre>
<img src="Reconforensic_GUI_v1.png" width="800">
</body>
</html>
