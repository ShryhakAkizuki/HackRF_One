#include <SFML/Graphics.hpp>
#include <SFML/OpenGL.hpp>
#include <vector>
#include <cmath>

// Function to plot a sine wave
void plotSineWave(std::vector<sf::Vertex>& vertices, float time) {
    vertices.clear();
    for (float x = -1; x <= 1; x += 0.0001) {
        float y = std::sin(x * 3.14159 * 2 + static_cast<float>(rand())/(RAND_MAX*2) + time);                            // Sine wave equation
        vertices.push_back(sf::Vertex(sf::Vector2f(x, y), sf::Color::Green));
    }
}

void renderingThread(sf::RenderWindow* window){

    
    window->setActive(true);            // activate the window's context
    std::vector<sf::Vertex> vertices;   // Vector to hold the plot data (points)
    sf::Clock clock;                    // Start the clock to update time for animation

    // the rendering loop
    while (window->isOpen()){
        
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);

        // Data to plot
        float time = clock.getElapsedTime().asSeconds();
        plotSineWave(vertices,time);

        // OpenGL
        glEnableClientState(GL_VERTEX_ARRAY);
        glVertexPointer(2, GL_FLOAT, sizeof(sf::Vertex), &vertices[0].position);
        glDrawArrays(GL_LINE_STRIP, 0, vertices.size());
        glDisableClientState(GL_VERTEX_ARRAY);

        window->display();
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



int main() {
    // Crea la ventana de SFML
    sf::RenderWindow window (sf::VideoMode(1366,768), "Plotting");
    
    // Initialize OpenGL
    initializeOpenGL();

    window.setPosition(sf::Vector2i(10, 50));   // Establece la posicion de la ventana
    // window.setFramerateLimit(60);               // Limita el Framerate a 60 FPS
    window.setActive(false);                    // deactivate its OpenGL context
    
    // launch the rendering thread
    sf::Thread thread(&renderingThread, &window);
    thread.launch();

    // Ciclo de ejecucion infinito hasta que se cierre la ventana
    while (window.isOpen()){

        // Constantemente verifica si se ha registrado un evento
        sf::Event event;

        while (window.pollEvent(event)){    // Si ha ocurrido un evento revisa la cola de eventos

            // Si el evento es del tipo de cierre, cierra la ventana.
            if (event.type == sf::Event::Closed)    window.close();
        }


    }



    return 0;
}
