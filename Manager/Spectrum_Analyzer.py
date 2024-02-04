import SoapySDR
from SoapySDR import *

from os import path
from multiprocessing import Process, Manager

import numpy
import scipy.signal
from scipy.fft import fft, fftfreq, fftshift
from  scipy.io import wavfile 

import pyqtgraph as pg
from pyqtgraph.Qt import QtGui, QtCore

import time

sample_rate=int(20e6)
frequency=int(99.7e6)
Samples=int(1024*2**6)

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
            if (Hackrf_RX.ret==-4):
                Hackrf.deactivateStream(rxStream) #stop streaming
                time.sleep(0.1)
        else:
            Data_Buffer.append(buffer-numpy.mean(buffer))
            

def FFT_samples_Graph(external_buff,FFT_Graph_Buffer,FFT_Axis_Graph_Buffer,samp_rate,samp):
    
    FFT_Axis=fftfreq(samp, 1/samp_rate)
    FFT_Axis=fftshift(FFT_Axis)

    FFT_Axis_Graph_Buffer.append(FFT_Axis)

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

                FFT_Graph_Buffer.append(Package_Buffer)


            else:
                for i in range (1,int((1/Packages))):
                    buff=numpy.array([0]*samp, numpy.complex64)
                    lowindex=(i-1)*samp
                    supindex=samp*i
                    buff=Package_Buffer[lowindex:supindex]
                    buff=fft(buff)
                    buff=1.0/samp*numpy.abs(buff)
                    buff=fftshift(buff)
                    
                    buff=20*numpy.log10(buff,where=(buff!=0),out=numpy.ones_like(buff)*-100)

                    FFT_Graph_Buffer.append(buff)

def update(graph,data_x,data_y):

            if len(data_y)!=0:
                graph.setData(data_x[0],data_y.pop(0))

def Graph_Pyqtgraph_Core(Title_1,x_1,y_1,freq):
    app = pg.mkQApp(Title_1)
    win = pg.GraphicsLayoutWidget(show=True, title=Title_1)
    win.resize(1000,600)
    win.setWindowTitle(Title_1)

    # Enable antialiasing for prettier plots
    pg.setConfigOptions(antialias=True)


    while len(y_1)==0:
        pass

    win.nextRow()

    x_1[0]=x_1[0]+freq

    p1 = win.addPlot()
    curve_1 = p1.plot(pen='y')
    p1.setXRange(x_1[0][0],x_1[0][-1], padding=0)
    p1.setYRange(-90, 0, padding=0)
    p1.enableAutoRange('xy', False)  ## stop auto-scaling after the first data set is plotted

    
    timer_1 = QtCore.QTimer()
    timer_1.timeout.connect(lambda:   update(curve_1,x_1,y_1))
    
    timer_1.start()


    pg.exec()



if __name__ == '__main__':

    manager=Manager()

    external_buff_Global=manager.list()

    FFT_Data_Graph_Buffer_Global=manager.list()
    FFT_Data_Axis_Graph_Buffer_Global=manager.list()

    Read=Process(target=HackRF_RX, args=(external_buff_Global,frequency,sample_rate))
    
    Fourier_Signal=Process(target=FFT_samples_Graph, args=(external_buff_Global,FFT_Data_Graph_Buffer_Global,FFT_Data_Axis_Graph_Buffer_Global,sample_rate,Samples))

    Graph=Process(target=Graph_Pyqtgraph_Core, args=("FFT",FFT_Data_Axis_Graph_Buffer_Global,FFT_Data_Graph_Buffer_Global,frequency))

    Read.start()
    Fourier_Signal.start()
    Graph.start()

    Read.join()



    # print("hola")v