import SoapySDR
from SoapySDR import *

from os import path
import multiprocessing
from multiprocessing import Process, Manager, shared_memory, Condition

import numpy
import scipy.signal
from scipy.fft import fft, fftfreq, fftshift
from  scipy.io import wavfile 

import pyqtgraph as pg
from pyqtgraph.Qt import QtGui, QtCore

import time

# La calidad del audio depende directamente de la cantidad de muestras que se utilicen en la HACKRF One

sample_rate=int(2822400)
frequency=int(97.9e6)
Samples=int(1024*2**4)
Base_Samples=int(131072)
# Base_Samples=int(1024*2**5)

Buffer_mult=int(1000)
Hackrf_LNA=int(32)
Hackrf_VGA=int(16)
Fm_decimation=8
Audio_decimation=8

def HackRF_RX(freq,samp_rate,Data_Condition,Samps,Manager):
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

        buffer = numpy.array([0]*Samps, numpy.complex64)
        Hackrf_RX = Hackrf.readStream(rxStream, [buffer], len(buffer))

        if(Hackrf_RX.ret!=Samps):
            print("Error "+str(Hackrf_RX.ret))
            if (Hackrf_RX.ret==-4):
                Hackrf.deactivateStream(rxStream) #stop streaming
        else:
            Manager.append(buffer)
            with Data_Condition:
                RawData_mem = shared_memory.SharedMemory(name='RawData')
                RawData = numpy.ndarray((2,Samps), dtype=numpy.float64, buffer=RawData_mem.buf)

                RawData[0]=numpy.real(buffer)
                RawData[1]=numpy.imag(buffer)

                RawData_mem.close()
                Data_Condition.notify()
            
def FFT_samples_Graph(Data,Graph,Axis,samp_rate,samp,Data_Condition,Data_len):
    
    FFT_Axis=fftfreq(samp, 1/samp_rate)
    FFT_Axis=fftshift(FFT_Axis)
    FFT_Data_Axis_Graph_Buffer_Global_mem = shared_memory.SharedMemory(name=Axis)
    FFT_Data_Axis_Graph_Buffer_Global = numpy.ndarray((samp), dtype=numpy.float64, buffer=FFT_Data_Axis_Graph_Buffer_Global_mem.buf)

    numpy.copyto(FFT_Data_Axis_Graph_Buffer_Global,FFT_Axis)

    FFT_Data_Axis_Graph_Buffer_Global_mem.close()    

    Packages=samp/Data_len
    while True:

        with Data_Condition:
            Data_Condition.wait()
            FourierRawData_mem = shared_memory.SharedMemory(name=Data)
            
            if(Data=='RawData'):
                FourierRawData = numpy.ndarray((2,Data_len), dtype=numpy.float64, buffer=FourierRawData_mem.buf)
                FourierRawData=FourierRawData[0]+FourierRawData[1]*1j
            else:
                FourierRawData = numpy.ndarray((Data_len), dtype=numpy.float64, buffer=FourierRawData_mem.buf)
                FourierRawData=FourierRawData+0*1j
            FourierRawData_mem.close()
        

        if(Packages>=1):
            Buffer=FourierRawData
            if(Packages>1):
                for i in range(1,int(Packages)):
                    with Data_Condition:
                        Data_Condition.wait()
                        FourierRawData_mem = shared_memory.SharedMemory(name=Data)
                        if(Data=='RawData'):
                            FourierRawData = numpy.ndarray((2,Data_len), dtype=numpy.float64, buffer=FourierRawData_mem.buf)
                            FourierRawData=FourierRawData[0]+FourierRawData[1]*1j
                        else:
                            FourierRawData = numpy.ndarray((Data_len), dtype=numpy.float64, buffer=FourierRawData_mem.buf)
                            FourierRawData=FourierRawData+0*1j
                        Buffer=numpy.append(Buffer,FourierRawData)
                        FourierRawData_mem.close()

            Buffer=Buffer-numpy.mean(Buffer)
            Buffer=fft(Buffer)
            Buffer=1.0/samp*numpy.abs(Buffer)
            Buffer=fftshift(Buffer)   

            Buffer=20*numpy.log10(Buffer,where=(Buffer!=0),out=numpy.ones_like(Buffer)*-100)

            FFT_Data_Graph_Buffer_Global_mem = shared_memory.SharedMemory(name=Graph)
            FFT_Data_Graph_Buffer_Global = numpy.ndarray((samp), dtype=numpy.float64, buffer=FFT_Data_Graph_Buffer_Global_mem.buf)

            numpy.copyto(FFT_Data_Graph_Buffer_Global,Buffer)
            FFT_Data_Graph_Buffer_Global_mem.close()

        else:
            for i in range (1,int((1/Packages))):
                Buffer=numpy.array([0]*samp, numpy.complex64)
                lowindex=(i-1)*samp
                supindex=samp*i
                Buffer=FourierRawData[lowindex:supindex]
                Buffer=Buffer-numpy.mean(Buffer)
                Buffer=fft(Buffer)
                Buffer=1.0/samp*numpy.abs(Buffer)
                Buffer=fftshift(Buffer)
    
                Buffer=20*numpy.log10(Buffer,where=(Buffer!=0),out=numpy.ones_like(Buffer)*-100)

                FFT_Data_Graph_Buffer_Global_mem = shared_memory.SharedMemory(name=Graph)
                FFT_Data_Graph_Buffer_Global = numpy.ndarray((samp), dtype=numpy.float64, buffer=FFT_Data_Graph_Buffer_Global_mem.buf)
       
                numpy.copyto(FFT_Data_Graph_Buffer_Global,Buffer)

                FFT_Data_Graph_Buffer_Global_mem.close()

def FM_demod(sample_rate,Decimation,Fm_Condition,Samps,Manager,FM_Manager):
    
    while True:
        if(len(Manager)!=0):
            Buffer = numpy.array([0]*Samps, numpy.complex64)
            Buffer=Manager.pop(0)

            # Filtro hasta 150Khz
            b, a = scipy.signal.iirfilter(4, Wn=150e3, fs=sample_rate, btype="low", ftype="butter")
            Buffer=scipy.signal.filtfilt(b, a, Buffer)
                
            Buffer=Buffer-numpy.mean(Buffer)

            Buffer=Buffer[::Decimation]

            # Angulo de la señal
            Buffer=numpy.angle(Buffer)

            # Derivada
            Buffer=numpy.diff(Buffer)
                
            # Normalizacion -> Ajusta el angulo entre 0 y 2pi para luego desplazarlo entre -pi y pi
            Buffer = (Buffer + numpy.pi) % (2 * numpy.pi) - numpy.pi

            # Ganancia y normalizacion (-pi,pi) -> (-1,1) -> Samplerate/(2*200k)
            Buffer = Buffer*0.99/(numpy.pi*200000/((sample_rate/Decimation) / 2))

            # Limita los valores
            Buffer = numpy.clip(Buffer, -0.999, +0.999)

            # Filtro hasta 100Khz
            b, a = scipy.signal.iirfilter(4, Wn=100e3, fs=sample_rate/Decimation, btype="low", ftype="butter")
            Buffer=scipy.signal.filtfilt(b, a, Buffer)
            Buffer=numpy.append(Buffer,Buffer[-1])

            FM_Manager.append(Buffer)

            with  Fm_Condition:
                FMData_mem   = shared_memory.SharedMemory(name='FMData')
                FMData       = numpy.ndarray(int(numpy.ceil(Samps/Decimation)), dtype=numpy.float64, buffer=FMData_mem.buf)
                numpy.copyto(FMData,Buffer)
                FMData_mem.close()
                Fm_Condition.notify()

def FM_Audio(sample_rate,Decimation,Mode,Data_len,Fm_Manager):
    
    while True:

        if(len(Fm_Manager)!=0):

            Stereo = numpy.array([0]*Data_len,numpy.float64)
            Mono = numpy.array([0]*Data_len,numpy.float64)
            
            Mono=Fm_Manager.pop(0)
            Stereo=Mono

            # Filtro de 15KHz Lowpass
            b, a = scipy.signal.iirdesign(wp=15e3,ws=18e3,gpass=0.1, gstop=60, fs=int(sample_rate), ftype="ellip")
            Mono=scipy.signal.filtfilt(b, a, Mono)
                    
            # Filtro de 30Hz Highpass
            b, a = scipy.signal.iirfilter(4, Wn=30,rp=0.1,rs=60, fs=int(sample_rate), btype="highpass", ftype="ellip")
            Mono=scipy.signal.filtfilt(b, a, Mono)

            if(Mode=="Stereo"):
                
                # Filtro de 23KHz-53KHz Bandpass
                b, a = scipy.signal.iirfilter(4, Wn=numpy.array([23e3, 53e3]),rp=0.1,rs=60, fs=int(sample_rate), btype="bandpass", ftype="ellip")
                Stereo=scipy.signal.filtfilt(b, a, Stereo)
    
                t_sample=numpy.arange(len(Stereo))/(sample_rate)

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

def FM_RDS(sample_rate,Fm_Condition,RDS_Condition,Data_len):
    while True:
        with Fm_Condition:
            Buffer=numpy.array([0]*Data_len,dtype=numpy.float64)
            Fm_Condition.wait()
            FMData_mem = shared_memory.SharedMemory(name='FMData')
            FMData = numpy.ndarray((Data_len), dtype=numpy.float64, buffer=FMData_mem.buf)

            numpy.copyto(Buffer,FMData)
            FMData_mem.close()

            # Filtro de 57+-2KHz Bandpass
            b, a = scipy.signal.iirfilter(6, Wn=numpy.array([55e3, 59e3]),rp=0.1,rs=60, fs=int(sample_rate), btype="bandpass", ftype="ellip")
            Buffer=scipy.signal.filtfilt(b, a, Buffer)
            
            with  RDS_Condition:
                RDSData_mem   = shared_memory.SharedMemory(name='RDSData')
                RDSData       = numpy.ndarray((Data_len), dtype=numpy.float64, buffer=RDSData_mem.buf)
                numpy.copyto(RDSData,Buffer)
                RDSData_mem.close()
                RDS_Condition.notify()

            # # Filtro de 30Hz Highpass
            # b, a = scipy.signal.iirfilter(4, Wn=30, fs=int(sample_rate), btype="highpass", ftype="butter")
            # Mono=scipy.signal.filtfilt(b, a, Mono)

def update(graph,data_x,data_y,num):
        
        X_mem = shared_memory.SharedMemory(name=data_x)
        Y_mem = shared_memory.SharedMemory(name=data_y)

        X_data = numpy.ndarray((num), dtype=numpy.float64, buffer=X_mem.buf)
        Y_data = numpy.ndarray((num), dtype=numpy.float64, buffer=Y_mem.buf)

        graph.setData(numpy.array(X_data),numpy.array(Y_data))

        X_mem.close()    
        Y_mem.close()   

def Graph_Pyqtgraph_Core(Title_1,freq,samp):
    app = pg.mkQApp(Title_1)
    win = pg.GraphicsLayoutWidget(show=True, title=Title_1)
    win.resize(1000,600)
    win.setWindowTitle(Title_1)

    # Enable antialiasing for prettier plots
    pg.setConfigOptions(antialias=True)


    p1 = win.addPlot()
    curve_1 = p1.plot(pen='y')
    p1.setXRange(-4.41e6/2, 4.41e6/2, padding=0)
    p1.setYRange(-90, 0, padding=0)
    p1.enableAutoRange('xy', False)  ## stop auto-scaling after the first data set is plotted
    
    win.nextRow()

    p2 = win.addPlot()
    curve_2 = p2.plot(pen='y')
    p2.setXRange(0, 75e3, padding=0)
    p2.setYRange(-90, 0, padding=0)
    p2.enableAutoRange('xy', False)  ## stop auto-scaling after the first data set is plotted

    win.nextRow()

    p3 = win.addPlot()
    curve_3 = p3.plot(pen='y')
    p3.setXRange(0, 75e3, padding=0)
    p3.setYRange(-90, 0, padding=0)
    p3.enableAutoRange('xy', False)  ## stop auto-scaling after the first data set is plotted

    
    timer_1 = QtCore.QTimer()
    timer_1.timeout.connect(lambda:   update(curve_1,'FFT_Data_Axis_Graph_Buffer_Global','FFT_Data_Graph_Buffer_Global',samp))
    
    timer_2 = QtCore.QTimer()
    timer_2.timeout.connect(lambda:   update(curve_2,'FFT_FM_Axis_Graph_Buffer_Global','FFT_FM_Graph_Buffer_Global',samp))

    timer_3 = QtCore.QTimer()
    timer_3.timeout.connect(lambda:   update(curve_3,'FFT_RDS_Axis_Graph_Buffer_Global','FFT_RDS_Graph_Buffer_Global',samp))

    timer_1.start()
    timer_2.start()
    timer_3.start()

    pg.exec()

if __name__ == '__main__':

    manager=Manager()

    Manager_RawData=manager.list()
    Manager_FMData=manager.list()

    Fm_Size=int(numpy.ceil(Base_Samples / (Fm_decimation)))

    d_size          = numpy.dtype(numpy.float64).itemsize * 2 * Base_Samples
    d_size_normal   = numpy.dtype(numpy.float64).itemsize * Base_Samples
    d_size_fm       = numpy.dtype(numpy.float64).itemsize * Fm_Size
    d_size_samples  = numpy.dtype(numpy.float64).itemsize * Samples

    RX_Data_ready = Condition()
    FM_Data_Ready = Condition()
    RDS_Data_Ready = Condition()

    RawData_mem     = shared_memory.SharedMemory(create=True, size=d_size, name='RawData')
    RawData         = numpy.ndarray(shape=(2,Base_Samples), dtype=numpy.float64, buffer=RawData_mem.buf)

    FMData_mem  = shared_memory.SharedMemory(create=True, size=d_size_fm, name='FMData')
    FMData      = numpy.ndarray(shape=(Fm_Size), dtype=numpy.float64, buffer=FMData_mem.buf)

    RDSData_mem  = shared_memory.SharedMemory(create=True, size=d_size_fm, name='RDSData')
    RDSData      = numpy.ndarray(shape=(Fm_Size), dtype=numpy.float64, buffer=RDSData_mem.buf)
    

    FFT_Data_Graph_Buffer_Global_mem    = shared_memory.SharedMemory(create=True, size=d_size_samples, name='FFT_Data_Graph_Buffer_Global')
    FFT_Data_Graph_Buffer_Global        = numpy.ndarray(shape=(Samples), dtype=numpy.float64, buffer=FFT_Data_Graph_Buffer_Global_mem.buf)

    FFT_Data_Axis_Graph_Buffer_Global_mem   = shared_memory.SharedMemory(create=True, size=d_size_samples, name='FFT_Data_Axis_Graph_Buffer_Global')
    FFT_Data_Axis_Graph_Buffer_Global       = numpy.ndarray(shape=(Samples), dtype=numpy.float64, buffer=FFT_Data_Axis_Graph_Buffer_Global_mem.buf)



    FFT_FM_Graph_Buffer_Global_mem  = shared_memory.SharedMemory(create=True, size=d_size_samples, name='FFT_FM_Graph_Buffer_Global')
    FFT_FM_Graph_Buffer_Global      = numpy.ndarray(shape=(Samples), dtype=numpy.float64, buffer=FFT_FM_Graph_Buffer_Global_mem.buf)

    FFT_FM_Axis_Graph_Buffer_Global_mem     = shared_memory.SharedMemory(create=True, size=d_size_samples, name='FFT_FM_Axis_Graph_Buffer_Global')
    FFT_FM_Axis_Graph_Buffer_Global         = numpy.ndarray(shape=(Samples), dtype=numpy.float64, buffer=FFT_FM_Axis_Graph_Buffer_Global_mem.buf)

 
    FFT_RDS_Graph_Buffer_Global_mem    = shared_memory.SharedMemory(create=True, size=d_size_samples, name='FFT_RDS_Graph_Buffer_Global')
    FFT_RDS_Graph_Buffer_Global        = numpy.ndarray(shape=(Samples), dtype=numpy.float64, buffer=FFT_RDS_Graph_Buffer_Global_mem.buf)

    FFT_RDS_Axis_Graph_Buffer_Global_mem   = shared_memory.SharedMemory(create=True, size=d_size_samples, name='FFT_RDS_Axis_Graph_Buffer_Global')
    FFT_RDS_Axis_Graph_Buffer_Global       = numpy.ndarray(shape=(Samples), dtype=numpy.float64, buffer=FFT_RDS_Axis_Graph_Buffer_Global_mem.buf)

   
    Read=Process(target=HackRF_RX, args=(frequency,sample_rate,RX_Data_ready,Base_Samples,Manager_RawData))
    
    Fourier_Signal=Process(target=FFT_samples_Graph, args=('RawData','FFT_Data_Graph_Buffer_Global','FFT_Data_Axis_Graph_Buffer_Global',sample_rate,Samples,RX_Data_ready,Base_Samples))
    Fourier_FM=Process(target=FFT_samples_Graph, args=('FMData','FFT_FM_Graph_Buffer_Global','FFT_FM_Axis_Graph_Buffer_Global',sample_rate/(Fm_decimation),Samples,FM_Data_Ready,Fm_Size))
    Fourier_RDS=Process(target=FFT_samples_Graph, args=('RDSData','FFT_RDS_Graph_Buffer_Global','FFT_RDS_Axis_Graph_Buffer_Global',sample_rate/(Fm_decimation),Samples,RDS_Data_Ready,Fm_Size))

    Fm=Process(target=FM_demod, args=(sample_rate,Fm_decimation,FM_Data_Ready,Base_Samples,Manager_RawData,Manager_FMData))
    Audio=Process(target=FM_Audio, args=(sample_rate/(Fm_decimation),Audio_decimation,"Mono",Fm_Size,Manager_FMData))
    FM_RadioDataSystem=Process(target=FM_RDS, args=(sample_rate/(Fm_decimation),FM_Data_Ready,RDS_Data_Ready,Fm_Size))
    Graph=Process(target=Graph_Pyqtgraph_Core, args=("FFT",frequency,Samples))

    Read.start()
    Fourier_Signal.start()

    Fm.start()
    Fourier_FM.start()
    Audio.start()
    FM_RadioDataSystem.start()
    Fourier_RDS.start()

    Graph.start()

    Graph.join()



    # print("hola")