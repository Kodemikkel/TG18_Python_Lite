import threading
import pigpio
import time

class LightControl(threading.Thread):
    def __init__(self, pi, receiveQueue, stateQueue):
        print("Initializing LightControl thread")
        threading.Thread.__init__(self)
        # Initialize all members
        self.pi = pi
        self.pinR = 17 # Physical pin 11
        self.pinG = 27 # Physical pin 13
        self.pinB = 22 # Physical pin 15

        self.rVal = 0
        self.gVal = 0
        self.bVal = 0
        self.aVal = 0
        self.mode = ""
        self.enabled = True

        # Set pins to output mode
        self.pi.set_mode(self.pinR, pigpio.OUTPUT)
        self.pi.set_mode(self.pinG, pigpio.OUTPUT)
        self.pi.set_mode(self.pinB, pigpio.OUTPUT)

        # Set the PWM frequency to be used
        self.pi.set_PWM_frequency(self.pinR, 200)
        self.pi.set_PWM_frequency(self.pinG, 200)
        self.pi.set_PWM_frequency(self.pinB, 200)

        # Initialize all pins with a dutycycle of 0 = off
        self.pi.set_PWM_dutycycle(self.pinR, 0)
        self.pi.set_PWM_dutycycle(self.pinG, 0)
        self.pi.set_PWM_dutycycle(self.pinB, 0)
        
        self.functionThread = ""
        self.receiveQueue = receiveQueue
        self.stateQueue = stateQueue

        print("LightControl thread initialized")

    def run(self):
        print("Starting LightControl thread")
        while True:
            data = self.receiveQueue.get()
            if data[0] == "2": # Indicates data is for us
                if data[2] == "G": # Indicates flash
                    self.setMode("flash")
                    self.aVal = int(data[8:10], 16)
                elif data[2] == "H": # Indicates strobe
                    self.setMode("strobe")
                    self.aVal = int(data[8:10], 16)
                elif data[2] == "I": # Indicates fade
                    self.setMode("fade")
                    self.aVal = int(data[8:10], 16)
                elif data[2] == "J": # Indicates smooth
                    self.setMode("smooth")
                    self.aVal = int(data[8:10], 16)
                elif data[2] == "K": # Indicates on
                    self.enabled = True
                elif data[2] == "L": # Indicates off
                    self.enabled = False
                else: # If none of the above, default to solid color
                    self.setColor(data[2:4], data[4:6], data[6:8], data[8:10])
                    self.setMode("solid")
            elif data[0] == "0": # Indicates data is for some internal message
                if data[2] == "A": # Indicates user has disconnected
                    self.stateQueue.put(self.getMode())

    def setColor(self, red, green, blue, alpha):
        self.aVal = int(alpha, 16)
        self.rVal = int(red, 16)
        self.gVal = int(green, 16)
        self.bVal = int(blue, 16)

    # Return the currently selected mode or color in hex
    def getMode(self):
        rReturn = "0x{:02x}".format(int(self.rVal))[2:]
        gReturn = "0x{:02x}".format(int(self.gVal))[2:]
        bReturn = "0x{:02x}".format(int(self.bVal))[2:]
        aReturn = "0x{:02x}".format(int(self.aVal))[2:]
        
        if self.mode == "flash":
            return ";2_G00000" + aReturn
        elif self.mode == "strobe":
            return ";2_H00000" + aReturn
        elif self.mode == "fade":
            return ";2_I00000" + aReturn
        elif self.mode == "smooth":
            return ";2_J00000" + aReturn
        else:
            return ";2_" + rReturn + gReturn + bReturn + aReturn

    def setMode(self, modeToSet):
        # Check that the mode requested is not the same as the one active
        if self.mode != modeToSet:
            self.mode = modeToSet

            # If there is a thread running, we want to wait until it stops
            if self.functionThread != "" and self.functionThread.isAlive():
                print("Waiting for existing thread to die...")
                self.functionThread.join()
                print("Thread dead, continuing")

            # Create the thread depending on what function is requested
            if self.mode == "flash":
                self.functionThread = threading.Thread(target=self.flash)
            elif self.mode == "strobe":
                self.functionThread = threading.Thread(target=self.strobe)
            elif self.mode == "fade":
                self.functionThread = threading.Thread(target=self.fade)
            elif self.mode == "smooth":
                self.functionThread = threading.Thread(target=self.smooth)
            elif self.mode == "solid":
                self.functionThread = threading.Thread(target=self.solid)
                
            # Start the thread
            self.functionThread.start()

    # Methods for the different color settings
    def solid(self):
        rValTmp = 0
        gValTmp = 0
        bValTmp = 0
        aValTmp = 0
        aValMult = 0
        first = True
        while self.mode == "solid":
            if not self.enabled: # Check if the LEDs should be enabled or not
                self.pi.set_PWM_dutycycle(self.pinR, 0)
                self.pi.set_PWM_dutycycle(self.pinG, 0)
                self.pi.set_PWM_dutycycle(self.pinB, 0)
                first = False
            else:
                if not first:
                    aValMult = self.aVal / 255
                    self.pi.set_PWM_dutycycle(self.pinR, self.rVal * aValMult)
                    self.pi.set_PWM_dutycycle(self.pinG, self.gVal * aValMult)
                    self.pi.set_PWM_dutycycle(self.pinB, self.bVal * aValMult)
                    first = True
                else:
                    if rValTmp != self.rVal:
                        self.pi.set_PWM_dutycycle(self.pinR, self.rVal * aValMult)
                        rValTmp = self.rVal
                    if gValTmp != self.gVal:
                        self.pi.set_PWM_dutycycle(self.pinG, self.gVal * aValMult)
                        gValTmp = self.gVal
                    if bValTmp != self.bVal:
                        self.pi.set_PWM_dutycycle(self.pinB, self.bVal * aValMult)
                        bValTmp = self.bVal
                    if aValTmp != self.aVal:
                        aValMult = self.aVal / 255.0
                        self.pi.set_PWM_dutycycle(self.pinR, self.rVal * aValMult)
                        self.pi.set_PWM_dutycycle(self.pinG, self.gVal * aValMult)
                        self.pi.set_PWM_dutycycle(self.pinB, self.bVal * aValMult)
                        aValTmp = self.aVal
                    time.sleep(.01)

    def flash(self):
        sleepTime = 0
        while self.mode == "flash":
            if not self.enabled: # Check if the LEDs should be enabled or not
                self.pi.set_PWM_dutycycle(self.pinR, 0)
                self.pi.set_PWM_dutycycle(self.pinG, 0)
                self.pi.set_PWM_dutycycle(self.pinB, 0)
            else:
                # Check if we have changed the alpha value
                if sleepTime != (((self.aVal - 0) * (.5 - .1)) / (255 - 0) + .05):
                    sleepTime = (((self.aVal - 0) * (.5 - .1)) / (255 - 0) + .05)

                # Check if we have left flash
                if self.mode != "flash":
                    self.pi.set_PWM_dutycycle(self.pinR, 0)
                    self.pi.set_PWM_dutycycle(self.pinG, 0)
                    self.pi.set_PWM_dutycycle(self.pinB, 0)
                    return

                # Check if we have disabled the LEDs
                if not self.enabled:
                    continue

                # Set red
                self.pi.set_PWM_dutycycle(self.pinR, 255)
                self.pi.set_PWM_dutycycle(self.pinG, 0)
                self.pi.set_PWM_dutycycle(self.pinB, 0)
                time.sleep(sleepTime)

                # Check if we have changed the alpha value
                if sleepTime != (((self.aVal - 0) * (.5 - .1)) / (255 - 0) + .05):
                    sleepTime = (((self.aVal - 0) * (.5 - .1)) / (255 - 0) + .05)

                # Check if we have left flash
                if self.mode != "flash":
                    self.pi.set_PWM_dutycycle(self.pinR, 0)
                    self.pi.set_PWM_dutycycle(self.pinG, 0)
                    self.pi.set_PWM_dutycycle(self.pinB, 0)
                    return

                # Check if we have disabled the LEDs
                if not self.enabled:
                    continue

                # Set green
                self.pi.set_PWM_dutycycle(self.pinR, 0)
                self.pi.set_PWM_dutycycle(self.pinG, 255)
                self.pi.set_PWM_dutycycle(self.pinB, 0)
                time.sleep(sleepTime)

                # Check if we have changed the alpha value
                if sleepTime != (((self.aVal - 0) * (.5 - .1)) / (255 - 0) + .05):
                    sleepTime = (((self.aVal - 0) * (.5 - .1)) / (255 - 0) + .05)

                # Check if we have left flash
                if self.mode != "flash":
                    self.pi.set_PWM_dutycycle(self.pinR, 0)
                    self.pi.set_PWM_dutycycle(self.pinG, 0)
                    self.pi.set_PWM_dutycycle(self.pinB, 0)
                    return

                # Check if we have disabled the LEDs
                if not self.enabled:
                    continue

                # Set blue
                self.pi.set_PWM_dutycycle(self.pinR, 0)
                self.pi.set_PWM_dutycycle(self.pinG, 0)
                self.pi.set_PWM_dutycycle(self.pinB, 255)
                time.sleep(sleepTime)

                # Check if we have changed the alpha value
                if sleepTime != (((self.aVal - 0) * (.5 - .1)) / (255 - 0) + .05):
                    sleepTime = (((self.aVal - 0) * (.5 - .1)) / (255 - 0) + .05)

                # Check if we have left flash
                if self.mode != "flash":
                    self.pi.set_PWM_dutycycle(self.pinR, 0)
                    self.pi.set_PWM_dutycycle(self.pinG, 0)
                    self.pi.set_PWM_dutycycle(self.pinB, 0)
                    return

                # Check if we have disabled the LEDs
                if not self.enabled:
                    continue

                # Set red and green
                self.pi.set_PWM_dutycycle(self.pinR, 255)
                self.pi.set_PWM_dutycycle(self.pinG, 255)
                self.pi.set_PWM_dutycycle(self.pinB, 0)
                time.sleep(sleepTime)

                # Check if we have changed the alpha value
                if sleepTime != (((self.aVal - 0) * (.5 - .1)) / (255 - 0) + .05):
                    sleepTime = (((self.aVal - 0) * (.5 - .1)) / (255 - 0) + .05)

                # Check if we have left flash
                if self.mode != "flash":
                    self.pi.set_PWM_dutycycle(self.pinR, 0)
                    self.pi.set_PWM_dutycycle(self.pinG, 0)
                    self.pi.set_PWM_dutycycle(self.pinB, 0)
                    return

                # Check if we have disabled the LEDs
                if not self.enabled:
                    continue

                # Set red and blue
                self.pi.set_PWM_dutycycle(self.pinR, 255)
                self.pi.set_PWM_dutycycle(self.pinG, 0)
                self.pi.set_PWM_dutycycle(self.pinB, 255)
                time.sleep(sleepTime)

                # Check if we have changed the alpha value
                if sleepTime != (((self.aVal - 0) * (.5 - .1)) / (255 - 0) + .05):
                    sleepTime = (((self.aVal - 0) * (.5 - .1)) / (255 - 0) + .05)

                # Check if we have left flash
                if self.mode != "flash":
                    self.pi.set_PWM_dutycycle(self.pinR, 0)
                    self.pi.set_PWM_dutycycle(self.pinG, 0)
                    self.pi.set_PWM_dutycycle(self.pinB, 0)
                    return

                # Check if we have disabled the LEDs
                if not self.enabled:
                    continue

                # Set green and blue
                self.pi.set_PWM_dutycycle(self.pinR, 0)
                self.pi.set_PWM_dutycycle(self.pinG, 255)
                self.pi.set_PWM_dutycycle(self.pinB, 255)
                time.sleep(sleepTime)

                # Check if we have changed the alpha value
                if sleepTime != (((self.aVal - 0) * (.5 - .1)) / (255 - 0) + .05):
                    sleepTime = (((self.aVal - 0) * (.5 - .1)) / (255 - 0) + .05)

                # Check if we have left flash
                if self.mode != "flash":
                    self.pi.set_PWM_dutycycle(self.pinR, 0)
                    self.pi.set_PWM_dutycycle(self.pinG, 0)
                    self.pi.set_PWM_dutycycle(self.pinB, 0)
                    return

                # Check if we have disabled the LEDs
                if not self.enabled:
                    continue

                # Set red, green and blue
                self.pi.set_PWM_dutycycle(self.pinR, 255)
                self.pi.set_PWM_dutycycle(self.pinG, 255)
                self.pi.set_PWM_dutycycle(self.pinB, 255)
                time.sleep(sleepTime)
                

    def strobe(self):
        sleepTime = 0
        while self.mode == "strobe":
            if not self.enabled: # Check if the LEDs should be enabled or not
                self.pi.set_PWM_dutycycle(self.pinR, 0)
                self.pi.set_PWM_dutycycle(self.pinG, 0)
                self.pi.set_PWM_dutycycle(self.pinB, 0)
            else:
                for strobeVal in range(0, 255, 1):
                    # Check if we have changed the alpha value
                    if sleepTime != (((self.aVal - 0) * (.8 - .05)) / (255 - 0) + .05):
                        sleepTime = (((self.aVal - 0) * (.8 - .05)) / (255 - 0) + .05)

                    # Check if we have left strobe
                    if self.mode != "strobe":
                        self.pi.set_PWM_dutycycle(self.pinR, 0)
                        self.pi.set_PWM_dutycycle(self.pinG, 0)
                        self.pi.set_PWM_dutycycle(self.pinB, 0)
                        return

                    # Check if we have disabled the LEDs
                    if not self.enabled:
                        break

                    # Set the dutycycle
                    self.pi.set_PWM_dutycycle(self.pinR, strobeVal)
                    self.pi.set_PWM_dutycycle(self.pinG, strobeVal)
                    self.pi.set_PWM_dutycycle(self.pinB, strobeVal)
                    time.sleep(sleepTime * .01)

                # Check if we have disabled the LEDs
                if not self.enabled:
                    continue
                    
                time.sleep(sleepTime)
                
                for strobeVal in range(255, -1, -1):
                    # Check if we have changed the alpha value
                    if sleepTime != (((self.aVal - 0) * (.8 - .05)) / (255 - 0) + .05):
                        sleepTime = (((self.aVal - 0) * (.8 - .05)) / (255 - 0) + .05)

                    # Check if we have left strobe
                    if self.mode != "strobe":
                        self.pi.set_PWM_dutycycle(self.pinR, 0)
                        self.pi.set_PWM_dutycycle(self.pinG, 0)
                        self.pi.set_PWM_dutycycle(self.pinB, 0)
                        return

                    # Check if we have disabled the LEDs
                    if not self.enabled:
                        break

                    # Set the dutycycle
                    self.pi.set_PWM_dutycycle(self.pinR, strobeVal)
                    self.pi.set_PWM_dutycycle(self.pinG, strobeVal)
                    self.pi.set_PWM_dutycycle(self.pinB, strobeVal)
                    time.sleep(sleepTime * .01)

                # Check if we have disabled the LEDs
                if not self.enabled:
                    continue
                    
                time.sleep(sleepTime)

    def fade(self):
        sleepTime = 0
        
        # Reset all pins
        self.pi.set_PWM_dutycycle(self.pinR, 0)
        self.pi.set_PWM_dutycycle(self.pinG, 0)
        self.pi.set_PWM_dutycycle(self.pinB, 0)
        
        while self.mode == "fade":
            if not self.enabled: # Check if the LEDs should be enabled or not
                self.pi.set_PWM_dutycycle(self.pinR, 0)
                self.pi.set_PWM_dutycycle(self.pinG, 0)
                self.pi.set_PWM_dutycycle(self.pinB, 0)
            else:
                for fadeVal in range(0, 255, 1):
                    # Check if we have changed the alpha value
                    if sleepTime != (((self.aVal - 0) * (1.8 - .05)) / (255 - 0) + .05):
                        sleepTime = (((self.aVal - 0) * (1.8 - .05)) / (255 - 0) + .05)

                    # Check if we have left fade
                    if self.mode != "fade":
                        self.pi.set_PWM_dutycycle(self.pinR, 0)
                        self.pi.set_PWM_dutycycle(self.pinG, 0)
                        self.pi.set_PWM_dutycycle(self.pinB, 0)
                        return

                    # Check if we have disabled the LEDs
                    if not self.enabled:
                        break

                    # Increase red
                    self.pi.set_PWM_dutycycle(self.pinR, fadeVal)
                    time.sleep(sleepTime * .01)

                # Check if we have disabled the LEDs
                if not self.enabled:
                    continue
                
                time.sleep(sleepTime * .5)

                for fadeVal in range(255, -1, -1):
                    # Check if we have changed the alpha value
                    if sleepTime != (((self.aVal - 0) * (1.8 - .05)) / (255 - 0) + .05):
                        sleepTime = (((self.aVal - 0) * (1.8 - .05)) / (255 - 0) + .05)

                    # Check if we have left fade
                    if self.mode != "fade":
                        self.pi.set_PWM_dutycycle(self.pinR, 0)
                        self.pi.set_PWM_dutycycle(self.pinG, 0)
                        self.pi.set_PWM_dutycycle(self.pinB, 0)
                        return

                    # Check if we have disabled the LEDs
                    if not self.enabled:
                        break

                    # Decrease red
                    self.pi.set_PWM_dutycycle(self.pinR, fadeVal)
                    time.sleep(sleepTime * .01)

                # Check if we have disabled the LEDs
                if not self.enabled:
                    continue
                    
                time.sleep(sleepTime * .5)

                for fadeVal in range(0, 255, 1):
                    # Check if we have changed the alpha value
                    if sleepTime != (((self.aVal - 0) * (1.8 - .05)) / (255 - 0) + .05):
                        sleepTime = (((self.aVal - 0) * (1.8 - .05)) / (255 - 0) + .05)

                    # Check if we have left fade
                    if self.mode != "fade":
                        self.pi.set_PWM_dutycycle(self.pinR, 0)
                        self.pi.set_PWM_dutycycle(self.pinG, 0)
                        self.pi.set_PWM_dutycycle(self.pinB, 0)
                        return

                    # Check if we have disabled the LEDs
                    if not self.enabled:
                        break

                    # Increase green
                    self.pi.set_PWM_dutycycle(self.pinG, fadeVal)
                    time.sleep(sleepTime * .01)

                # Check if we have disabled the LEDs
                if not self.enabled:
                    continue
                    
                time.sleep(sleepTime * .5)

                for fadeVal in range(255, -1, -1):
                    # Check if we have changed the alpha value
                    if sleepTime != (((self.aVal - 0) * (1.8 - .05)) / (255 - 0) + .05):
                        sleepTime = (((self.aVal - 0) * (1.8 - .05)) / (255 - 0) + .05)

                    # Check if we have left fade
                    if self.mode != "fade":
                        self.pi.set_PWM_dutycycle(self.pinR, 0)
                        self.pi.set_PWM_dutycycle(self.pinG, 0)
                        self.pi.set_PWM_dutycycle(self.pinB, 0)
                        return

                    # Check if we have disabled the LEDs
                    if not self.enabled:
                        break

                    # Decrease green
                    self.pi.set_PWM_dutycycle(self.pinG, fadeVal)
                    time.sleep(sleepTime * .01)

                # Check if we have disabled the LEDs
                if not self.enabled:
                    continue
                    
                time.sleep(sleepTime * .5)

                for fadeVal in range(0, 255, 1):
                    # Check if we have changed the alpha value
                    if sleepTime != (((self.aVal - 0) * (1.8 - .05)) / (255 - 0) + .05):
                        sleepTime = (((self.aVal - 0) * (1.8 - .05)) / (255 - 0) + .05)

                    # Check if we have left fade
                    if self.mode != "fade":
                        self.pi.set_PWM_dutycycle(self.pinR, 0)
                        self.pi.set_PWM_dutycycle(self.pinG, 0)
                        self.pi.set_PWM_dutycycle(self.pinB, 0)
                        return

                    # Check if we have disabled the LEDs
                    if not self.enabled:
                        break

                    # Increase blue
                    self.pi.set_PWM_dutycycle(self.pinB, fadeVal)
                    time.sleep(sleepTime * .01)

                # Check if we have disabled the LEDs
                if not self.enabled:
                    continue
                    
                time.sleep(sleepTime * .5)

                for fadeVal in range(255, -1, -1):
                    # Check if we have changed the alpha value
                    if sleepTime != (((self.aVal - 0) * (1.8 - .05)) / (255 - 0) + .05):
                        sleepTime = (((self.aVal - 0) * (1.8 - .05)) / (255 - 0) + .05)

                    # Check if we have left fade
                    if self.mode != "fade":
                        self.pi.set_PWM_dutycycle(self.pinR, 0)
                        self.pi.set_PWM_dutycycle(self.pinG, 0)
                        self.pi.set_PWM_dutycycle(self.pinB, 0)
                        return

                    # Check if we have disabled the LEDs
                    if not self.enabled:
                        break

                    # Decrease blue
                    self.pi.set_PWM_dutycycle(self.pinB, fadeVal)
                    time.sleep(sleepTime * .01)

                # Check if we have disabled the LEDs
                if not self.enabled:
                    continue
                
                time.sleep(sleepTime * .5)
            
    def smooth(self):
        sleepTime = 0
        
        # Reset all pins
        self.pi.set_PWM_dutycycle(self.pinR, 255)
        self.pi.set_PWM_dutycycle(self.pinG, 0)
        self.pi.set_PWM_dutycycle(self.pinB, 0)
        
        while self.mode == "smooth":
            if not self.enabled: # Check if the LEDs should be enabled or not
                self.pi.set_PWM_dutycycle(self.pinR, 0)
                self.pi.set_PWM_dutycycle(self.pinG, 0)
                self.pi.set_PWM_dutycycle(self.pinB, 0)
            else:
                for smoothVal in range(0, 255, 1):
                    # Check if we have changed the alpha value
                    if sleepTime != (((self.aVal - 0) * (2 - .025)) / (255 - 0) + .025):
                        sleepTime = (((self.aVal - 0) * (2 - .025)) / (255 - 0) + .025)

                    # Check if we have left smooth
                    if self.mode != "smooth":
                        self.pi.set_PWM_dutycycle(self.pinR, 0)
                        self.pi.set_PWM_dutycycle(self.pinG, 0)
                        self.pi.set_PWM_dutycycle(self.pinB, 0)
                        return

                    # Check if we have disabled the LEDs
                    if not self.enabled:
                        break

                    # Increase green
                    self.pi.set_PWM_dutycycle(self.pinG, smoothVal)
                    time.sleep(sleepTime * .01)

                # Check if we have disabled the LEDs
                if not self.enabled:
                    continue
                    
                time.sleep(sleepTime)

                for smoothVal in range(255, -1, -1):
                    # Check if we have changed the alpha value
                    if sleepTime != (((self.aVal - 0) * (2 - .025)) / (255 - 0) + .025):
                        sleepTime = (((self.aVal - 0) * (2 - .025)) / (255 - 0) + .025)

                    # Check if we have left smooth
                    if self.mode != "smooth":
                        self.pi.set_PWM_dutycycle(self.pinR, 0)
                        self.pi.set_PWM_dutycycle(self.pinG, 0)
                        self.pi.set_PWM_dutycycle(self.pinB, 0)
                        return

                    # Check if we have disabled the LEDs
                    if not self.enabled:
                        break

                    # Decrease red
                    self.pi.set_PWM_dutycycle(self.pinR, smoothVal)
                    time.sleep(sleepTime * .01)

                # Check if we have disabled the LEDs
                if not self.enabled:
                    continue
                    
                time.sleep(sleepTime)

                for smoothVal in range(0, 255, 1):
                    # Check if we have changed the alpha value
                    if sleepTime != (((self.aVal - 0) * (2 - .025)) / (255 - 0) + .025):
                        sleepTime = (((self.aVal - 0) * (2 - .025)) / (255 - 0) + .025)

                    # Check if we have left smooth
                    if self.mode != "smooth":
                        self.pi.set_PWM_dutycycle(self.pinR, 0)
                        self.pi.set_PWM_dutycycle(self.pinG, 0)
                        self.pi.set_PWM_dutycycle(self.pinB, 0)
                        return

                    # Check if we have disabled the LEDs
                    if not self.enabled:
                        break

                    # Increase blue
                    self.pi.set_PWM_dutycycle(self.pinB, smoothVal)
                    time.sleep(sleepTime * .01)

                # Check if we have disabled the LEDs
                if not self.enabled:
                    continue
                    
                time.sleep(sleepTime)

                for smoothVal in range(255, -1, -1):
                    # Check if we have changed the alpha value
                    if sleepTime != (((self.aVal - 0) * (2 - .025)) / (255 - 0) + .025):
                        sleepTime = (((self.aVal - 0) * (2 - .025)) / (255 - 0) + .025)

                    # Check if we have left smooth
                    if self.mode != "smooth":
                        self.pi.set_PWM_dutycycle(self.pinR, 0)
                        self.pi.set_PWM_dutycycle(self.pinG, 0)
                        self.pi.set_PWM_dutycycle(self.pinB, 0)
                        return

                    # Check if we have disabled the LEDs
                    if not self.enabled:
                        break

                    # Decrease green
                    self.pi.set_PWM_dutycycle(self.pinG, smoothVal)
                    time.sleep(sleepTime * .01)

                # Check if we have disabled the LEDs
                if not self.enabled:
                    continue
                    
                time.sleep(sleepTime)

                for smoothVal in range(0, 255, 1):
                    # Check if we have changed the alpha value
                    if sleepTime != (((self.aVal - 0) * (2 - .025)) / (255 - 0) + .025):
                        sleepTime = (((self.aVal - 0) * (2 - .025)) / (255 - 0) + .025)

                    # Check if we have left smooth
                    if self.mode != "smooth":
                        self.pi.set_PWM_dutycycle(self.pinR, 0)
                        self.pi.set_PWM_dutycycle(self.pinG, 0)
                        self.pi.set_PWM_dutycycle(self.pinB, 0)
                        return

                    # Check if we have disabled the LEDs
                    if not self.enabled:
                        break

                    # Increase red
                    self.pi.set_PWM_dutycycle(self.pinR, smoothVal)
                    time.sleep(sleepTime * .01)

                # Check if we have disabled the LEDs
                if not self.enabled:
                    continue
                    
                time.sleep(sleepTime)

                for smoothVal in range(255, -1, -1):
                    # Check if we have changed the alpha value
                    if sleepTime != (((self.aVal - 0) * (2 - .025)) / (255 - 0) + .025):
                        sleepTime = (((self.aVal - 0) * (2 - .025)) / (255 - 0) + .025)

                    # Check if we have left smooth
                    if self.mode != "smooth":
                        self.pi.set_PWM_dutycycle(self.pinR, 0)
                        self.pi.set_PWM_dutycycle(self.pinG, 0)
                        self.pi.set_PWM_dutycycle(self.pinB, 0)
                        return

                    # Check if we have disabled the LEDs
                    if not self.enabled:
                        break

                    # Decrease blue
                    self.pi.set_PWM_dutycycle(self.pinB, smoothVal)
                    time.sleep(sleepTime * .01)

                # Check if we have disabled the LEDs
                if not self.enabled:
                    continue
                    
                time.sleep(sleepTime)
