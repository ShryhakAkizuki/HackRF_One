// ------------------------------ Constantes ------------------------------

const unsigned __int32 DEFAULT_SAMPLE_RATE_HZ = 20000000; 						// 20MHz default sample rate 
const unsigned __int32 FREQ_ONE_MHZ = 1000000;									// 1MHz Reference value
const unsigned __int32 FREQ_ONE_GHZ = 1000000000;								// 1GHz Reference Value
const unsigned __int32 DEFAULT_BASEBAND_FILTER_BANDWIDTH = 15000000; 			// 15MHz default 

const unsigned __int64 MAX_FREQ = 6000000000;									// Max Frequency - 6GHz 
const unsigned __int8 MAX_LNA = 40;												// Max LNA amplification
const unsigned __int8 MAX_VGA = 62;												// Max VGA amplification
const unsigned __int32 MAX_SAMPLES = 131072; 									// Max value

const unsigned __int32 MIN_FREQ = 1000000;										// Min Frequency - 1MHz

typedef enum {						// Modos de operacion de la HACKRF ONE
	TRANSCEIVER_MODE_OFF = 0,		
	TRANSCEIVER_MODE_RX  = 1,		// Recepcion
	TRANSCEIVER_MODE_TX  = 2,		// Transmision
	TRANSCEIVER_MODE_SS  = 3,
} transceiver_mode_t;

// ------------------------------ Librerias ------------------------------

#include <iostream>
#include <libhackrf/hackrf.h>
#include <complex>
#include <vector>
#include <mutex>
#include <windows.h>
#include <signal.h>
#include <SFML/Graphics.hpp>
#include <SFML/OpenGL.hpp>
#include <thread>

// ------------------------------ Funciones ------------------------------

int rx_callback(hackrf_transfer*);		// Funcion a ejecutar por cada llamada de la recepcion en POSIX
void handle_error(int, const char*);	// Funcion para comprobar Errores de llamados a funciones de LibHackRF
BOOL WINAPI sighandler(DWORD);			// Funcion para manejar las señales de terminacion	
void renderingThread(sf::RenderWindow*, std::vector<std::complex<float>>*, double);	// Hilo de renderizado
void initializeOpenGL();				// Funcion de inicializacion de OpenGL

// ------------------------------ Variables Globales ------------------------------
bool do_exit = false;											// Variable de terminacion

static hackrf_device* device = NULL;	// Dispositivo HackRF

const char* serial_number = NULL;								// Serial de la HackRF One -- Especifico: 0000000000000000458460c8387197a7
const unsigned __int32 sample_rate = DEFAULT_SAMPLE_RATE_HZ;	// Sample Rate: 2MHz - 20MHz in Hz
const unsigned __int8 lna_gain = 32;							// Low Noise Amplifier (LNA): 0-40dB, 8dB steps
const unsigned __int8 vga_gain = 24;							// Variable Gain Amplifier (LNA): 0-62dB, 2dB steps
const unsigned __int64 freq_hz = FREQ_ONE_MHZ*94.7;				// Frecuencia central: 1MHz - 6GHz in Hz
const unsigned __int32 samples = 131072;						// Cantidad de muestras a capturar
transceiver_mode_t transceiver_mode = TRANSCEIVER_MODE_RX;

std::mutex RX_Transfer; 								// Mutual Exclusion for RX transfer Sync between Threads
std::mutex Graph_Transfer; 								// Mutual Exclusion for Graph Transfer Sync between Threads


int main(){
// ------------------------------ Control de terminacion - CTRL+C ------------------------------

	// Configuracion de señales de terminacion
	if (SetConsoleCtrlHandler(sighandler, TRUE) == FALSE) {
		std::cerr<<"No se pudo configurar el manejador de señales"<<std::endl;
		return EXIT_FAILURE;
	}	
// ------------------------------ Variables Locales ------------------------------

	int result = 0;											// Variable tipo FLAG --- Status HACKRF
	
	std::vector<std::complex<float>> Transfer_Buffer;					// Complex Buffer obtaining Data from HackRF and used for Move semantics
	std::vector<std::complex<float>> Raw_Data (samples);				// Data from RX CallBack
	std::vector<std::complex<float>> Graph_Transfer_Buffer;				// Buffer to transfer the Raw Data to Graph Thread

// ------------------------------ Verificacion de Tolerancias ------------------------------

	// Sample Rate
	if (sample_rate < FREQ_ONE_MHZ*2 || sample_rate > DEFAULT_SAMPLE_RATE_HZ) {
		std::cerr	<<"Sample rate must be between: "
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
		std::cerr	<<"frequency must be between: "
					<< static_cast<float>(MIN_FREQ)/FREQ_ONE_MHZ
					<<"MHz and "
					<<static_cast<float>(MAX_FREQ)/FREQ_ONE_GHZ
					<<"GHz"
					<<std::endl;
		return EXIT_FAILURE;

	}

	// Cantidad de muestras
	if(samples > MAX_SAMPLES){
		std::cerr	<<"Samples must be less than: "
					<< static_cast<int>(MAX_SAMPLES)+1
					<<std::endl;
		return EXIT_FAILURE;

	}

// ------------------------------------------------ Configuracion de la HackRF -----------------------------------

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

	// Modo de recepcion --- start_rx empieza a recibir datos (Hardware y llama a rx_callback en un hilo aparte) POSIX Threads
	if (transceiver_mode == TRANSCEIVER_MODE_RX) {
		result = hackrf_set_vga_gain(device, vga_gain);
		handle_error(result, "No se pudo establecer la ganancia VGA");

		result = hackrf_set_lna_gain(device, lna_gain);
		handle_error(result, "No se pudo establecer la ganancia LNA");

		result = hackrf_start_rx(device, rx_callback, &Transfer_Buffer);
		handle_error(result, "No se pudo iniciar el streaming de recepcion");
	}


// ------------------------------------------------ Creacion de la ventana grafica - Thread -----------------------------------

  	// Crea la ventana de SFML
    sf::RenderWindow window (sf::VideoMode(1366,768), "Plotting");
    
    // Inicializa OpenGL
    initializeOpenGL();

	window.setPosition(sf::Vector2i(10, 50));   // Establece la posicion de la ventana
    window.setFramerateLimit(60);               // Limita el Framerate a 60 FPS
    window.setActive(false);                    // deactivate its OpenGL context

   // Genera el Hilo de ejecucion de la ventana
    std::thread thread(renderingThread, &window, &Graph_Transfer_Buffer, 0.5);


	// Ejecucion constante hasta que la HackRF deje de transmitir datos
	while ((hackrf_is_streaming(device) == HACKRF_TRUE) && do_exit == false) {	

        sf::Event event;	// Registro de Eventos de las ventanas

        while (window.pollEvent(event)){    						// Si ha ocurrido un evento revisa la cola de eventos
            if (event.type == sf::Event::Closed)    window.close(); // Si el evento es del tipo de cierre, cierra la ventana.
        }

// ------------------------------------------------ Transferencia de datos desde la HackRF -----------------------------------


	// Mientras el buffer de transferencia no este vacio
	if(!Transfer_Buffer.empty()){				
			
			{	// Block for Lock
				std::lock_guard<std::mutex> lock(RX_Transfer); 					// Bloqueo para usar el buffer de numeros complejos
				Raw_Data = std::move(Transfer_Buffer);
			}
	}


// ------------------------------------------------ Copia y Transferencia de datos para graficarlos -----------------------------------

	// Solo si el buffer de transferir datos a graficar esta vacio y existen datos a transferir
	if(Graph_Transfer_Buffer.empty() && !Raw_Data.empty()){		

			{	// Block for Lock
				std::lock_guard<std::mutex> lock(Graph_Transfer); 				// Bloqueo para usar el buffer de numeros complejos
				Graph_Transfer_Buffer.resize(samples);							// Redimensionar el buffer de datos complejos

				for(int i = 0; i<Raw_Data.size(); i++){							// Transferencia de los datos a un vector vacio
					Graph_Transfer_Buffer[i]=Raw_Data[i];
				}
			}
	}


	}
	
// ------------------------------------------------ Finalizacion de procesos  -----------------------------------

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

	return 0;
}

int rx_callback(hackrf_transfer* transfer){
	if(do_exit) return 0;													// Si se solicita terminar, no hacer nada
	
	// Apuntador al Buffer desde el main
	std::vector<std::complex<float>>* Buffer_Pointer = static_cast<std::vector<std::complex<float>>*>(transfer->rx_ctx);	
    std::lock_guard<std::mutex> lock(RX_Transfer); 							// Bloqueo para poder transferir el Buffer sin interrupciones
	
	(*Buffer_Pointer).resize(samples);										// Redimensionar el buffer de datos complejos

	for (uint32_t i = 0; i < samples; i++) {				// Recorrer todo el buffer disponible de la HackRF One
		// Guarda los Bytes en un buffer temporal de tipo complejo cuya finalidad sera tranasferir los datos a otro vector con Move Semantics
		(*Buffer_Pointer)[i] = std::complex<float>(static_cast<float>(transfer->buffer[2*i]), static_cast<float>(transfer->buffer[2*i+1]));

	}

	return 0;
}

void handle_error(int result, const char* message) {
	if (result != HACKRF_SUCCESS) {
		std::cerr<<message<<": "<<hackrf_error_name(static_cast<hackrf_error>(result))<<" ("<<result<<")"<<std::endl;
		exit(EXIT_FAILURE);
	}
}

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

void renderingThread(sf::RenderWindow *window, std::vector<std::complex<float>> *Graphics_Buffer, double Y_size){

    window->setActive(true);            // activate the window's context
    std::vector<sf::Vertex> vertices;   // Vector para almacenar los puntos (vertices) del plano cartesiano normalizado

    // Ciclo de ejecucion de la ventana
    while (window->isOpen()){

		if(!Graphics_Buffer->empty()){
			{	// Block for Lock
				std::lock_guard<std::mutex> lock(Graph_Transfer); 					// Bloqueo para usar el buffer de numeros complejos
				vertices.clear();													// Limpia el buffer de Vertices

				for (int i = 0; i < Graphics_Buffer->size(); i++) { 				// Transfiere y normaliza los datos para representarlos desde -1 a 1 en el Eje X y Eje Y (Normalizado en el Eje Y por Y_Size)
					vertices.push_back(sf::Vertex(sf::Vector2f(static_cast<double>(i)*2/(Graphics_Buffer->size()-1)-1,((*Graphics_Buffer)[i].real()*2/(255)-1)*Y_size), sf::Color::White));
				}
				
				Graphics_Buffer->clear();											// Limpia el buffer de datos para graficar
			}
		}

        // OpenGL
		glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);							// Limpia el buffer de OpenGL

        glEnableClientState(GL_VERTEX_ARRAY);
        glVertexPointer(2, GL_FLOAT, sizeof(sf::Vertex), &vertices[0].position);
        glDrawArrays(GL_LINE_STRIP, 0, vertices.size());
        glDisableClientState(GL_VERTEX_ARRAY);

        window->display();															// Muestra el contenido en la ventana
    }
}

// Function to initialize OpenGL settings
void initializeOpenGL() {
    glClearColor(0.0f, 0.0f, 0.0f, 1.0f); // Set background color (black)
    glMatrixMode(GL_PROJECTION);            // Use projection matrix
    glLoadIdentity();                       // Reset the projection matrix
    glOrtho(-1.0, 1.0, -1.0, 1.0, -1.0, 1.0); // Set orthographic projection (for 2D)
    glMatrixMode(GL_MODELVIEW);             // Switch to modelview matrix
}