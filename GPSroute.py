from gps import *
import time, sys
import threading
import math
import ps_drone # Import PS-Drone

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
        print "Angulo corrigido de {} para 170 por limitacao da biblioteca".format(angulo)
        angulo = 170 #limitacao de biblioteca descrita na documentacao

    if((sentido==False)and(angulo>0)):
        angulo = angulo*(-1)

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
#TESTE
latDest = -13.0013262
longDest = -38.5070985

#velocidadeMax = 1 #equivalente a 5m/s
velocidade = 0.1 #equivalente a 0.5m/s, velocidade utilizada por limitacao da comunicacao do GPS com satelites 

# create the controller
gpsc = GpsController()
# start using drone
drone = ps_drone.Drone()

def startRoute():
    try:
	global velocidade
        arrived = False
        while not arrived:
            if ( len(gpsc.satellites) > 0 ):

                #-------VERIFICA SE POSICAO INICIAL == DESTINO---------------------------------
                latAtual = gpsc.fix.latitude
                longAtual = gpsc.fix.longitude

                distancia = getDistanceByCoordinates(latAtual,longAtual,latDest,longDest)
                if distancia < 2:
                    drone.stop()
                    time.sleep(2)
                    drone.land() #Pousa
		    arrived = True
                    print "Chegou no destino"
                else:
		    #-------LEVANTA VOO-----------------------------------------------------------
                    drone.takeoff()
                    print "Levantando voo..."
                    while drone.NavData["demo"][0][2]: time.sleep(0.1)	#Aguarda takeoff acabar
		    drone.moveUp()
		    time.sleep(5)
		    drone.stop()
		    time.sleep(1)

                    #----------SE MOVE PARA AJUSTE INICIAL DE ANGULO -------------------------

                    latAnt = latAtual
                    longAnt = longAtual

		    drone.setSpeed(velocidade)
                    drone.moveForward()

                    distPercorrida = 0
                    while(distPercorrida<3):
                        latAtual = gpsc.fix.latitude
                        longAtual = gpsc.fix.longitude

                        distPercorrida = getDistanceByCoordinates(latAnt,longAnt,latAtual,longAtual)
		        time.sleep(0.5)

                    drone.stop()
		    time.sleep(3)

                    angulo = getAngle(latAnt,longAnt,latAtual,longAtual,latDest,longDest)

		    #recebe modulo do angulo
                    moduloAngulo = angulo
                    if(angulo<0):
                        moduloAngulo = angulo*(-1)

                    if(moduloAngulo>10):
                        print "Angulo de curvatura: {}".format(angulo)
                        drone.turnAngle(angulo,1,1)
                        time.sleep(4)
		    else:
			print "Segue direto"
					
		    drone.moveForward()

                    #---------INICIA LOOP PARA CORRECAO DE ROTA/VELOCIDADE ATE DESTINO--------
                    while not arrived:

                        latAnt = latAtual
                        longAnt = longAtual

			distPercorrida = 0
			while(distPercorrida<3):			    
			    latAtual = gpsc.fix.latitude
                            longAtual = gpsc.fix.longitude
			    
			    distPercorrida = getDistanceByCoordinates(latAnt,longAnt,latAtual,longAtual)
			    time.sleep(0.5)

                        # Calcula distancia
                        distancia = getDistanceByCoordinates(latAtual,longAtual,latDest,longDest)
			print "Distancia: {}".format(distancia)
                        
			if ((distancia < 2) or (len(gpsc.satellites) == 0)):
                            drone.stop()
                            time.sleep(4)
                            drone.land() #Pousa
                            arrived = True
                            print "Chegou no destino"
                        else:
			    #Calcula variacao da velocidade em relacao a distancia
                            #if distancia < 5:
			    #    velocidade = 0.02*velocidadeMax
                            #    print "Velocidade: 100cm/s"
                            #elif distancia < 10:
			    #	 velocidade = 0.1*velocidadeMax
                            #    print "Velocidade: 500cm/s"
                            #elif distancia < 30:
			    #    velocidade = 0.5*velocidadeMax
                            #    print "Velocidade: 2.5m/s"
			    #else:
			    #    velocidade = velocidadeMax
                            #    print "Velocidade: 5m/s"

			    angulo = getAngle(latAnt,longAnt,latAtual,longAtual,latDest,longDest)
                            
			    #recebe modulo do angulo
			    moduloAngulo = angulo
			    if(angulo<0):
			    	moduloAngulo = angulo*(-1)
						
			    #calcula variacao da velocidade com base no modulo do angulo, dado que foi conferido em testes que 
			    # cada angulo de 60 demora cerca de 1 segundo para ser feito com acuracia maxima
			    #if((moduloAngulo>60)and(moduloAngulo<120)):
			    # 	velocidade = velocidade / 2
			    # 	print "Velocidade dividida pela metade para curvar corretamente"
			    #elif(moduloAngulo>120):
			    # 	velocidade = velocidade / 3
			    # 	print "Velocidade dividida ao terco para curvar corretamente"
			    
			    if(moduloAngulo>10):
				print "Angulo de curvatura: {}".format(angulo)
				drone.turnAngle(angulo,1,1)
			    else:
	                        print "Segue direto"


			    #drone.setSpeed(velocidade)
			    drone.moveForward()

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
        drone.stop()
        time.sleep(4)
        drone.land() #Pousa
        #wait for the tread to finish
        gpsc.join()

    print "Done"

if __name__ == '__main__':
    # start GPS controller
    gpsc.start()

    ##### Suggested clean drone startup sequence #####
    # start drone
    drone.startup()                                                # Connects to drone a$

    drone.reset()                                                  # Sets the drone's st$
    while (drone.getBattery()[0] == - 1):   time.sleep(0.1)        # Wait until the dron$
    print "Battery: "+str(drone.getBattery()[0])+"%  "+str(drone.getBattery()[1])    # G$
    drone.useDemoMode(True)                                        # Just give me 15 bas$
    time.sleep(0.5)                                                # Give it some time t$

    print "Espaco para iniciar"
    stop = False
    while not stop:
        key = drone.getKey()
        if key == " ":
            if drone.NavData["demo"][0][2] and not drone.NavData["demo"][0][3]:
                stop = True
                startRoute()

