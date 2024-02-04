import SoapySDR
from SoapySDR import *

from os import path
import multiprocessing
from multiprocessing import Process, Manager, shared_memory, RLock, Condition

import numpy
import scipy.signal
from scipy.fft import fft, fftfreq, fftshift
from  scipy.io import wavfile 

import pyqtgraph as pg
from pyqtgraph.Qt import QtGui, QtCore

import time

sample_rate=int(20e6)
frequency=int(97.9e6)
Samples=int(1024*2**4)
Base_Samples=int(131072)
# Base_Samples=int(1024*2**5)

Buffer_mult=int(1000)
Hackrf_LNA=int(32)
Hackrf_VGA=int(16)


def HackRF_RX(freq,samp_rate,Data_Condition,Samps):
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
    p1.setXRange(-10e6, 10e6, padding=0)
    p1.setYRange(-90, 0, padding=0)
    p1.enableAutoRange('xy', False)  ## stop auto-scaling after the first data set is plotted
    

    timer_1 = QtCore.QTimer()
    timer_1.timeout.connect(lambda:   update(curve_1,'FFT_Data_Axis_Graph_Buffer_Global','FFT_Data_Graph_Buffer_Global',samp))
    
    timer_1.start()


    pg.exec()

if __name__ == '__main__':

    d_size          = numpy.dtype(numpy.float64).itemsize * 2 * Base_Samples
    d_size_samples  = numpy.dtype(numpy.float64).itemsize * Samples

    RX_Data_ready = Condition()

    RawData_mem     = shared_memory.SharedMemory(create=True, size=d_size, name='RawData')
    RawData         = numpy.ndarray(shape=(2,Base_Samples), dtype=numpy.float64, buffer=RawData_mem.buf)

    FFT_Data_Graph_Buffer_Global_mem    = shared_memory.SharedMemory(create=True, size=d_size_samples, name='FFT_Data_Graph_Buffer_Global')
    FFT_Data_Graph_Buffer_Global        = numpy.ndarray(shape=(Samples), dtype=numpy.float64, buffer=FFT_Data_Graph_Buffer_Global_mem.buf)

    FFT_Data_Axis_Graph_Buffer_Global_mem   = shared_memory.SharedMemory(create=True, size=d_size_samples, name='FFT_Data_Axis_Graph_Buffer_Global')
    FFT_Data_Axis_Graph_Buffer_Global       = numpy.ndarray(shape=(Samples), dtype=numpy.float64, buffer=FFT_Data_Axis_Graph_Buffer_Global_mem.buf)

   
    Read=Process(target=HackRF_RX, args=(frequency,sample_rate,RX_Data_ready,Base_Samples))
    Fourier_Signal=Process(target=FFT_samples_Graph, args=('RawData','FFT_Data_Graph_Buffer_Global','FFT_Data_Axis_Graph_Buffer_Global',sample_rate,Samples,RX_Data_ready,Base_Samples))
    Graph=Process(target=Graph_Pyqtgraph_Core, args=("FFT",frequency,Samples))

    Read.start()
    Fourier_Signal.start()
    Graph.start()

    Graph.join()



    # print("hola")