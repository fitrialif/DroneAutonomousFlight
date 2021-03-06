from gps import *
import time, sys
import threading
import math

class GpsController(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.gpsd = gps(mode=WATCH_ENABLE) #starting the stream of info
        self.running = False

    def run(self):
        self.running = True
        while self.running:
            # grab EACH set of gpsd info to clear the buffer
            self.gpsd.next()

    def stopController(self):
        self.running = False

    @property
    def fix(self):
        return self.gpsd.fix

    @property
    def utc(self):
        return self.gpsd.utc

    @property
    def satellites(self):
        return self.gpsd.satellites

def getDistanceByCoordinates(latI,longI,latF,longF):
    earthRadius = 3958.75
    latDiff = math.radians(latF-latI)
    lngDiff = math.radians(longF-longI)
    a = math.sin(latDiff /2) * math.sin(latDiff /2) + math.cos(math.radians(latI)) * math.cos(math.radians(latF)) * math.sin(lngDiff /2) * math.sin(lngDiff /2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    distance = earthRadius * c

    meterConversion = 1609

    distance = distance * meterConversion
    print "Distancia: ",distance

    return distance
#			Teste
#5570 m
#Coliseu
#-12.966275, -38.403925
#Farol de Itapua
#-12.957065, -38.353690

def getDestinoDirection(latI,longI,latA,longA,latF,longF):
    return ( longF - longI ) * ( latA - latI ) - ( latF - latI ) * ( longA - longI )

def getCoefAng(latI,longI,latF,longF):
    if (longI==longF):
        longF = longF + 0.000001
    return ( ( latF - latI ) / ( longF - longI ) )

def getAngle(latI,longI,latA,longA,latF,longF):
	
    direction = getDestinoDirection(latI,longI,latA,longA,latF,longF)

    sentido = True #Direita = True / Esquerda = False
    if (direction == 0):
    	return 0
    elif (direction < 0):
    	sentido = False
		
    coefAngI = getCoefAng(latI, longI, latA, longA)
    coefAngF = getCoefAng(latA, longA, latF, longF)
	
    tangAngulo = ( ( coefAngI - coefAngF ) / ( 1 + ( coefAngI * coefAngF ) ) )

    if(tangAngulo < 0):
        tangAngulo = tangAngulo*(-1)

    angulo = math.degrees(math.atan(tangAngulo))

    #se o ponto de destino for mais perto do inicial que o atual
    #usar complemento do angulo em 180
    distFim = getDistanceByCoordinates(latI,longI,latF,longF)
    distAtual = getDistanceByCoordinates(latA,longA,latF,longF)
	
    if(distFim < distAtual):
	angulo = 180-angulo
	
    if(angulo>170):
        print "Angulo corrigido de ",angulo," para 170 por limitacao da biblioteca"
        angulo = 170 #limitacao de biblioteca descrita na documentacao

    if((sentido==False)and(angulo>0)):
        angulo = angulo*(-1)

    print "Angulo de curvatura: ",angulo

    return angulo

#---------------COORDENADAS DO DESTINO----------------
#CASA
#latDest = -12.893525
#longDest = -38.459263
#IGREJINHA
#latDest = -12.901878
#longDest = -38.457580
#UFBA
#latDest = -13.002755
#longDest = -38.506940
#TCA
latDest = -12.988789
longDest = -38.520005
#-----------------------------------------------------

if __name__ == '__main__':
    # create the controller
    gpsc = GpsController()
    try:
        # start GPS controller
        gpsc.start()

        ##### Suggested clean drone startup sequence #####
        # start drone
        print "Inicializa Drone"
		
	print "Battery: x"    # Gives a battery-status
        
	print "Buscando satelites..."
        while True:
            if ( len(gpsc.satellites) > 0 ):

                #-------LEVANTA VoO-----------------------------------------------------------
                print "Levantando voo..."

                #-------VERIFICA SE POSIcaO INICIAL == DESTINO---------------------------------
                print "Verifica direcao e sentido do drone"
		
		latAtual = gpsc.fix.latitude
                longAtual = gpsc.fix.longitude
		
		#teste
		#latAnt = -13.000805
		#longAnt =  -38.507584
	
                distancia = getDistanceByCoordinates(latAtual,longAtual,latDest,longDest)
                if distancia < 1:
                    print "Chegou no destino"
                    print "drone para"
                    time.sleep(1)
		    print "drone pousa"
                else:
                    #----------SE MOVE PARA AJUSTE INICIAL DE ANGULO -------------------------

                    latAnt = latAtual
                    longAnt = longAtual

                    time.sleep(1)

                    latAtual = gpsc.fix.latitude
                    longAtual = gpsc.fix.longitude
		
                    angulo = getAngle(latAnt,longAnt,latAtual,longAtual,latDest,longDest)
		    time.sleep(1)
                    #---------INICIA LOOP PARA CORREcaO DE ROTA/VELOCIDADE ATe DESTINO
                    arrived = False
                    while not arrived:

                        latAnt = latAtual
                        longAnt = longAtual

                        latAtual = gpsc.fix.latitude
                        longAtual = gpsc.fix.longitude

                        # Calcula distancia
                        distancia = getDistanceByCoordinates(latAtual,longAtual,latDest,longDest)
                        if distancia < 1:
                            print "drone para"
                            time.sleep(1)
                            print "drone pousa"
                            arrived = True
                            print "Chegou no destino"
                        else:
                            # Calcula Velocidade
                            if distancia < 5:
                                print "Velocidade: 2%"

                            elif distancia < 10:
                                print "Velocidade: 10%"

                            elif distancia < 30:
                                print "Velocidade: 50%"

                            else:
                                print "Velocidade: 100%"

                            angulo = getAngle(latAnt,longAnt,latAtual,longAtual,latDest,longDest)

                            time.sleep(2)
            else:
                print "Procurando por satelites..."
            time.sleep(3)

    #Ctrl C
    except KeyboardInterrupt:
        print "User cancelled"

    #Error
    except:
        print "Unexpected error:", sys.exc_info()[0]
        raise

    finally:
        print "Stopping gps controller"
        gpsc.stopController()
        print "Pousando drone"
        time.sleep(1)
        #wait for the tread to finish
        gpsc.join()

    print "Done"
