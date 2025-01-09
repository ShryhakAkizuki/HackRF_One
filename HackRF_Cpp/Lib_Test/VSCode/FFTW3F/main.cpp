
#include <stdio.h>
#include <math.h>
#include <fftw3.h>
#include <time.h>
#include <stdlib.h>

#define M_PI 3.14159265358979323846

int main() {
    const int N = 1024; // Size of the FFT
    float* in;
    fftwf_complex* out;
    fftwf_plan p;

    out = new fftwf_complex[N];
    in = new float[N];
    p = fftwf_plan_dft_r2c_1d(N, in, out, FFTW_ESTIMATE);

    float tiempo[N];
    int frecuencia = pow(2,8);
    float f_axis[N];

    // Initialize input data with a sine wave
    for (int i = 0; i < N; i++) {
        tiempo[i] = 1 *i / N;      // 1 segundo dividido en N partes
        in[i] = 5 + sin(2 * M_PI * frecuencia * tiempo[i]);
        f_axis[i] = -N/2+i;
        // Sine wave with phase drift and slight frequency modulation
        double phase_drift = 0.05 * sin(2 * M_PI * 0.1 * tiempo[i]); // Low-frequency phase drift
        double freq_modulation = frecuencia + 0.5 * sin(2 * M_PI * 0.2 * tiempo[i]); // Frequency modulation

        // Generate the signal
        in[i] = 10 * sin(2 * M_PI * freq_modulation * tiempo[i] + phase_drift);

        // Add random noise
        double noise = 0.05 * ((double)rand() / RAND_MAX - 0.5) * 2; // Uniform noise in [-noise_level, noise_level]
        in[i] += noise;
 
    }

    // Create a plan for the FFT

    // Execute the plan
    fftwf_execute(p);

    // Print the output
    printf("FFT Output:\n");
    for (int i = 0; i < N / 2 + 1; i++) {
        printf("out[%d] = %.3f + %.3fi\n", i, out[i][0], out[i][1]);
    }

    // Clean up
    fftwf_destroy_plan(p);
    fftwf_free(out);
    delete in;

    return 0;
}