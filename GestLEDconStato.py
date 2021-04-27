
import array, machine, utime
from machine import Pin, UART
from rp2 import PIO, StateMachine, asm_pio

# Configure the number of WS2812 LEDs and GPIO driver
NUM_LEDS = 135
GPIO_NUM = 4

BLACK = (0, 0, 0)
RED = (255, 0, 0)
YELLOW = (255, 180, 0)
GREEN = (0, 255, 0)
ORANGE = (255, 90, 0)
BLUE = (0, 0, 255)
PURPLE = (180, 0, 255)
WHITE = (255, 255, 255)
# Colour sequence should be: 0=black,1=red,2=orange etc
COLORS = (BLACK, RED, ORANGE, YELLOW, GREEN, BLUE, PURPLE, WHITE)

STX=2
ETX=3
NAK=21

global Coda
Coda = bytearray('0000')
global CodaReady
CodaReady= 0
brightness = 1

@asm_pio(sideset_init=PIO.OUT_LOW, out_shiftdir=PIO.SHIFT_LEFT, autopull=True, pull_thresh=24)
def ws2812():
    T1 = 2
    T2 = 5
    T3 = 3
    wrap_target()
    label("bitloop")
    out(x, 1)               .side(0)    [T3 - 1]
    jmp(not_x, "do_zero")   .side(1)    [T1 - 1]
    jmp("bitloop")          .side(1)    [T2 - 1]
    label("do_zero")
    nop()                   .side(0)    [T2 - 1]
    wrap()


# Create the StateMachine with the ws2812 program, outputting on pin
sm = StateMachine(0, ws2812, freq=8_000_000, sideset_base=Pin(GPIO_NUM))

# Start the StateMachine, it will wait for data on its FIFO.
sm.active(1)

# Display a pattern on the LEDs via an array of LED RGB values (ogni elemento = INT = 4 bytes)
ar = array.array("I", [0 for _ in range(NUM_LEDS)])

##########################################################################

# UART0 impegna i pin GP0 e GP1 e forse anche 12, 13, 16, 17
uart = UART(0,4800)
ledonboard = Pin(25, Pin.OUT) #LED on board
buf=bytearray('0000000000000000000000000000000000000000')   # lungo almeno len_msg*2 + 2 (STX e ETX)
len_msg=4                 # Lunghezza della parte significativa del messaggio ( es. A132 )
stato=0                   # Stato iniziale della linea seriale
ContaGiri = 0
puntatore=0

def GestSeriale_Sleep(delay_ms):
    """
    Gestione degli sleep (delay) con controllo della Linea seriale
    Gestione seriale per mezzo di macchina a stati finiti.
    Se ricevuti caratteri strani, non risponde, facendo quindi scadere timeout al master (cioè non invia NAK)
    """
    global buf, ledonboard, uart, stato, ContaGiri
    global Coda, CodaReady, puntatore
    
    Start_time= utime.ticks_ms()
    char=0
    while (utime.ticks_diff(utime.ticks_ms(), Start_time)<delay_ms):    #mentre scorre il ritardo chiesto
        utime.sleep_ms(1)
        #Lampeggia il LED on board per dire che sei vivo
        ContaGiri = ContaGiri+1
        if (ContaGiri>1000):       # ogni 1 secondi
            ContaGiri=0
            ledonboard.on()
            utime.sleep_ms(5)
            ledonboard.off()
        if (uart.any() != 0):                                           # e' arrivato un carattere ?
            char = ord(uart.read(1))
            # STATO 0 ------- Attesa di STX -------------------------
            if stato == 0:               
                if (char==STX):
                    stato = 1           #passa nello stato dove attendi altri caratteri
                    buf[0] = char
                    puntatore = 1
            # STATO 1 -------- Attesa ricezione altri caratteri ------------------------
            elif stato == 1:
                if (char==STX):        # controlla se ci siamo sfasati, ricomincia quando arriva STX
                    buf[0]=char
                    puntatore = 1
                elif char == ETX:
                    stato = 0
                    if buf[1:len_msg+1]==buf[len_msg+1:len_msg*2+1]:
                        uart.write(bytes(buf[0:(len_msg+1)*2]))    #ricevuto stringa giusta, rispondi
                        Coda[0:len_msg] = buf[1:len_msg+1]
                        CodaReady +=1               #indica che abbiamo un messaggio in buf
                        buf=bytearray('000000000000000000000000000000')
                else:
                    buf[puntatore] = char
                    puntatore +=1
        
def pixels_show():
    """
    Emette l'array ar aggiustandolo con la luminosità
    """
    dimmer_ar = array.array("I", [0 for _ in range(NUM_LEDS)])
    for i,c in enumerate(ar):
        r = int(((c >> 8) & 0xFF) * brightness)
        g = int(((c >> 16) & 0xFF) * brightness)
        b = int((c & 0xFF) * brightness)
        dimmer_ar[i] = (g<<16) + (r<<8) + b
    sm.put(dimmer_ar, 8)
    GestSeriale_Sleep(10)

def colora_un_pixel(i, color):
    """
    imposta una cella (LED) con il colore richiesto
    """
    ar[i] = (color[1]<<16) + (color[0]<<8) + color[2]

def tutto_acceso(color):
    """
    colora ogni pixel con il colore richiesto
    """
    for i in range(len(ar)):
        colora_un_pixel(i, color)
    pixels_show()

def scorri_1_LED(color, wait):
    while (True):
        # fai scorrere avanti e indietro un pixel con colore dato
        for ii in range(1, NUM_LEDS):
            colora_un_pixel(ii, color)
            GestSeriale_Sleep(wait)
            colora_un_pixel(ii-1, BLACK)
            pixels_show()
            if (CodaReady >0): break      # Continua fino a che non arriva un nuovo comando
        for ii in range(NUM_LEDS-2, -1,-1):
            colora_un_pixel(ii, color)
            GestSeriale_Sleep(wait)
            colora_un_pixel(ii+1, BLACK)
            pixels_show()
            if (CodaReady >0): break      # Continua fino a che non arriva un nuovo comando
        colora_un_pixel(0,BLACK)
        pixels_show()
        if (CodaReady >0): break      # Continua fino a che non arriva un nuovo comando

def scorri_1_colore(color, wait):
    while (True):
        # riempi in progressione, avanti e indietro, la striscia con colore dato
        for i in range(NUM_LEDS):
            colora_un_pixel(i, color)
            GestSeriale_Sleep(wait)
            pixels_show()
            if (CodaReady >0): break      # Continua fino a che non arriva un nuovo comando
        for i in range(NUM_LEDS):
            colora_un_pixel(i, BLACK)
            GestSeriale_Sleep(wait)
            pixels_show()
            if (CodaReady >0): break      # Continua fino a che non arriva un nuovo comando
        for i in range(NUM_LEDS-1, 0,-1):
            colora_un_pixel(i, color)
            GestSeriale_Sleep(wait)
            pixels_show()
            if (CodaReady >0): break      # Continua fino a che non arriva un nuovo comando
        colora_un_pixel(0,color)
        pixels_show()
        for i in range(NUM_LEDS-1, 0,-1):
            colora_un_pixel(i, BLACK)
            GestSeriale_Sleep(wait)
            pixels_show()
            if (CodaReady >0): break      # Continua fino a che non arriva un nuovo comando
        if (CodaReady >0): break      # Continua fino a che non arriva un nuovo comando

def arcobaleno():
# colora gruppi di led come un arcobaleno e fallo scorrere
    base=0
    while (True):
        n= NUM_LEDS/(len(COLORS)-1)
        base=0
        for k in range(base, NUM_LEDS+base):
            for i in range(len(ar)):
                j=int(i//n)+1               #punta al colore escludendo il nero
                colora_un_pixel(((k+i) % NUM_LEDS), COLORS[j])
            GestSeriale_Sleep(50)
            pixels_show()
            base+=1
            if (CodaReady >0): break      # Continua fino a che non arriva un nuovo comando
        if (CodaReady >0): break      # Continua fino a che non arriva un nuovo comando
# alternativa con 1 LED che cambia colore
#        for k in range(NUM_LEDS):
#            colora_un_pixel((k+base) % NUM_LEDS , COLORS[k % len(COLORS)])
#        pixels_show()
#        GestSeriale_Sleep(500)
#        base = (base + 1) % NUM_LEDS
#        if (CodaReady >0): break      # Continua fino a che non arriva un nuovo comando


def incr_decr_base_compo(base_compo, flag):
    if (flag !=  0): 
        if (base_compo<255):
            base_compo +=1
    else:
        if (base_compo>0):
            base_compo -=1
    return (base_compo)

def sfuma_arcobaleno():
    # colora tutti i led sfumando i colori
    rgb = [0, 0, 0]
    progr = (1,3,2,6,7,5,4,0)      # sequenza dei colori secondo il codice Gray per sfumare gentilmente
    index=0
    while (True):
        for i in range(255):
            #red
            flag=progr[index] & 4
            rgb[0]=incr_decr_base_compo(rgb[0], flag)
            #green
            flag=progr[index] & 2
            rgb[1]=incr_decr_base_compo(rgb[1], flag)
            #red
            flag=progr[index] & 1
            rgb[2]=incr_decr_base_compo(rgb[2], flag)
            for i in range(len(ar)):
                colora_un_pixel(i, rgb)
            pixels_show()
            GestSeriale_Sleep(10)
            if (CodaReady >0): break      # Continua fino a che non arriva un nuovo comando
        index =(index+1)%7             # CIcla su 7 colori (se %8, allora include anche lo spegnimento tra rosso e blu)
        if (CodaReady >0): break          # Continua fino a che non arriva un nuovo comando

# Startup = spegni tutto
color_index= 0
brightness= 0
mem_command= ord('1')           # se arriva "ripeti comando" allo startup, simula una accensione totale
tutto_acceso(COLORS[color_index])
pixels_show()
#_thread.start_new_thread(GestSeriale_thread, ())

# loop permanente in attesa di comando dal master su linea seriale 0
while (True):
    if (CodaReady >0):
        CodaReady -=1
        color_index= Coda[2] & 0xF             # quindi imposta l'indice del colore e luminosita
        brightness= (Coda[3] & 0xF)/10
        if (Coda[0]==ord('A')):
            if (Coda[1]==ord('0')):          # ripeti ultimo comando con colore o lum diversi
                Coda[1] = mem_command
            if (Coda[1]==ord('1')):          # e poi scegli il programma
                tutto_acceso(COLORS[color_index])
            elif (Coda[1]==ord('2')):
                arcobaleno()
            elif (Coda[1]==ord('3')):
                scorri_1_LED(COLORS[color_index], 10)
                tutto_acceso(COLORS[0])
            elif (Coda[1]==ord('4')):
                sfuma_arcobaleno()
                tutto_acceso(COLORS[0])
            elif (Coda[1]==ord('5')):
                scorri_1_colore(COLORS[color_index], 10)
                tutto_acceso(COLORS[0])
            mem_command=Coda[1]              # memorizza il comando se poi si cambia solo colore o luminosita
        else:
            color_index = 0                      # ricevuto "Spegni" -> accendi con NERO
            tutto_acceso(COLORS[color_index])
    GestSeriale_Sleep(200)
