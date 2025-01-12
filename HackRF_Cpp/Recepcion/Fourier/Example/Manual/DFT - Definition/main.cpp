#define _USE_MATH_DEFINES

#include <iostream>
#include <cmath>
#include <fstream>
#include <complex.h>

const int N = 1024;

int main(){
  std::ofstream file;

  float samples[N];
  float square_signal[N];
  float pass = 1.0;

  file.open("Input_Signal.csv");
  // Check if the file was successfully created.
  if (!file.is_open()){
      std::cout << "Error in creating file!" << std::endl;
      return 1;
  }

  for(int k = 0; k < N; k++){

    samples[k]=10*static_cast<float>(k)/(N-1);
    if(samples[k]>pass){
      pass+=1;
    }

    if(samples[k]<pass-1.0/2.0){
      square_signal[k]=1;
    }else{
      square_signal[k]=-1;
    }
    file << samples[k] <<","<<square_signal[k]<<std::endl;
  }
    file.close();

    std::complex<float> Fourier[N];

  file.open("Output_Signal.csv");
  // Check if the file was successfully created.
  if (!file.is_open()){
      std::cout << "Error in creating file!" << std::endl;
      return 1;
  }

  for(int k = 0; k < N; k++){
    for(int j = 0; j < N; j++){
      Fourier[k]+=square_signal[j]*std::complex<float>(cos(-2*M_PI*k*j/(N-1)),sin(-2*M_PI*k*j/(N-1)));
    }
  }

  for(int k = 0; k < N; k++){
 
     if(k<N/2.0){
      file << ((k-N/2.0)+1)/10.0 <<","<< Fourier[k+N/2].real() <<","<<Fourier[k+N/2].imag()<<std::endl;
    }else{
      file << (k-N/2.0)/10.0 <<","<< Fourier[k-N/2].real() <<","<<Fourier[k-N/2].imag()<<std::endl;
    }
    
  }


  return 0;
}