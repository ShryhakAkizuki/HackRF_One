Fecha: 2024-12-23 20:40
Tags: [[C_C++]] [[Visual Studio Code]] [[MSVC]] [[Powershell]] [[GIt]] 
<hr>

Para poder comunicarse con el sistema la HacRF ONE hace uso de la librería libusb que permite la comunicación a través de los puertos USB, para su instalación primero se ha de clonar el repositorio de LIBUSB a través del comando `{powershell} git clone https://github.com/libusb/libusb.git`

Una vez se ha obtenido el repositorio de github, se busca la ruta /libusb/msvc de tal manera que se abre la solución de MSVC llamada libusb.sln. Luego se ha de configurar MSVC en la versión Release de x64 y compilar la solución completa.

Esto compila los archivos en la ruta `{powershell} /libusb/build/v143/x64/release/` por lo cual se tienen las siguientes rutas:
- Include: `{powershell} /libusb/libusb`
- Lib: `{powershell} /libusb/build/v143/x64/release/lib`
- Bin (DLL): `{powershell} /libusb/build/v143/x64/release/dll`

De igual manera como se explica en [[FFTW3 (Windows)]], se creo una carpeta con el fin de organizar los ficheros y acomodar las variables de entorno, por ende es recomendable mover los ficheros .lib, .h y .dll a sus respectivos PATH.
# Verificación de instalación <hr>
Para verificar que los archivos estén correctamente instalados y se busque ejecutar un código de prueba en c/c++, revisar el ejemplo realizado en [[FFTW3 (Windows)]].

# Referencias <hr>
\[1] [Github LibUSB](https://github.com/libusb/libusb)
\[2] [Instrucciones especificas para windows](https://github.com/libusb/libusb/blob/master/INSTALL_WIN.txt)


