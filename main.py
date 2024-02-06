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

sample_rate=int(2e6)
frequency=int(88.9e6)
Samples=int(1024*2**4)
Base_Samples=int(131072)
# Base_Samples=int(1024*2**5)

Buffer_mult=int(1000)
Hackrf_LNA=int(16)
Hackrf_VGA=int(16)
Fm_sample_rate=int(250e3)
RDS_sample_rate=int(19e3)

bufferappend=16

# see Annex B, page 64 of the standard
def calc_syndrome(x, mlen):
    reg = 0
    plen = 10
    for ii in range(mlen, 0, -1):
        reg = (reg << 1) | ((x >> (ii-1)) & 0x01)
        if (reg & (1 << plen)):
            reg = reg ^ 0x5B9
    for ii in range(plen, 0, -1):
        reg = reg << 1
        if (reg & (1 << plen)):
            reg = reg ^ 0x5B9
    return reg & ((1 << plen) - 1) # select the bottom plen bits of reg

def Buffer_Expand(Manager_In,Manager_Out,n):
    while True:
        if(len(Manager_In)>n):
            Buffer=Manager_In.pop(0)
            if(n>1):  
                for i in range(n-1):
                    Buffer=numpy.append(Buffer, Manager_In.pop(0))
            Manager_Out.append(Buffer)                

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

def FM_demod(sample_rate,Fm_sample_rate,Fm_Condition,Manager,FM_Manager,RDS_Manager,Fm_Sz):
    
    while True:
        if(len(Manager)!=0):
            Buffer=Manager.pop(0)
            # Filtro hasta 150Khz
            b, a = scipy.signal.iirfilter(4, Wn=150e3, fs=sample_rate, btype="low", ftype="butter")
            Buffer=scipy.signal.filtfilt(b, a, Buffer)
                
            Buffer=Buffer-numpy.mean(Buffer)

            # Remuestreo
            Buffer=scipy.signal.resample_poly(Buffer,Fm_sample_rate , sample_rate)

            # Angulo de la señal
            Buffer=numpy.angle(Buffer)

            # Derivada
            Buffer=numpy.diff(Buffer)
                
            # Normalizacion -> Ajusta el angulo entre 0 y 2pi para luego desplazarlo entre -pi y pi
            Buffer = (Buffer + numpy.pi) % (2 * numpy.pi) - numpy.pi

            # Ganancia y normalizacion (-pi,pi) -> (-1,1) -> Samplerate/(2*200k)
            Buffer = Buffer*0.99/(numpy.pi*200000/((Fm_sample_rate) / 2))

            # Limita los valores
            Buffer = numpy.clip(Buffer, -0.999, +0.999)

            # Filtro hasta 100Khz
            b, a = scipy.signal.iirfilter(4, Wn=100e3, fs=Fm_sample_rate, btype="low", ftype="butter")
            Buffer=scipy.signal.filtfilt(b, a, Buffer)
            Buffer=numpy.append(Buffer,Buffer[-1])

            FM_Manager.append(Buffer)
            RDS_Manager.append(Buffer)

            with  Fm_Condition:
                FMData_mem   = shared_memory.SharedMemory(name='FMData')
                FMData       = numpy.ndarray(Fm_Sz, dtype=numpy.float64, buffer=FMData_mem.buf)
                numpy.copyto(FMData,Buffer[0:Fm_Sz])
                FMData_mem.close()
                Fm_Condition.notify()

def FM_Audio(sample_rate,Mode,Data_len,Fm_Manager):
    
    while True:

        if(len(Fm_Manager)!=0):
            
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
            
                # Remuestreo a 44.1KHz
                left=scipy.signal.resample_poly(left, 44100 , sample_rate)
                right=scipy.signal.resample_poly(right, 44100 , sample_rate)


                Stereo=numpy.vstack((left, right))
                Stereo=Stereo.transpose()
            
            Mono=scipy.signal.resample_poly(Mono, 44100 , sample_rate)


            if(Mode=="Stereo"):

                if (path.exists("sound1.wav")):
                    xd, data = wavfile.read("sound1.wav")
                    wavfile.write('sound1.wav', int(2*44100), numpy.append(data,numpy.round(Stereo * 32767).astype(numpy.int16)))
                else:
                    wavfile.write('sound1.wav', int(2*44100), numpy.round(Stereo * 32767).astype(numpy.int16))
            else:
                if (path.exists("sound1.wav")):
                    xd, data = wavfile.read("sound1.wav")
                    wavfile.write('sound1.wav', int(44100), numpy.append(data,numpy.round(Mono * 32767).astype(numpy.int16)))
                else:
                    wavfile.write('sound1.wav', int(44100), numpy.round(Mono * 32767).astype(numpy.int16))

def FM_RDS(sample_rate,RDS_sample_rate,RDS_Manager,Data_len,Rds_Sz):

    phase = 0
    freq = 0
    mu = 0.01 # initial estimate of phase of sample
    sps = 16

    mu_AGC = 0.001
    AGCMult =1
    ref = 1

    # Constants
    syndrome = [383, 14, 303, 663, 748]
    offset_pos = [0, 1, 2, 3, 2]
    offset_word = [252, 408, 360, 436, 848]


    # Initialize all the working vars we'll need during the loop
    synced = False
    presync = False

    wrong_blocks_counter = 0
    blocks_counter = 0
    group_good_blocks_counter = 0

    reg = numpy.uint32(0) # was unsigned long in C++ (64 bits) but numpy doesn't support bitwise ops of uint64, I don't think it gets that high anyway
    lastseen_offset_counter = 0
    lastseen_offset = 0

    # the synchronization process is described in Annex C, page 66 of the standard */
    bytes_out = []

    # Annex F of RBDS Standard Table F.1 (North America) and Table F.2 (Europe)
    #              Europe                   North America
    pty_table = [["Undefined",             "Undefined"],
                ["News",                  "News"],
                ["Current Affairs",       "Information"],
                ["Information",           "Sports"],
                ["Sport",                 "Talk"],
                ["Education",             "Rock"],
                ["Drama",                 "Classic Rock"],
                ["Culture",               "Adult Hits"],
                ["Science",               "Soft Rock"],
                ["Varied",                "Top 40"],
                ["Pop Music",             "Country"],
                ["Rock Music",            "Oldies"],
                ["Easy Listening",        "Soft"],
                ["Light Classical",       "Nostalgia"],
                ["Serious Classical",     "Jazz"],
                ["Other Music",           "Classical"],
                ["Weather",               "Rhythm & Blues"],
                ["Finance",               "Soft Rhythm & Blues"],
                ["Children’s Programmes", "Language"],
                ["Social Affairs",        "Religious Music"],
                ["Religion",              "Religious Talk"],
                ["Phone-In",              "Personality"],
                ["Travel",                "Public"],
                ["Leisure",               "College"],
                ["Jazz Music",            "Spanish Talk"],
                ["Country Music",         "Spanish Music"],
                ["National Music",        "Hip Hop"],
                ["Oldies Music",          "Unassigned"],
                ["Folk Music",            "Unassigned"],
                ["Documentary",           "Weather"],
                ["Alarm Test",            "Emergency Test"],
                ["Alarm",                 "Emergency"]]
    pty_locale = 1 # set to 0 for Europe which will use first column instead

    # page 72, Annex D, table D.2 in the standard
    coverage_area_codes = ["Local",
                        "International",
                        "National",
                        "Supra-regional",
                        "Regional 1",
                        "Regional 2",
                        "Regional 3",
                        "Regional 4",
                        "Regional 5",
                        "Regional 6",
                        "Regional 7",
                        "Regional 8",
                        "Regional 9",
                        "Regional 10",
                        "Regional 11",
                        "Regional 12"]

    radiotext_AB_flag = 0
    radiotext = [' ']*65
    first_time = True

    while True:
        if(len(RDS_Manager)!=0):
            Buffer=RDS_Manager.pop(0)

            # Filtro de 57+-2KHz Bandpass
            b, a = scipy.signal.iirfilter(6, Wn=numpy.array([55e3, 59e3]),rp=0.1,rs=90, fs=int(sample_rate), btype="bandpass", ftype="ellip")
            Buffer=scipy.signal.filtfilt(b, a, Buffer)
            
            # Corrimiento de -57KHz
            t_sample=numpy.arange(len(Buffer))/(sample_rate)
            Buffer=Buffer*numpy.exp(2j*numpy.pi*-57e3*t_sample)
    
            # Filtro de 7.5KHz Lowpass
            b, a = scipy.signal.iirdesign(wp=7.5e3,ws=8e3,gpass=0.1, gstop=60, fs=int(sample_rate), ftype="ellip")
            Buffer=scipy.signal.filtfilt(b, a, Buffer)

            # Remuestreo a 19KHz
            Buffer=scipy.signal.resample_poly(Buffer, RDS_sample_rate , sample_rate)

            # Sincronizacion temporal de las muestras - Samples at 19KHz to Samples at 1187.5Hz , Sample length / 16
            # Sincronizacion de Mueller and mueller clock recovery


            # num_iter = len(Buffer)
            # out=numpy.zeros(num_iter, dtype=numpy.complex64)

            # for n in range(1,num_iter):
            #     out[n]=Buffer[n]*AGCMult
            #     error=ref-numpy.abs(out[n])
            #     AGCMult = AGCMult +mu_AGC*error
            #     AGCMult=numpy.clip(AGCMult,0,65536)

            # numpy.copyto(Buffer,out)


            # Symbol sync, using what we did in sync chapter


            samples_interpolated = scipy.signal.resample_poly(Buffer, 32, 1) # we'll use 32 as the interpolation factor, arbitrarily chosen, seems to work better than 16
            out = numpy.zeros(len(Buffer) + 10, dtype=numpy.complex64)
            out_rail = numpy.zeros(len(Buffer) + 10, dtype=numpy.complex64) # stores values, each iteration we need the previous 2 values plus current value
            i_in = 0 # inumpyut samples index
            i_out = 2 # output index (let first two outputs be 0)
            
            while i_out < len(Buffer) and i_in+32 < len(Buffer):

                out[i_out] = samples_interpolated[i_in*32 + int(mu*32)] # grab what we think is the "best" sample
                out_rail[i_out] = int(numpy.real(out[i_out]) > 0) + 1j*int(numpy.imag(out[i_out]) > 0)
                x = (out_rail[i_out] - out_rail[i_out-2]) * numpy.conj(out[i_out-1])
                y = (out[i_out] - out[i_out-2]) * numpy.conj(out_rail[i_out-1])
                mm_val = numpy.real(y - x)


                mu += sps + 0.0004*mm_val
                # mu += sps + 0.3*mm_val

                i_in += int(numpy.floor(mu)) # round down to nearest int since we are using it as an index
                mu = mu - numpy.floor(mu) # remove the integer part of mu
                i_out += 1 # increment output index
            Buffer = out[2:i_out] # remo


            # damp=numpy.sqrt(2)/2
            # bw=2*numpy.pi/200

            # alpha = (4 * damp * bw) / (1 + 2 * damp * bw + bw * bw)

            # beta = (4 * bw * bw) / (1 + 2 * damp * bw + bw * bw)


            # # Fine freq sync
            N = len(Buffer)

            # These next two params is what to adjust, to make the feedback loop faster or slower (which impacts stability)
            alpha = 8.0
            beta = 0.002

            # alpha = 0.1
            # beta = 0.1

            # freq=0
            # phase=0


            out = numpy.zeros(N, dtype=numpy.complex64)
            for i in range(N):
                out[i] = Buffer[i] * numpy.exp(-1j*phase) # adjust the inumpyut sample by the inverse of the estimated phase offset

                # error = numpy.real(out[i]) * numpy.imag(out[i]) # This is the error formula for 2nd order Costas Loop (e.g. for BPSK)
                error = numpy.imag(out[i]) # This is the error formula for 2nd order Costas Loop (e.g. for BPSK)

                # Advance the loop (recalc phase and freq offset)
                freq += (beta * error)
                # print(freq * RDS_sample_rate / (2*numpy.pi*16))
                phase += freq + (alpha * error)
                # phase += (alpha * error)

                # Optional: Adjust phase so its always between 0 and 2pi, recall that phase wraps around every 2pi
                while phase >= 2*numpy.pi:
                    phase -= 2*numpy.pi
                while phase < 0:
                    phase += 2*numpy.pi
            Buffer = out



            # mu_AGC = 0.01
            # AGCMult =1
            # ref = 1
            # num_iter = len(Buffer)
            # out=numpy.zeros(num_iter, dtype=numpy.complex64)

            # for n in range(1,num_iter):
            #     out[n]=Buffer[n]*AGCMult
            #     error=ref-numpy.abs(out[n])
            #     AGCMult = AGCMult +mu_AGC*error
            #     AGCMult=numpy.clip(AGCMult,0,65536)

            # numpy.copyto(Buffer,out)



            RDS_IQ_mem   = shared_memory.SharedMemory(name='RDS_IQ')
            RDS_IQ       = numpy.ndarray((2,Rds_Sz), dtype=numpy.float64, buffer=RDS_IQ_mem.buf)

            numpy.copyto(RDS_IQ[0],numpy.real(Buffer[0:Rds_Sz]))
            numpy.copyto(RDS_IQ[1],numpy.imag(Buffer[0:Rds_Sz]))

            RDS_IQ_mem.close()







     

            # Demod BPSK
            Buffer = (numpy.real(Buffer) > 0).astype(int) # 1's and 0's

            # Differential decoding, so that it doesn't matter whether our BPSK was 180 degrees rotated without us realizing it
            Buffer = (Buffer[1:] - Buffer[0:-1]) % 2
            Buffer = Buffer.astype(numpy.uint8) # for decoder


            for i in range(len(Buffer)):
                # in C++ reg doesn't get init so it will be random at first, for ours its 0s
                # It was also an unsigned long but never seemed to get anywhere near the max value
                # bits are either 0 or 1
                reg = numpy.bitwise_or(numpy.left_shift(reg, 1), Buffer[i]) # reg contains the last 26 rds bits. these are both bitwise ops
                if not synced:
                    reg_syndrome = calc_syndrome(reg, 26)
                    for j in range(5):
                        if reg_syndrome == syndrome[j]:
                            if not presync:
                                lastseen_offset = j
                                lastseen_offset_counter = i
                                presync = True
                            else:
                                if offset_pos[lastseen_offset] >= offset_pos[j]:
                                    block_distance = offset_pos[j] + 4 - offset_pos[lastseen_offset]
                                else:
                                    block_distance = offset_pos[j] - offset_pos[lastseen_offset]
                                if (block_distance*26) != (i - lastseen_offset_counter):
                                    presync = False
                                else:
                                    print('Sync State Detected')
                                    wrong_blocks_counter = 0
                                    blocks_counter = 0
                                    block_bit_counter = 0
                                    block_number = (j + 1) % 4
                                    group_assembly_started = False
                                    synced = True
                        break # syndrome found, no more cycles

                else: # SYNCED
                    # wait until 26 bits enter the buffer */
                    if block_bit_counter < 25:
                        block_bit_counter += 1
                    else:
                        good_block = False
                        dataword = (reg >> 10) & 0xffff
                        block_calculated_crc = calc_syndrome(dataword, 16)
                        checkword = reg & 0x3ff
                        if block_number == 2: # manage special case of C or C' offset word
                            block_received_crc = checkword ^ offset_word[block_number]
                            if (block_received_crc == block_calculated_crc):
                                good_block = True
                            else:
                                block_received_crc = checkword ^ offset_word[4]
                                if (block_received_crc == block_calculated_crc):
                                    good_block = True
                                else:
                                    wrong_blocks_counter += 1
                                    good_block = False
                        else:
                            block_received_crc = checkword ^ offset_word[block_number] # bitwise xor
                            if block_received_crc == block_calculated_crc:
                                good_block = True
                            else:
                                wrong_blocks_counter += 1
                                good_block = False

                        # Done checking CRC
                        if block_number == 0 and good_block:
                            group_assembly_started = True
                            group_good_blocks_counter = 1
                            bytes = bytearray(8) # 8 bytes filled with 0s
                        if group_assembly_started:
                            if not good_block:
                                group_assembly_started = False
                            else:
                                # raw data bytes, as received from RDS. 8 info bytes, followed by 4 RDS offset chars: ABCD/ABcD/EEEE (in US) which we leave out here
                                # RDS information words
                                # block_number is either 0,1,2,3 so this is how we fill out the 8 bytes
                                bytes[block_number*2] = (dataword >> 8) & 255
                                bytes[block_number*2+1] = dataword & 255
                                group_good_blocks_counter += 1
                                #print('group_good_blocks_counter:', group_good_blocks_counter)
                            if group_good_blocks_counter == 5:
                                #print(bytes)
                                bytes_out.append(bytes) # list of len-8 lists of bytes
                        block_bit_counter = 0
                        block_number = (block_number + 1) % 4
                        blocks_counter += 1
                        if blocks_counter == 50:
                            if wrong_blocks_counter > 35: # This many wrong blocks must mean we lost sync
                                print("Lost Sync (Got ", wrong_blocks_counter, " bad blocks on ", blocks_counter, " total)")
                                synced = False
                                presync = False
                            else:
                                print("Still Sync-ed (Got ", wrong_blocks_counter, " bad blocks on ", blocks_counter, " total)")
                            blocks_counter = 0
                            wrong_blocks_counter = 0
            
            for bytes in bytes_out:
                group_0 = bytes[1] | (bytes[0] << 8)
                group_1 = bytes[3] | (bytes[2] << 8)
                group_2 = bytes[5] | (bytes[4] << 8)
                group_3 = bytes[7] | (bytes[6] << 8)

                group_type = (group_1 >> 12) & 0xf # here is what each one means, e.g. RT is radiotext which is the only one we decode here: ["BASIC", "PIN/SL", "RT", "AID", "CT", "TDC", "IH", "RP", "TMC", "EWS", "___", "___", "___", "___", "EON", "___"]
                AB = (group_1 >> 11 ) & 0x1 # b if 1, a if 0

                #print("group_type:", group_type) # this is essentially message type, i only see type 0 and 2 in my recording
                #print("AB:", AB)

                program_identification = group_0     # "PI"

                program_type = (group_1 >> 5) & 0x1f # "PTY"
                pty = pty_table[program_type][pty_locale]

                pi_area_coverage = (program_identification >> 8) & 0xf
                coverage_area = coverage_area_codes[pi_area_coverage]

                pi_program_reference_number = program_identification & 0xff # just an int

                if first_time:
                    print("PTY:", pty)
                    print("program:", pi_program_reference_number)
                    print("coverage_area:", coverage_area)
                    first_time = False

                if group_type == 2:
                    # when the A/B flag is toggled, flush your current radiotext
                    if radiotext_AB_flag != ((group_1 >> 4) & 0x01):
                        radiotext = [' ']*65
                    radiotext_AB_flag = (group_1 >> 4) & 0x01
                    text_segment_address_code = group_1 & 0x0f
                    if AB:
                        radiotext[text_segment_address_code * 2    ] = chr((group_3 >> 8) & 0xff)
                        radiotext[text_segment_address_code * 2 + 1] = chr(group_3        & 0xff)
                    else:
                        radiotext[text_segment_address_code *4     ] = chr((group_2 >> 8) & 0xff)
                        radiotext[text_segment_address_code * 4 + 1] = chr(group_2        & 0xff)
                        radiotext[text_segment_address_code * 4 + 2] = chr((group_3 >> 8) & 0xff)
                        radiotext[text_segment_address_code * 4 + 3] = chr(group_3        & 0xff)
                    print(''.join(radiotext))
                else:
                    pass
                    #print("unsupported group_type:", group_type)

def update(graph,data_x,data_y,num):
        
        X_mem = shared_memory.SharedMemory(name=data_x)
        Y_mem = shared_memory.SharedMemory(name=data_y)

        X_data = numpy.ndarray((num), dtype=numpy.float64, buffer=X_mem.buf)
        Y_data = numpy.ndarray((num), dtype=numpy.float64, buffer=Y_mem.buf)

        graph.setData(numpy.array(X_data),numpy.array(Y_data))

        X_mem.close()    
        Y_mem.close()   

def update_IQ(graph,Data_IQ,num):
        Data_mem = shared_memory.SharedMemory(name=Data_IQ)
        Data = numpy.ndarray((2,num), dtype=numpy.float64, buffer=Data_mem.buf)
        graph.setData(numpy.array(Data[0]),numpy.array(Data[1]))

        Data_mem.close()    

def update_Samples(graph,Data,num):
        Data_mem = shared_memory.SharedMemory(name=Data)
        Data = numpy.ndarray((num), dtype=numpy.float64, buffer=Data_mem.buf)
        graph.setData(numpy.array(Data))

        Data_mem.close()    

def Graph_Pyqtgraph_Core(Title_1,freq,samp,rds_sz):
    app = pg.mkQApp(Title_1)
    win = pg.GraphicsLayoutWidget(show=True, title=Title_1)
    win.resize(1000,600)
    win.setWindowTitle(Title_1)

    # Enable antialiasing for prettier plots
    pg.setConfigOptions(antialias=True)


    p1 = win.addPlot()
    curve_1 = p1.plot(pen='y')
    p1.setXRange(-1e6, 1e6, padding=0)
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
    curve_3 = p3.plot(pen=None, symbol='o', symbolPen=None, symbolSize=3, symbolBrush=(255, 255, 255, 100))
    p3.setXRange(-2, 2, padding=0)
    p3.setYRange(-2, 2, padding=0)
    p3.enableAutoRange('xy', False)  ## stop auto-scaling after the first data set is plotted


    timer_1 = QtCore.QTimer()
    timer_1.timeout.connect(lambda:   update(curve_1,'FFT_Data_Axis_Graph_Buffer_Global','FFT_Data_Graph_Buffer_Global',samp))
    
    timer_2 = QtCore.QTimer()
    timer_2.timeout.connect(lambda:   update(curve_2,'FFT_FM_Axis_Graph_Buffer_Global','FFT_FM_Graph_Buffer_Global',samp))

    timer_3 = QtCore.QTimer()
    timer_3.timeout.connect(lambda:   update_IQ(curve_3,'RDS_IQ',rds_sz))
    

    timer_1.start()
    timer_2.start()
    timer_3.start()

    pg.exec()

if __name__ == '__main__':

    manager=Manager()

    Manager_RawData=manager.list()
    Manager_FMData=manager.list()
    Manager_RDSData=manager.list()

    Manager_Buffer=manager.list()

    Fm_Size=numpy.log2(Base_Samples * (bufferappend) * (Fm_sample_rate/sample_rate))
    Fm_Size=numpy.floor(Fm_Size)
    Fm_Size=int(2**Fm_Size)

    Rds_Size=numpy.log2(Fm_Size * (RDS_sample_rate/Fm_sample_rate))
    Rds_Size=numpy.floor(Rds_Size)
    Rds_Size=int(2**Rds_Size)
    Rds_Size=int(Rds_Size/16)

    d_size          = numpy.dtype(numpy.float64).itemsize * 2 * Base_Samples
    d_size_fm       = numpy.dtype(numpy.float64).itemsize * Fm_Size
    d_size_samples  = numpy.dtype(numpy.float64).itemsize * Samples
    d_size_rds      = numpy.dtype(numpy.float64).itemsize * 2 * Rds_Size


    RX_Data_ready = Condition()
    FM_Data_Ready = Condition()

    RawData_mem     = shared_memory.SharedMemory(create=True, size=d_size, name='RawData')
    RawData         = numpy.ndarray(shape=(2,Base_Samples), dtype=numpy.float64, buffer=RawData_mem.buf)

    FMData_mem  = shared_memory.SharedMemory(create=True, size=d_size_fm, name='FMData')
    FMData      = numpy.ndarray(shape=(Fm_Size), dtype=numpy.float64, buffer=FMData_mem.buf)

    RDS_IQ_mem   = shared_memory.SharedMemory(create=True, size=d_size_rds, name='RDS_IQ')
    RDS_IQ       = numpy.ndarray(shape=(2,Rds_Size), dtype=numpy.float64, buffer=RDS_IQ_mem.buf)


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
    
    Man_Buff=Process(target=Buffer_Expand, args=(Manager_RawData,Manager_Buffer,bufferappend))

    Fourier_Signal=Process(target=FFT_samples_Graph, args=('RawData','FFT_Data_Graph_Buffer_Global','FFT_Data_Axis_Graph_Buffer_Global',sample_rate,Samples,RX_Data_ready,Base_Samples))
    Fourier_FM=Process(target=FFT_samples_Graph, args=('FMData','FFT_FM_Graph_Buffer_Global','FFT_FM_Axis_Graph_Buffer_Global',Fm_sample_rate,Samples,FM_Data_Ready,Fm_Size))

    Fm=Process(target=FM_demod, args=(sample_rate,Fm_sample_rate,FM_Data_Ready,Manager_Buffer,Manager_FMData,Manager_RDSData,Fm_Size))
    Audio=Process(target=FM_Audio, args=(Fm_sample_rate,"Stereo",Fm_Size,Manager_FMData))
    FM_RadioDataSystem=Process(target=FM_RDS, args=(Fm_sample_rate,RDS_sample_rate,Manager_RDSData,Fm_Size,Rds_Size))
    Graph=Process(target=Graph_Pyqtgraph_Core, args=("FFT",frequency,Samples,Rds_Size))

    Read.start()
    Fourier_Signal.start()
    
    Man_Buff.start()

    Fm.start()
    Fourier_FM.start()
    Audio.start()
    FM_RadioDataSystem.start()

    Graph.start()

    Graph.join()



    # print("hola")