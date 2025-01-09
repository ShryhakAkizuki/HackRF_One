const float M_PI = 3.14159265358979323846;
const int samples = 1024;

#include <fftw3.h>
#include <math.h>
#include <stdlib.h>
#include <iostream>

int main() {
	float* in;
	fftwf_complex* out;
	fftwf_plan plan;

	out = new fftwf_complex[samples];	
	in = new float[samples];
	plan = fftwf_plan_dft_r2c_1d(samples, in, out, FFTW_ESTIMATE);

	float tiempo[samples];
	int frecuencia = pow(2, 8);
	float f_axis[samples];

	for (int i = 0; i < samples; i++) {
		tiempo[i] = 1 * i / static_cast<float>(samples);
		f_axis[i] = -samples / 2 + i;

		double phase_drift = 0.05 * sin(2 * M_PI * 0.1 * tiempo[i]);
		double freq_modulation = frecuencia + 0.5 * sin(2 * M_PI * 0.2 * tiempo[i]);

		in[i] = 10 * sin(2 * M_PI * freq_modulation * tiempo[i] + phase_drift);
		
		double noise = 0.05 * static_cast<double>(rand() / RAND_MAX - 0.5)*2;
		in[i] += noise;
	}

	fftwf_execute(plan);	

	std::cout << "FFT Output:" << std::endl;
	for (int i = 0; i < samples / 2; i++) {
		std::cout << "Out ["<<i<<"] = "<< out[i][0]<<" + "<< out[i][1] <<"i" << std::endl;
	}

	fftwf_destroy_plan(plan);
	fftwf_free(out);
	delete in;

	return 0;
}