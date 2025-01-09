Fecha: 2024-12-23 14:24
Tags: [[C_C++]] [[Visual Studio Code]] [[MSVC]] [[Powershell]]
<hr>

Pthreads es una librería para poder ejecutar los programas a través de subprocesos, generalmente se conoce como ***POSIX Threads*** y para implementarlo en este proyecto en Windows es necesario obtener los ficheros compilados, esto se puede hacer a través del explorador de archivos haciendo uso del protocolo FTP con el siguiente enlace: ftp://sourceware.org/pub/pthreads-win32/dll-latest.

Una vez se hallan copiado los archivos, las rutas son las siguientes:
- Include: `{powershell} pthreads/include`
- Lib: `{powershell} pthreads/lib/x64`
- Bin (DLL): `{powershell} pthreads/dll/x64`

De igual manera como se explica en [[FFTW3 (Windows)]], se creo una carpeta con el fin de organizar los ficheros y acomodar las variables de entorno, por ende es recomendable mover los ficheros .lib, .h y .dll a sus respectivos PATH.

Adicionalmente es importante instalar los Microsoft Visual C++ Redistributable de la siguiente pagina: https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist?view=msvc-170, especialmente la versión ***Visual Studio 2010 (VC++ 10.0) SP1 (no longer supported)*** 

# Verificación de instalación <hr>
Para verificar que los archivos estén correctamente instalados y se busque ejecutar un código de prueba en c/c++, revisar el ejemplo realizado en [[FFTW3 (Windows)]].

## Posible error de compilación --- Timespec
Dado que estamos usando el compilador MSVC es posible que por defecto el incluya librerías como time.h incluso si estas no fueron especificadas, por ende la estructura TIMESPEC puede llegar a ser redefinida y provocar problemas de compilación. Para evitar esto una posible solución es comentar las siguientes líneas de código en ***pthread.h***.
```c
#if !defined(HAVE_STRUCT_TIMESPEC)
#define HAVE_STRUCT_TIMESPEC
#if !defined(_TIMESPEC_DEFINED)
#define _TIMESPEC_DEFINED

struct timespec {
        time_t tv_sec;
        long tv_nsec;
};

#endif /* _TIMESPEC_DEFINED */
#endif /* HAVE_STRUCT_TIMESPEC */
```


# Referencias <hr>
\[1] [Pagina principal de PThreads](https://sourceware.org/pthreads-win32/)
\[2] [Microsoft Visual C++ Redistributable]( https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist?view=msvc-170)
