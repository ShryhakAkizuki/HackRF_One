#include <pthread.h>
#include <iostream>

// Function to be executed by threads
void* threadFunction(void* arg) {
    int id = *reinterpret_cast<int*>(arg); // Cast void* back to int*
    std::cout << "Hello from thread " << id << "!" << std::endl;
    return nullptr; // No return value
}

int main() {
    const int threadCount = 5;
    pthread_t threads[threadCount];
    int threadArgs[threadCount];

    // Create threads
    for (int i = 0; i < threadCount; ++i) {
        threadArgs[i] = i; // Assign ID to each thread
        if (pthread_create(&threads[i], nullptr, threadFunction, &threadArgs[i]) != 0) {
            std::cerr << "Error creating thread " << i << std::endl;
        }
    }

    // Wait for threads to finish
    for (int i = 0; i < threadCount; ++i) {
        if (pthread_join(threads[i], nullptr) != 0) {
            std::cerr << "Error joining thread " << i << std::endl;
        }
    }

    std::cout << "All threads have completed!" << std::endl;

    return 0;
}