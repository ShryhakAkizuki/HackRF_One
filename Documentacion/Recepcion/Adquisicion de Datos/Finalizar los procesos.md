Fecha: 2024-12-29 11:24
Tags: [[Visual Studio Code]], [[MSVC]], [[HackRF One]], [[C_C++]]
<hr>
Es importante poder finalizar y cerrar las librerías en lugar de forzar el cierre de las mismas, dado que actualmente la aplicación es principalmente de tipo consola, la forma mas usual de terminar el proceso es a través del comando **CTRL+C**, por ende se implementara control de señales para terminar este proceso correctamente.

Primero es importante tener una variable global de control, en este caso se definió la siguiente variable: `{cpp} bool do_exit = false;`.

Dado que se van a gestionar un tipo de funciones de control especificas para Windows, es importante importar las siguientes librerías nativas:
``` cpp
#include <windows.h>
#include <signal.h>
```

La función de control que gestiona el comando **CTRL+C** tiene como objetivo principal poner la variable de control en **True**, por ende el código que realiza eso es el siguiente:
``` cpp
BOOL WINAPI sighandler(DWORD signum){
	//Si el comando es CTRL+C
	if (CTRL_C_EVENT == signum || CTRL_BREAK_EVENT == signum) {
		std::cerr<<"CTRL+C"<<std::endl;
		// Asignar True a la variable de control
		do_exit = true;
		
		return TRUE;
	}
	return FALSE;
}
```

Una vez definida la señal de control, es importante configurar al sistema de señales de Windows por ende al principio de la función main se declaran las siguientes líneas de código:
``` cpp
// Configuracion de señales de terminacion
if (SetConsoleCtrlHandler(sighandler, TRUE) == FALSE) {
	std::cerr<<"No se pudo configurar el manejador de señales"<<std::endl;
	
	return EXIT_FAILURE;
}
```

Una vez realizado esto, el comando **CTRL+C** no finaliza el programa sino que modifica la variable global **do_exit** permitiendo empezar el proceso de finalización. Primero se modifica ligeramente la funcion **rx_callback** con el fin de que si esta variable es verdadera no ejecute nada a través de la siguiente linea de código `{cpp} if(do_exit) return 0;`. Esto evitara que se realice alguna transferencia de datos desde la librería al programa principal. 

Por ultimo para terminar los procesos se llaman a las respectivas funciones de la librería **LibHackRF** tal y como se muestra en el siguiente código:
``` cpp
result = hackrf_is_streaming(device);
if (do_exit) {
	std::cerr<<"Terminando el proceso"<<std::endl;
} else {
	handle_error(result, "La HackRF esta transmitiendo datos ");
}

if (device != NULL) {
	result = hackrf_stop_rx(device);
	handle_error(result, "No se pudo detener la recepcion");
	std::cerr<<"Recepcion detenida"<<std::endl;

	result = hackrf_close(device);
	handle_error(result, "No se pudo cerrar el dispositivo");
	std::cerr<<"Dispositivo cerrado"<<std::endl;

	hackrf_exit();
	std::cerr<<"Libreria cerrada"<<std::endl;
}

std::cerr<<"Proceso finalizado"<<std::endl;
```

# Referencias <hr>
\[1] [Archivo fuente - HackRF_Sweep.C](https://github.com/greatscottgadgets/hackrf/blob/master/host/hackrf-tools/src/hackrf_sweep.c)
\[2] [Archivo fuente - HackRF Transfer.C](https://github.com/greatscottgadgets/hackrf/blob/master/host/hackrf-tools/src/hackrf_transfer.c)
\[3] [Control de señales en C++](https://www.geeksforgeeks.org/signal-handling-in-cpp/)


