#define _USE_MATH_DEFINES

#include <iostream>
#include <cmath>
#include <fstream>
#include <complex.h>

const int N = 1024;

int main(){
  std::ofstream file;     // File variable for control Output CSV
  
  float samples[N];       // Samples X axis
  float square_signal[N]; // Square signal (1Hz Period, 0.5 Duty Cycle)
  float pass = 1.0;       // Variable for make 10 perior signal and the duty cycle

  file.open("Input_Signal.csv");  // Create the Input Signal file
 
  if (!file.is_open()){
      std::cout << "Error in creating file!" << std::endl;
      return 1;
  }
  file << "Samples" <<","<<"Amplitude"<<std::endl;  // CSV Header

  for(int k = 0; k < N; k++){                   // Create the Signal

    samples[k]=10*static_cast<float>(k)/(N-1);  // X axis from 0 to 10
    if(samples[k]>pass){                        // Variable for periods
      pass+=1;
    }

    if(samples[k]<pass-1.0/2.0){                // Create the duty cycle
      square_signal[k]=1;
    }else{
      square_signal[k]=-1;
    }
    file << samples[k] <<","<<square_signal[k]<<std::endl;  // Put the data into the file
  }
    file.close();                                 // Close the file

    std::complex<float> Fourier[N];               // Create Fourier complex array

  file.open("Output_Signal.csv");                 // Open Output signal file
  if (!file.is_open()){
      std::cout << "Error in creating file!" << std::endl;
      return 1;
  }
  file << "Frequency Samples" <<","<<"Real"<<","<<"Imag"<<std::endl;  // CSV Header



















  // for(int k = 0; k < N; k++){                       // Calculate DFT through definition 
  //   for(int j = 0; j < N; j++){
  //     // Fourier[k]+=square_signal[j]*std::complex<float>(cos(-2*M_PI*k*j/(N-1)),sin(-2*M_PI*k*j/(N-1)));
  //     Fourier[k]+=square_signal[j]*std::exp(std::complex <float>(0,-2*M_PI*k*j/(N-1)));
  //   }
  //   Fourier[k]/=N;  // Normalization
  // }

  // for(int k = 0; k < N; k++){                       // Saving Fourier Data with Shift from (-N/2)/period to +(N/2)/period  
 
  //    if(k<N/2.0){
  //     file << ((k-N/2.0)+1)/10.0 <<","<< Fourier[k+N/2].real() <<","<<Fourier[k+N/2].imag()<<std::endl;
  //   }else{
  //     file << (k-N/2.0)/10.0 <<","<< Fourier[k-N/2].real() <<","<<Fourier[k-N/2].imag()<<std::endl;
  //   }
    
  // }

  file.close();                                 // Close the file

  return 0;
}