#define _USE_MATH_DEFINES

#include <iostream>
#include <cmath>
#include <fstream>
#include <complex.h>
#include <vector>

const int N = 1024;                                                         // Number of samples
std::vector<std::complex<float>> FFT(std::vector<std::complex<float>>&);    // FFT algorithm

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


  file.open("Output_Signal.csv");                 // Open Output signal file
  if (!file.is_open()){
      std::cout << "Error in creating file!" << std::endl;
      return 1;
  }
  file << "Frequency Samples" <<","<<"Real"<<","<<"Imag"<<std::endl;  // CSV Header

  std::vector<std::complex<float>> Input_convert (N);

  for(int i = 0; i < N; i++){
    Input_convert[i]=std::complex<float>(square_signal[i], 0.0);
  }

  std::vector<std::complex<float>> Fourier = FFT(Input_convert);

  for(int k = 0; k < N; k++){                       // Saving Fourier Data with Shift from (-N/2)/period to +(N/2)/period  
 
     if(k<N/2.0){
      file << ((k-N/2.0))/10.0 <<","<< Fourier[k+N/2].real() <<","<<Fourier[k+N/2].imag()<<std::endl;
    }else{
      file << (k-N/2.0)/10.0 <<","<< Fourier[k-N/2].real() <<","<<Fourier[k-N/2].imag()<<std::endl;
    }
    
  }
  file.close();                                 // Close the file


  return 0;
}

std::vector<std::complex<float>> FFT(std::vector<std::complex<float>> &Input){
  
  // Number of samples on this Division recursive step
  int N = Input.size();
  
  if(N==1){       // If number of samples is 1, the division recursion is complete
    return Input;
  } 

  int M = N/2;    // Length of Divided Buffers

  std::vector<std::complex<float>> Xeven(M,0);    // Buffer of even samples
  std::vector<std::complex<float>> Xodd(M,0);     // Buffer of odd samples

  for(int i = 0; i<M; i++){                       // Fill the buffer with the input samples divided by two
    Xeven[i]=Input[2*i];
    Xodd[i]=Input[2*i+1];
  }

  std::vector<std::complex<float>> Feven(M,0);    // Buffer for recursive FFT Even side
  Feven = FFT(Xeven);                                 // Perform recursive algorithm Even side
  std::vector<std::complex<float>> Fodd(M,0);     // Buffer for recursive FFT Odd side
  Fodd = FFT(Xodd);                                   // Perform recursive algorithm Odd side

  std::vector<std::complex<float>> freqbins(N,0);  // Calculate the Sum of Odd and Even by the complex factor for all Fourier Bins
  for(int k=0; k<N/2.0; k++){
    std::complex<float> oddComplex = std::exp(std::complex<float>(0,static_cast<float>(-2*M_PI*k)/N))*Fodd[k];
    freqbins[k] = Feven[k]+oddComplex;
    freqbins[k+N/2.0] = Feven[k]-oddComplex; 
  }

  return freqbins;

}