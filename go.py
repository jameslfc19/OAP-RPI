from PyQt4 import QtGui,QtCore
import sys
import ui_main
import numpy as np
import pylab
import time
import pyqtgraph
import requests
import RPi.GPIO as gpio

from envirophat import motion

class AccelerationGraph(QtGui.QMainWindow, ui_main.Ui_MainWindow):
    
    global points, X, Y_ax, Y_ay, Y_az, Y_r, a, inactivity_time, inactive, fallingAccel, impactAccel, movementGracePeriod, sirenLength, siren, movementUpperThreshold, movementLowerThreshold, inactivityPeriod
    
    #vars
    points=250 #number of data points
    movementGracePeriod=2.5
    inactivityPeriod = 3
    fallingAccel=0.4
    sirenLength = 6
    impactAccel = 3
    movementUpperThreshold = 1.3
    movementLowerThreshold = 0.7
    
    #Initialise
    inactivity_time = 0
    inactive = False
    siren = False
    
    #Array of points
    X=np.arange(points)
    Y_ax = np.zeros(points)
    Y_ay = np.zeros(points)
    Y_az = np.zeros(points)
    Y_r = np.zeros(points)
    
    def __init__(self, parent=None):
        #configure graph
        pyqtgraph.setConfigOption('background', 'w') #before loading widget
        super(AccelerationGraph, self).__init__(parent)
        self.setupUi(self)
        self.btnAdd.clicked.connect(self.update)
        self.grPlot.plotItem.showGrid(True, True, 0.7)
        self.chkMore.checked = True
        
        #Setup rpi pins for buzzer and button
        gpio.setmode(gpio.BCM)
        gpio.setup(12, gpio.OUT)
        gpio.setup(22, gpio.IN, pull_up_down = gpio.PUD_DOWN)
        gpio.output(12, True)

    def update(self):
        global inactivity_time, inactive, siren
        
        #acceleration in each dimension
        ax,ay,az =  motion.accelerometer()
        #resultant acceleration
        a = np.sqrt(ax*ax+ay*ay+az*az)
        #Detect if in free fall
        if(a<fallingAccel and not inactive):
            print("falling detected")
            print(a)
            inactivity_time = time.time()+movementGracePeriod
            inactive = True
            
        #Detect if large impact
        if(a>impactAccel and not inactive):
            print("impact detected")
            print(a)
            inactivity_time = time.time()+movementGracePeriod
            inactive = True
            
        #Detect button press and set to inactive and turn buzzer off
        if(gpio.input(22)):
            inactive = False
            gpio.output(12, True)
            print("button press detected, false alarm")
            
        #Wait until after movementGracePeriod then check for any movement
        if(inactivity_time < time.time() and (time.time()-inactivity_time)<=inactivityPeriod and inactive) :
            #print("Timer ended")
            if((a <= movementUpperThreshold) and (a >= movementLowerThreshold)):
               inactive = True
            else:
               inactive = False
               gpio.output(12, True)
               print("movement detected, false alarm")
               
        if(inactivity_time+inactivityPeriod < time.time() and inactive) :
            if(not siren):
                gpio.output(12, False)
                siren = True
            else:
                gpio.output(12, True)
                siren = False
            

        #If no movement detecting after fall, send notification    
        if(inactivity_time+inactivityPeriod < time.time() and (time.time()-inactivity_time-inactivityPeriod)>sirenLength and inactive):
            inactivity_time = 0
            inactive = False
            gpio.output(12, True)
            r = requests.post("https://maker.ifttt.com/trigger/raspberry_pi/with/key/cy_OmR1__iqa_mYUIMAdzY")
            print(r.text)

        
        #print(" ")
        #print(np.around(ax,2),np.around(ay,2),np.around(az,2),"r:",a)
        
        #Move points along x axis
        for i in range(points):
            if(i > 0):
                Y_ax[i-1] = Y_ax[i]
                Y_ay[i-1] = Y_ay[i]
                Y_az[i-1] = Y_az[i]
                Y_r[i-1] = Y_r[i]
            Y_ax[i] = ax
            Y_ay[i] = ay
            Y_az[i] = az
            Y_r[i] = a
          
        #Set color and widths of lines on graph
        C=pyqtgraph.hsvColor(0,alpha=.75)
        pen=pyqtgraph.mkPen(color=C,width=2.5)
        C2=pyqtgraph.hsvColor(0.5,alpha=.75)        
        pen2=pyqtgraph.mkPen(color=C2,width=2.5)
        C3=pyqtgraph.hsvColor(0.8,alpha=.75)        
        pen3=pyqtgraph.mkPen(color=C3,width=2.5)
        C4=pyqtgraph.hsvColor(1,alpha=.75)        
        pen4=pyqtgraph.mkPen(color=C4,width=2.5)  
        
        #self.grPlot.plot(X,Y_ax,pen=pen,clear=True)
        #self.grPlot.plot(X,Y_ay,pen=pen2,clear=False) 
        #self.grPlot.plot(X,Y_az,pen=pen3,clear=False)
        self.grPlot.plot(X,Y_r,pen=pen4,clear=True)                

        #print("update took %.02f ms"%((time.clock()-t1)*1000))
        #if self.chkMore.isChecked():
        QtCore.QTimer.singleShot(50, self.update) # QUICKLY repeat

if __name__=="__main__":
    app = QtGui.QApplication(sys.argv)
    form = AccelerationGraph()
    form.show()
    form.update() #start with something
    app.exec_()
    print("DONE")