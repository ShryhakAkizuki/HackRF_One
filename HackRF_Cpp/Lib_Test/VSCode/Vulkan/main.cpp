#define GLFW_INCLUDE_VULKAN
#include <GLFW/glfw3.h>
#include <iostream>

int main() {
    // Inicializa GLFW
    if (!glfwInit()) {
        std::cerr << "Failed to initialize GLFW" << std::endl;
        return -1;
    }

    // Comprueba si Vulkan está soportado
    if (!glfwVulkanSupported()) {
        std::cerr << "GLFW: Vulkan not supported" << std::endl;
        glfwTerminate();
        return -1;
    }

    std::cout << "Vulkan is supported!" << std::endl;

    // Limpieza
    glfwTerminate();
    return 0;
}