#!/usr/bin/env python3.8
# -*- coding: utf-8 -*-
#
import serial, sys, time, math

SceltaComando = { 'on' : 'A', 'off' : 'S', 'req' : 'R' }
    
SceltaProgr =  { 'Non_Cambiare' : '0',
                 'Tutto_Acceso' : '1',
                 'Arcobaleno' : '2',
                 'Scorri_1_LED' : '3',
                 'Sfuma_Arcobaleno' : '4',
                 'Scorri_Un_Colore' : '5' }

SceltaColore = { 'Nero' : '0',
                 'Rosso' : '1',
                 'Arancio' : '2',
                 'Giallo' : '3',
                 'Verde' : '4',
                 'Azzurro' : '5',
                 'Viola' : '6',
                 'Bianco' : '7' }

def ScambioDati(comando):
    STX=2
    ETX=3
    NAK=21
    buf=bytearray(b'000000000000000')
    LENBUF=10
    ser = serial.Serial('/dev/ttyS0', baudrate=4800, timeout=3)  # open serial port
    #print(ser.name, sys.version)       # check which port was really used
    ser.reset_input_buffer()            # clear input buffer
    ser.flush()                         # empty output buffer
    buf[0] = STX
    buf[1:5] = comando
    buf[5:9] = comando
    buf[9] = ETX
    #print(buf[0:11])
    ser.write(buf[0:10])
    buffer=ser.read_until(expected=bytes(chr(ETX), 'ascii'))      # terminator=bytes(chr(ETX), 'ascii'))
    if len(buffer)>1 and buffer[0]==NAK:
        pass
        #print('NAK')
    elif len(buffer)<LENBUF:          #se non si riceve ETX, scade il timeout e si hanno meno (o 0) bytes di quelli attesi
        pass
        #print("Timeout", buffer)
    elif buffer[1:5]==buffer[5:9]:
        pass
        #print('OK', buffer[1:5], buffer[5:9])
    else:
        pass
        #print('Boh', buf, '--')
    ser.close()             # close port


f = open('/home/pi/pippo.txt', 'w')
Comando = SceltaComando[sys.argv[1]]
Programma = SceltaProgr[sys.argv[2]]
Colore = SceltaColore[sys.argv[3]]
Lume = math.floor(float(sys.argv[4])/10)
#print (Comando, Programma, Colore, Lume, file=f)
f.close()

bufmain=bytearray(b'0000000000')
bufmain[0]=ord(Comando)
bufmain[1]=ord(Programma)
bufmain[2]=ord(Colore)
bufmain[3]= Lume | 0x30
ScambioDati(bufmain)
time.sleep(4)


"""
import serial

ser = serial.Serial("/dev/ttyS0", 115200)

def getTFminiData():
    while True:
        count = ser.in_waiting
        if count > 8:
            recv = ser.read(9)
            ser.reset_input_buffer()
            if recv[0] == 'Y' and recv[1] == 'Y': # 0x59 is 'Y'
                low = int(recv[2].encode('hex'), 16)
                high = int(recv[3].encode('hex'), 16)
                distance = low + high * 256
                print(distance)
                


if __name__ == '__main__':
    try:
        if ser.is_open == False:
            ser.open()
        getTFminiData()
    except KeyboardInterrupt:   # Ctrl+C
        if ser != None:
            ser.close()
"""
