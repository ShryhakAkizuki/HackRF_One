Fecha: 2024-12-28 14:54
Tags: [[Visual Studio Code]], [[MSVC]], [[HackRF One]], [[C_C++]]
<hr>

Para comenzar a adquirir datos a través de la radio, es fundamental realizar una serie de configuraciones que permitan captar la información deseada. Sin embargo, la radio opera dentro de ciertos rangos, por lo que es crucial definir previamente una serie de ***constantes*** que establecen los valores máximos, mínimos y de referencias necesarios para garantizar el funcionamiento de la radio. A continuación, se presentan las constantes definidas:
``` cpp
// 20MHz default sample rate
const unsigned __int32 DEFAULT_SAMPLE_RATE_HZ = 20000000;
// 1MHz Reference value
const unsigned __int32 FREQ_ONE_MHZ = 1000000;                                  
// 1GHz Reference Value
const unsigned __int32 FREQ_ONE_GHZ = 1000000000;                               
// 15MHz default
const unsigned __int32 DEFAULT_BASEBAND_FILTER_BANDWIDTH = 15000000;            

// Max Frequency - 6GHz
const unsigned __int64 MAX_FREQ = 6000000000;                                   
// Max LNA amplification
const unsigned __int8 MAX_LNA = 40;                                             
// Max VGA amplification
const unsigned __int8 MAX_VGA = 62;                                             
// Max value
const unsigned __int32 MAX_SAMPLES = 131072; 
  
// Min Frequency - 1MHz
const unsigned __int32 MIN_FREQ = 1000000;                                      
```

Las ***librerías*** que se implementaron para este fin son las siguientes:
``` cpp
#include <iostream>
#include <libhackrf/hackrf.h>
#include <complex>
#include <vector>
#include <mutex>
```

Con el fin de generar una cierta interfaz de usuario a futuro y/o establecer el modo de operación de la radio, se declararon las siguientes ***variables globales***:
``` cpp
// Dispositivo HackRF
static hackrf_device* device = NULL;    
// Serial de la HackRF One
const char* serial_number = NULL;
// Sample Rate: 2MHz - 20MHz in Hz
const unsigned __int32 sample_rate = DEFAULT_SAMPLE_RATE_HZ;
// Low Noise Amplifier (LNA): 0-40dB, 8dB steps
const unsigned __int8 lna_gain = 32;                            
// Variable Gain Amplifier (LNA): 0-62dB, 2dB steps
const unsigned __int8 vga_gain = 24;                            
// Frecuencia central: 1MHz - 6GHz in Hz
const unsigned __int64 freq_hz = FREQ_ONE_MHZ*94.7; 
// Cantidad de muestras a capturar
const unsigned __int32 samples = 131072;                        

// Mutual Exclusion for RX transfer Sync between Threads
std::mutex RX_Transfer;                                 
```

## Main()

Luego de declarar aquellas constantes y variables globales necesarias para ejecutar el programa, se declaran las ***variables locales*** dentro del programa principal. Primero se tiene una variable de tipo ***entero*** cuya función se centra en el control de ejecución de la librería ***LibHackRF***, por otro lado se declararon dos ***vectores*** de tipo ***complejo*** de los cuales uno de ellos funcionara como ***memoria compartida*** entre los ***Threads*** y se gestionara a través de ***Move Semantics***, mientras que el otro es gestionado únicamente por el programa principal, las variables declaradas son las siguientes:
``` cpp
// Variable tipo FLAG --- Status HACKRF
int result = 0;                                         

// Complex Buffer obtaining Data from HackRF and used for Move semantics
std::vector<std::complex<float>> Transfer_Buffer;       
// Data from RX CallBack
std::vector<std::complex<float>> Raw_Data (samples);    
```

La primera sección del programa principal verifica si los diferentes parámetros configurados por el usuario están dentro de los rangos de operación establecidos en las constantes, el código que realiza la comprobación de los parámetros es el siguiente:
``` cpp
// Sample Rate
if (sample_rate < FREQ_ONE_MHZ*2 || sample_rate > DEFAULT_SAMPLE_RATE_HZ) {
	std::cerr   <<"Sample rate must be between: "
				<< static_cast<float>(FREQ_ONE_MHZ*2)/FREQ_ONE_MHZ
				<<" and "
				<<static_cast<float>(DEFAULT_SAMPLE_RATE_HZ)/FREQ_ONE_MHZ
				<<"MHz"
				<<std::endl;

	return EXIT_FAILURE;
}

// Low Noise Amplifier
if (lna_gain % 8) {
	std::cerr<<"LNA gain must be a multiple of 8"<<std::endl;
	
	return EXIT_FAILURE;

}else if(lna_gain>MAX_LNA){
	std::cerr<<"LNA gain is high, must be less than: "<<MAX_LNA<<"dB"<<std::endl;

	return EXIT_FAILURE;

}
  
// Variable Gain Amplifier
if (vga_gain % 2) {
	std::cerr<<"VGA gain must be a multiple of 2"<<std::endl;
	
	return EXIT_FAILURE;

}else if(lna_gain>MAX_VGA){
	std::cerr<<"VGA gain is high, must be less than: "<<MAX_VGA<<"dB"<<std::endl;

	return EXIT_FAILURE;

}
  
// Frecuencia central
if(freq_hz > MAX_FREQ || freq_hz < MIN_FREQ){
	std::cerr   <<"frequency must be between: "
				<< static_cast<float>(MIN_FREQ)/FREQ_ONE_MHZ
				<<"MHz and "
				<<static_cast<float>(MAX_FREQ)/FREQ_ONE_GHZ
				<<"GHz"
				<<std::endl;

	return EXIT_FAILURE;

}

// Cantidad de muestras
if(samples > MAX_SAMPLES){
	std::cerr   <<"Samples must be less than: "
				<< static_cast<int>(MAX_SAMPLES)+1
				<<std::endl;

	return EXIT_FAILURE;

}
```

Luego de comprobar si los valores configurados están dentro del rango establecido, se configuro estos parámetros en la HackRF One a través de la librería **LibHackRF**, sin embargo para evitar ser redundante con la gestión de los errores, se realizo una función la cual comprueba si el resultado fue erróneo y en dado caso generar un mensaje de error, además de terminar la ejecución del programa, el código de la función es el siguiente:
``` cpp
void handle_error(int result, const char* message) {
	if (result != HACKRF_SUCCESS) {
		std::cerr<<message<<": "
		<<hackrf_error_name(static_cast<hackrf_error>(result))
		<<" ("<<result<<")"<<std::endl;

		exit(EXIT_FAILURE);
	}
}
```

El código que configura los respectivos parámetros de la HackRF One es el siguiente:
``` cpp
// Inicializa la libreria
result = hackrf_init();
handle_error(result, "No se pudo inicializar la libreria: ");

// Reconoce el dispositivo por numero de serial o NULL (Por defecto)
result = hackrf_open_by_serial(serial_number, &device);
handle_error(result, "No se pudo reconocer el dispositivo: ");

// Establece el Sampling Rate
result = hackrf_set_sample_rate_manual(device, sample_rate, 1);
handle_error(result, "No se pudo establecer la tasa de muestreo: ");

// Establecer la frecuencia cental
result = hackrf_set_freq(device, freq_hz);
handle_error(result, "No se pudo establecer la frecuencia: ");

// Establece la amplificacion del amplificador de ganancia variable
result = hackrf_set_vga_gain(device, vga_gain);
handle_error(result, "No se pudo establecer la ganancia VGA");

// Estblece la amplificacion del amplificador de bajo ruido
result = hackrf_set_lna_gain(device, lna_gain);
handle_error(result, "No se pudo establecer la ganancia LNA");
```

Para realizar la adquisición de datos es importante entender que la función **hackrf_start_rx** genera un **Thread** el cual realiza la adquisición de los datos del hardware y los gestiona la librería **LibHackRF** a través de una estructura de datos llamada **hackrf_transfer**, adicionalmente el **Thread** llama constantemente a una función definida por el usuario, en este caso la función que queremos ejecutar tiene como objetivo guardar las muestras I/Q de la **HackRF** en el **vector** Transfer_Buffer, tal y como se observa en el siguiente código:
``` cpp
int rx_callback(hackrf_transfer* transfer){
// Apuntador al Buffer desde el main
std::vector<std::complex<float>>* Buffer_Pointer = static_cast<std::vector<std::complex<float>>*>(transfer->rx_ctx);

// Bloqueo para poder transferir el Buffer sin interrupciones
std::lock_guard<std::mutex> lock(RX_Transfer);

// Redimensionar el buffer de datos complejos
(*Buffer_Pointer).resize(samples);                                      

// Recorrer todo el buffer disponible de la HackRF One
for (uint32_t i = 0; i < samples; i++) {                

	// Guarda los Bytes en un buffer temporal de tipo complejo cuya finalidad sera tranasferir los datos a otro vector con Move Semantics
	(*Buffer_Pointer)[i] = std::complex<float>(static_cast<float>(transfer->buffer[2*i]), static_cast<float>(transfer->buffer[2*i+1]));

	return 0;
}
```

Es importante remarcar que el buffer se llama a través de un puntero almacenado en el argumento **rx_ctx** de la función **hackrf_start_rx**, por lo tanto la llamada a esta función se puede observar en el siguiente código:
``` cpp
result = hackrf_start_rx(device, rx_callback, &Transfer_Buffer);
handle_error(result, "No se pudo iniciar el streaming de recepcion");
```

Con esto, se ha creado el **Thread** encargado de recolectar los datos cada vez que la radio los pone a disposición. Sin embargo, para evitar sobrecargar esta función con tareas de procesamiento, se decidió transferir la información al **Thread** principal (función main).
En este flujo, el vector **Transfer_Buffer** siempre contiene los datos más recientes captados por la HackRF One, mientras que el vector **Raw_Data** se encarga de procesar esta información a medida que se necesita.

Para optimizar este procedimiento, se implementaron **move semantics**, que permiten reasignar las direcciones de memoria entre los vectores. Esto garantiza que el vector **Transfer_Buffer** quede vacío después de transferir los datos, optimizando el uso de recursos. Para llevar a cabo esta operación de manera segura, se utiliza un condicional que verifica si **Transfer_Buffer** no está vacío antes de realizar la transferencia. El siguiente código ilustra este procedimiento:
``` cpp
// Verificar si el Buffer esta vacio
if(!Transfer_Buffer.empty()){               

	{   // Bloqueo para usar el buffer de numeros complejos
		std::lock_guard<std::mutex> lock(RX_Transfer);
		Raw_Data = std::move(Transfer_Buffer);
	}
}
```

A través de esto ya se pueden procesar los datos en la función principal, mientras que se adquieren los datos de la radio lo mas rápido posible, un diagrama que expone este flujo de la información en la memoria es el siguiente:
![[RX_Block_Diagram.png]]
# Referencias <hr>
\[1] [Archivo fuente - HackRF_Sweep.C](https://github.com/greatscottgadgets/hackrf/blob/master/host/hackrf-tools/src/hackrf_sweep.c)
\[2] [Archivo fuente - HackRF Transfer.C](https://github.com/greatscottgadgets/hackrf/blob/master/host/hackrf-tools/src/hackrf_transfer.c)
\[3] [Archivo fuente - Librería LibHackRF](https://github.com/greatscottgadgets/hackrf/blob/master/host/libhackrf/src/hackrf.c)
\[4] [HackRF Tools - Documentación](https://hackrf.readthedocs.io/en/latest/hackrf_tools.html)
\[5] [HackRF Especificaciones](https://hackrf.readthedocs.io/en/latest/hackrf_one.html)




