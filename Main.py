import threading
import pigpio
import multiprocessing

import BluetoothConnection
import LightControl

class Controller():
    def __init__(self):
        self.pi = pigpio.pi()
        
        self.lightQueue = multiprocessing.Queue()
        self.stateQueue = multiprocessing.Queue()
        
        self.bluetoothConnection = BluetoothConnection.BluetoothConnection(self.lightQueue, self.stateQueue)
        self.lightControl = LightControl.LightControl(self.pi, self.lightQueue, self.stateQueue)        
        self.bluetoothConnection.start()
        self.lightControl.start()

if __name__ == '__main__':
    controller = Controller()
