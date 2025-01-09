Fecha: 2024-12-23 22:06
Tags: [[Visual Studio Code]] [[MSVC]] [[GIt]] [[Powershell]] [[Cmake]] [[C_C++]] [[HackRFOne]] 
<hr>

Una vez se han instalado todos los prerrequisitos, especialmente las librerías base (LibUSB, FFTW3, PThread) es momento de instalar la librería de la HackRF ONE, para ello se ha de clonar el repositorio oficial de la HackRF a través del siguiente comando:
`{powershel} git clone https://github.com/greatscottgadgets/hackrf.git`

una vez clonada la carpeta se ha de ir a la ruta `{powershell} cd hackrf/host` y crear la carpeta build con el comando `{powershell} mkdir build` y acceder a la carpeta con `{powershell} cd build`. Una vez nos encontramos en la respectiva carpeta para compilar los archivos se ha de ejecutar el siguiente comando: `{powershell} cmake ../ -G "Visual Studio 17 2022" -A x64 -DLIBUSB_LIBRARIES=... -DLIBUSB_INCLUDE_DIR=... -DFFTW_INCLUDES=... -DFFTW_LIBRARIES=... -DTHREADS_PTHREADS_INCLUDE_DIR=... -DTHREADS_PTHREADS_WIN32_LIBRARY=... -DCMAKE_INSTALL_PREFIX=...`

Se ha de especificar la ruta completa del IncludePATH, LibPATH y InstallPATH (en caso de querer organizar los archivos). El resumen de los comandos utilizados en este caso es el siguiente:
``` powershell
git clone https://github.com/greatscottgadgets/hackrf.git
cd hackrf/host
mkdir build
cd build
cmake ../ -G "Visual Studio 17 2022" -A x64 \
-DLIBUSB_LIBRARIES=C:/Manual_Install_Libraries/HackRF_One/Install/lib/libusb-1.0.lib \
-DLIBUSB_INCLUDE_DIR=C:/Manual_Install_Libraries/HackRF_One/Install/include/libusb-1.0/ \
-DFFTW_INCLUDES=C:/Manual_Install_Libraries/HackRF_One/Install/include/ \ 
-DFFTW_LIBRARIES=C:/Manual_Install_Libraries/HackRF_One/Install/lib/fftw3f.lib \
-DTHREADS_PTHREADS_INCLUDE_DIR=C:/Manual_Install_Libraries/HackRF_One/Install/include/ \
-DTHREADS_PTHREADS_WIN32_LIBRARY=C:/Manual_Install_Libraries/HackRF_One/Install/lib/pthreadVC2.lib \
-DCMAKE_INSTALL_PREFIX=C:/Manual_Install_Libraries/HackRF_One/Install




```

Una vez se ha generado la configuración de la compilación, se compilan a través del siguiente comando: `{powershell} cmake --build . --config Release`, en caso de haber especificado la ruta de instalación se ha de ejecutar el comando `{powershell} cmake --install . --config Release`, por ultimo es importante organizar correctamente los archivos .lib en su respectivo directorio lib en lugar bin donde se instala por defecto. Para mas detalle del procedimiento de instalación a través de CMake y las rutas de instalación con su respectiva configuración de las variables de entorno, revisar la nota [[FFTW3 (Windows)]]. 
# Verificación de instalación <hr>
Para verificar que la librería HackRF se instalo correctamente se pueden probar múltiples métodos, sin embargo el método mas directo es probar si los ejecutables HackRF_Info o HackRF_Sweep que se encuentran en el directorio BIN donde se instalaron los archivos o en la ruta `{powershell} \hackrf\host\build\hackrf-tools\src\Release` donde se compilaron.

En caso de querer ejecutar un código de prueba en c/c++, revisar el ejemplo realizado en [[FFTW3 (Windows)]] para configurar tanto MSVC y Visual Studio Code.
# Referencias <hr>
\[1] [Github de HackRF One](https://github.com/greatscottgadgets/hackrf)
\[2] [Documentación de instalación de la HackRF One](https://hackrf.readthedocs.io/en/latest/installing_hackrf_software.html)



