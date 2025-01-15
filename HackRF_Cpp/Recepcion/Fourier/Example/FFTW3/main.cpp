#define _USE_MATH_DEFINES

#include <iostream>
#include <cmath>
#include <fstream>
#include <complex>
#include <vector>
#include <time.h>
#include <fftw3.h>

const int N = 131072;                   // Number of samples

int main(){
  clock_t start, end;                   // Variables to measure time.

  std::ofstream file;                   // File variable for control Output CSV
  
  float *samples = new float[N];        // Samples X axis
  float *square_signal = new float[N];  // Square signal (1Hz Period, 0.5 Duty Cycle)
  float pass = 1.0;                     // Variable for make 10 perior signal and the duty cycle

  fftwf_complex *out = new fftwf_complex[N];                                    // Output Fourier N/2 samples
  fftwf_plan p = fftwf_plan_dft_r2c_1d(N, square_signal, out, FFTW_ESTIMATE);   // Fourier plan FFTW

  file.open("Input_Signal.csv");        // Create the Input Signal file
 
  if (!file.is_open()){
      std::cout << "Error in creating file!" << std::endl;
      return 1;
  }
  file << "Samples" <<","<<"Amplitude"<<std::endl;  // CSV Header

  for(int k = 0; k < N; k++){                       // Create the Signal

    samples[k]=10*static_cast<float>(k)/(N-1);      // X axis from 0 to 10
    if(samples[k]>pass){                            // Variable for periods
      pass+=1;
    }

    if(samples[k]<pass-1.0/2.0){                    // Create the duty cycle
      square_signal[k]=1;
    }else{
      square_signal[k]=-1;
    }
    file << samples[k] <<","<<square_signal[k]<<std::endl;  // Put the data into the file
  }
    file.close();                                 // Close the file


  file.open("Output_Signal.csv");                 // Open Output signal file
  if (!file.is_open()){
      std::cout << "Error in creating file!" << std::endl;
      return 1;
  }
  file << "Frequency Samples" <<","<<"Real"<<","<<"Imag"<<std::endl;  // CSV Header

  start = clock();  // Reference time
  fftwf_execute(p); // Run FFTW calculation
  end = clock();    // End Time

  std::cout<<"Time Elapsed in unsigned: "<< static_cast<unsigned int>(end-start);

  for(int k = 0; k < N; k++){                       // Saving Fourier Data with Shift from (-N/2)/period to +(N/2)/period  
 
     if(k<N/2.0){
      file << ((k-N/2.0))/10.0 <<","<< out[N/2-k][0] <<","<<out[N/2-k][1]<<std::endl;
    }else{
      file << (k-N/2.0)/10.0 <<","<< out[k-N/2][0] <<","<<out[k-N/2][1]<<std::endl;
    }
    
  }
  file.close();                                 // Close the file
  fftwf_destroy_plan(p);                        // Delete Plan
  fftwf_free(out);                              // Free output signal
  delete[] samples;                             // Free samples signal
  delete[] square_signal;                       // Free square signal
  
  return 0;
}

