import SoapySDR
from SoapySDR import *

from os import path
from multiprocessing import Process, Manager

import numpy
import scipy.signal
from scipy.fft import fft, fftfreq, fftshift
from  scipy.io import wavfile 

import matplotlib.pyplot as plt

import time

# sample_rate=int(4.41e6)
sample_rate=int(4.41e6)
frequency=int(99.7e6)
# Samples=int(131072)
Samples=int(1024*4*4)

Buffer_mult=int(1000)
Hackrf_LNA=int(32)
Hackrf_VGA=int(16)
Fm_decimation=10
Audio_decimation=10


def HackRF_RX(Data_Buffer,freq,samp_rate):

    # Crea una interfaz de dispositivo
    Hackrf = SoapySDR.Device()

    # Configura una frecuencia y tasa de muestreo
    Hackrf.setSampleRate(SOAPY_SDR_RX, 0, samp_rate)
    Hackrf.setFrequency(SOAPY_SDR_RX, 0, freq)
    Hackrf.setGain(SOAPY_SDR_RX,0,'LNA',Hackrf_LNA)
    Hackrf.setGain(SOAPY_SDR_RX,0,'VGA',Hackrf_VGA)
    Hackrf.setGain(SOAPY_SDR_RX,0,'AMP',1)


    # Configura la transmision de datos, TX o RX y su formato
    rxStream = Hackrf.setupStream(SOAPY_SDR_RX, SOAPY_SDR_CF32)
    Hackrf.activateStream(rxStream) # Inicia la transmision de datos

    while True:
    
        buffer = numpy.array([0]*131072, numpy.complex64)
        Hackrf_RX = Hackrf.readStream(rxStream, [buffer], len(buffer))

        if(Hackrf_RX.ret!=131072):
            print("Error "+str(Hackrf_RX.ret))
        else:
            Data_Buffer.append(buffer)

def FFT_samples_Graph(external_buff,samp_rate,samp,limy):
    
    plt.ion()

    FFT_Axis=fftfreq(samp, 1/samp_rate)
    FFT_Axis=fftshift(FFT_Axis)
    
    figure, ax = plt.subplots(figsize=(10, 8))
    line1, = ax.plot(FFT_Axis,numpy.array([0]*samp))

    plt.xlabel("Frecuencia")
    plt.ylabel("Amplitud")

    plt.ylim(limy[0],limy[1])
    plt.xlim(0,75e3)

    Packages=samp/131072

    while True:

        if(len(external_buff)>Packages):

            Package_Buffer=numpy.array([0]*131072, numpy.complex64)
            Package_Buffer=external_buff.pop(0)
    
            if(Packages>1):
                for i in range(1,int(Packages)):
                    Package_Buffer=numpy.append(Package_Buffer,external_buff[0])

            if(Packages>=1):
                Package_Buffer=fft(Package_Buffer)
                Package_Buffer=1.0/samp*numpy.abs(Package_Buffer)
                Package_Buffer=fftshift(Package_Buffer)   

                Package_Buffer=20*numpy.log10(Package_Buffer)

                line1.set_ydata(Package_Buffer)
                figure.canvas.draw() 
                figure.canvas.flush_events()
            else:
                for i in range (1,int((1/Packages))):
                    buff=numpy.array([0]*samp, numpy.complex64)
                    lowindex=(i-1)*samp
                    supindex=samp*i
                    buff=Package_Buffer[lowindex:supindex]
                    buff=fft(buff)
                    buff=1.0/samp*numpy.abs(buff)
                    buff=fftshift(buff)
                    
                    buff=20*numpy.log10(buff)


                    line1.set_ydata(buff)
                    figure.canvas.draw() 
                    figure.canvas.flush_events()

def FM_demod(Data_buffer,Fourier_Buffer,RDS_Buffer,FM_Buff,sample_rate,Decimation):
    
    while True:
        if(len(Data_buffer)>Decimation):
            buff = numpy.array([0]*131072, numpy.complex64)

            buff=Data_buffer.pop(0)
            for i in range(1,Decimation):
                buff=numpy.append(buff,Data_buffer.pop(0))


            # Filtro hasta 150Khz
            b, a = scipy.signal.iirfilter(4, Wn=150e3, fs=sample_rate, btype="low", ftype="butter")
            buff=scipy.signal.filtfilt(b, a, buff)
            
            buff=buff-numpy.mean(buff)

            buff=buff[::Decimation]

            # Angulo de la señal
            buff=numpy.angle(buff)

            # Derivada
            buff=numpy.diff(buff)
            
            # Normalizacion -> Ajusta el angulo entre 0 y 2pi para luego desplazarlo entre -pi y pi
            buff = (buff + numpy.pi) % (2 * numpy.pi) - numpy.pi

            # Ganancia y normalizacion (-pi,pi) -> (-1,1) -> Samplerate/(2*200k)
            buff = buff*0.99/(numpy.pi*200000/((sample_rate/Decimation) / 2))

            # Limita los valores
            buff = numpy.clip(buff, -0.999, +0.999)

            # Filtro hasta 100Khz
            b, a = scipy.signal.iirfilter(4, Wn=100e3, fs=sample_rate/Decimation, btype="low", ftype="butter")
            buff=scipy.signal.filtfilt(b, a, buff)
            buff=numpy.append(buff,buff[32766])

            FM_Buff.append(buff)
            Fourier_Buffer.append(buff)
            RDS_Buffer.append(buff)

def FM_Audio(Data_Buffer,sample_rate,Decimation,Mode):
    
    while True:

        if(len(Data_Buffer)!=0):
            buff = numpy.array([0]*131072, numpy.complex64)
            buff=Data_Buffer.pop(0)

            Mono=buff

            # Filtro de 15KHz Lowpass
            b, a = scipy.signal.iirdesign(wp=15e3,ws=18e3,gpass=0.1, gstop=60, fs=int(sample_rate), ftype="ellip")
            Mono=scipy.signal.filtfilt(b, a, Mono)
                
            # Filtro de 30Hz Highpass
            b, a = scipy.signal.iirfilter(4, Wn=30,rp=0.1,rs=60, fs=int(sample_rate), btype="highpass", ftype="ellip")
            Mono=scipy.signal.filtfilt(b, a, Mono)

            if(Mode=="Stereo"):
                Stereo=buff

                # Filtro de 23KHz-53KHz Bandpass
                b, a = scipy.signal.iirfilter(4, Wn=numpy.array([23e3, 53e3]),rp=0.1,rs=60, fs=int(sample_rate), btype="bandpass", ftype="ellip")
                Stereo=scipy.signal.filtfilt(b, a, Stereo)
 
                t_sample=numpy.arange(len(buff))/(sample_rate)

                Stereo=Stereo*numpy.exp(2j*numpy.pi*-38e3*t_sample)
                Stereo=numpy.real(Stereo)
 
                # Filtro de 15KHz Lowpass
                b, a = scipy.signal.iirdesign(wp=15e3,ws=18e3,gpass=0.1, gstop=60, fs=int(sample_rate), ftype="ellip")
                Stereo=scipy.signal.filtfilt(b, a, Stereo)
                
                # Filtro de 30Hz Highpass
                b, a = scipy.signal.iirfilter(4, Wn=30,rp=0.1,rs=60, fs=int(sample_rate), btype="highpass", ftype="ellip")
                Stereo=scipy.signal.filtfilt(b, a, Stereo)
                
                left=Mono+Stereo
                right=Mono-Stereo

                left=left[::Decimation]
                right=right[::Decimation]

                Stereo=numpy.vstack((left, right))
                Stereo=Stereo.transpose()

            Mono=Mono[::Decimation]

            if(Mode=="Stereo"):

                if (path.exists("sound1.wav")):
                    xd, data = wavfile.read("sound1.wav")
                    wavfile.write('sound1.wav', int(2*sample_rate/(Decimation)), numpy.append(data,numpy.round(Stereo * 32767).astype(numpy.int16)))
                else:
                    wavfile.write('sound1.wav', int(2*sample_rate/(Decimation)), numpy.round(Stereo * 32767).astype(numpy.int16))
            else:
                if (path.exists("sound1.wav")):
                    xd, data = wavfile.read("sound1.wav")
                    wavfile.write('sound1.wav', int(sample_rate/(Decimation)), numpy.append(data,numpy.round(Mono * 32767).astype(numpy.int16)))
                else:
                    wavfile.write('sound1.wav', int(sample_rate/(Decimation)), numpy.round(Mono * 32767).astype(numpy.int16))

def FM_RDS(Data_Buffer,Samplerate,Fourier_buffer):
    while True:
        if(len(Data_Buffer)!=0):
            buff = numpy.array([0]*131072, numpy.complex64)
            buff=Data_Buffer.pop(0)
            

            # Filtro de 57+-2KHz Bandpass
            b, a = scipy.signal.iirfilter(6, Wn=numpy.array([55e3, 59e3]),rp=0.1,rs=60, fs=int(Samplerate), btype="bandpass", ftype="ellip")
            buff=scipy.signal.filtfilt(b, a, buff)

            # Fourier_buffer.append(buff)
  
            # # Filtro de 30Hz Highpass
            # b, a = scipy.signal.iirfilter(4, Wn=30, fs=int(sample_rate), btype="highpass", ftype="butter")
            # Mono=scipy.signal.filtfilt(b, a, Mono)

if __name__ == '__main__':

    manager=Manager()

    external_buff_Global=manager.list()
    FM_Buff_Global=manager.list()
    FM_Fourier_Buff_Global=manager.list()
    FM_RDS_Buff_Global=manager.list()
    FM_RDS_Fourier_Buff_Global=manager.list()

    Read=Process(target=HackRF_RX, args=(external_buff_Global,frequency,sample_rate))
    Fourier=Process(target=FFT_samples_Graph, args=(FM_Fourier_Buff_Global,sample_rate/(Fm_decimation),Samples,[-65, -20]))
    Fm=Process(target=FM_demod, args=(external_buff_Global,FM_Fourier_Buff_Global,FM_RDS_Buff_Global,FM_Buff_Global,sample_rate,Fm_decimation))
    Audio=Process(target=FM_Audio, args=(FM_Buff_Global,sample_rate/(Fm_decimation),Audio_decimation,"Stereo"))
    FM_RadioDataSystem=Process(target=FM_RDS, args=(FM_RDS_Buff_Global,sample_rate/(Fm_decimation),FM_RDS_Fourier_Buff_Global))

    Read.start()
    Fm.start()
    Fourier.start()
    Audio.start()
    FM_RadioDataSystem.start()

    Fourier.join()



    # print("hola")