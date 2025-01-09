Fecha: 2024-12-22 20:37
Tags: [[C_C++]] [[Cmake]] [[MSVC]] [[Powershell]] [[Visual Studio Code]]
<hr>

- #1 - Descargar los archivos FFTW de su pagina oficial (No realizarlo desde Github dado que no están las versiones RELEASE):  https://www.fftw.org/download.html

- #2 - Crear una carpeta donde se extraerán los archivos necesarios (En este caso concreto HackRF_One)

- #3 - Extraer la carpeta fftw-3.3.10

- #4 - Abrir POWERSHELL de windows

- #5 - Entrar a la ruta donde se extrajeron los archivos: `{powershell} cd ....../HackRF_One/fftw-3.3.10`

- #6 -  Crear un nuevo directorio para compilar los archivos (default: build):`{powershell} mkdir build`

- #7 - Ingresar a este nuevo directorio: `{powershell} cd build`

- #8 - Generar la configuración necesaria para compilar los archivos de FFTW en la versión de Microsoft Visual Studio xxxx (MSVC), en este caso concreto se usa MSVC 2022. 
	***Importante***, Habilitar la precision single en lugar de double que esta por defecto:
	`{powershell} cmake ../ -G "Visual Studio 17 2022" -A x64  -DENABLE_FLOAT=ON -DENABLE_SSE=ON`
	
- #9 - Compilar los archivos, en la versión Release: `{powershell} cmake --build . --config Release`

De formar resumida los comandos en powershell para compilar la librería FFTW en modo precisión single son los siguientes:

``` powershell
cd ....../HackRF_One/fftw-3.3.10
mkdir build
cd build
cmake ../ -G "Visual Studio 17 2022" -A x64  -DENABLE_FLOAT=ON -DENABLE_SSE=ON
cmake --build . --config Release
```

Una vez se tienen los archivos los directorios para FFTW3F (FFTW3 Float) son los siguientes:
- Include: `{powershell} fftw-3.3.10/api`
- Lib: `{powershell} fftw-3.3.10/build/release`
- Bin (DLL): `{powershell} fftw-3.3.10/build/release`

# Organizacion de ficheros (Install)(Opcional) <hr>

En dado caso que se busque un mayor nivel de organización con los archivos del proyecto, se puede optar por "Instalar" los ficheros importantes a una carpeta y realizar este proceso con las demás librerías, para esto es necesario modificar ligeramente la linea de configuración de compilación de tal manera que indique la ruta donde se instalaran estos ficheros, en este caso se busca instalar los archivos en la carpeta ***HackRF_One/Install***, por ende la configuración de compilación resultante es: 

`{powershell} cmake ../ -G "Visual Studio 17 2022" -A x64  -DENABLE_FLOAT=ON -DENABLE_SSE=ON -DCMAKE_INSTALL_PREFIX=../../Install`

Luego de compilar los archivos con `{powershell} cmake --build . --config Release`, se han de instalar con el comando `{powershell} cmake --install . --config Release`, por lo cual los comandos para compilar e instalar la librería FFTW3F en un directorio son los siguientes:

``` powershell
cd ....../HackRF_One/fftw-3.3.10
mkdir build
cd build
cmake ../ -G "Visual Studio 17 2022" -A x64  -DENABLE_FLOAT=ON -DENABLE_SSE=ON  -DCMAKE_INSTALL_PREFIX=../../Install
cmake --build . --config Release
cmake --install . --config Release
```


# Verificación de la instalación <hr>

Para verificar que la librería FFTW3 se instalo correctamente se pueden probar múltiples métodos
### #1 - Bench.EXE

Existe un ejecutable nombrado Bench.exe el cual es generado al compilar la librería FFTW3, este se encuentra en la ruta `{powershell} HackRF_One/fftw-3.3.10/build/release`, por lo cual se puede probar a través del siguiente comando en powershell: `{powershell} bench.exe -opatient 64 128 256 512 1024 2048 4096`
### #2 - MSVC --- Proyecto de prueba

Para implementar la librería en MSVC es importante que una vez generado el proyecto, se configuren los directorios tanto del compilador como del linker ***del proyecto*** (Tener en cuenta que para incluir múltiples ubicaciones o nombres se separan por ; en MSVC), por ende se realizan las siguientes configuraciones:

- C/C++: Dirección de inclusión adicionales ---> INCLUDE PATH`{powershell} HackRF_One/Install/Include` o `{powershell} fftw-3.3.10/api`

- Vinculador->Entrada: Dependencias adicionales ---> LIB NAME `{powershell} fftw3f.lib`

- VInculador -> General: Directorios de bibliotecas adicionales ---> LIB PATH `{powershell} HackRF_One/Install/Lib` o `{powershell} fftw-3.3.10/build/release`

Con estas 3 opciones ya es posible compilar el proyecto, sin embargo para poder ejecutarlo correctamente es importante que las librerías dinámicas (DLL) se encuentren en el directorio del ejecutable, por ende es posible incluir una opción adicional en MSVC para copiar automáticamente los DLL a la carpeta del ejecutable de la siguiente manera:

- Eventos de compilación -> Evento posterior a la compilación: `{powershell} xcopy /d /y "HackRF_One\Install\bin\*.dll" "$(TargetDir)"`

### #3 - Variables de Entorno (Opcional)

Para poder compilar correctamente el código a través de Visual Studio Code utilizando la extensión C/C++ de Microsoft y facilitar la configuración en MSVC, es importante modificar las variables de entorno del sistema de la siguiente manera:

- Path: `{powershell} HackRF_One/Install/bin`
- lIB: `{powershell} HackRF_One/Install/lib`
- lIBPATH: `{powershell} HackRF_One/Install/lib`
- INCLUDE: `{powershell} HackRF_One/Install/include`

Esto incluye ventajas como en MSVC evitar incluir la ruta de las carpetas completa, sino utilizar directamente las variables de entorno de la siguiente manera:


- C/C++: Dirección de inclusión adicionales ---> INCLUDE PATH`{powershell} $(INCLUDE)`

- Vinculador->Entrada: Dependencias adicionales ---> LIB NAME `{powershell} fftw3f.lib`

- Vinculador -> General: Directorios de bibliotecas adicionales ---> LIB PATH `{powershell} $(LIB)`

Al tener los DLL en el PATH del sistema es posible evitar copiar los archivos .DLL a la carpeta donde se compila el ejecutable del programa

### #4 - Visual Studio Code - C/C++ --- Proyecto Prueba (Opcional)

para poder compilar y ejecutar a través de Visual Studio code, es importante abrir la aplicación a través del `Developer Command Prompt for VS 2022` o `x64 Native Tools Command Prompt for VS 2022` a través del comando `{powershell} code.`, Luego es importante poder configurar los archivos tasks.json y c_cpp_properties.json con el fin de configurar correctamente la compilación, en caso que no se cuente con estos archivos, al ejecutar la compilación de la extensión C/C++ se generan automáticamente.

- c_cpp_properties.json:  incluir la ruta del compilador a través de la siguiente linea:
	`{json} "compilerPath": COMPILERPATH` en este caso concreto la ruta es:
	`{json} "compilerPath": "C:/Program Files/Microsoft Visual Studio/2022/Community/VC/Tools/MSVC/14.42.34433/bin/Hostx64/x64/cl.exe"`
- tasks.json:  Incluir la librería a compilar al final de los argumentos:
	`{json} "args" : [....., "fftw3f.lib"]`

Con estas modificaciones es posible compilar el código.
# Referencias <hr>

\[1] [Pagina para descargar FFTW fuente]( https://www.fftw.org/download.html)
\[2] [Indicacion del Bench.exe](https://www.fftw.org/install/windows.html)
\[3] [VIdeo Guia de instalacion para windows de FFTW3](https://youtu.be/0qQm5AGB_18?si=QsT1msQpnnVUXFYA)

