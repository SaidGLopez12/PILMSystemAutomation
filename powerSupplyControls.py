#------Libraries------#
import asyncio # for AconityStudio integration
import pyvisa # frontend to the VISA library
import time # for delays and timer function
import keyboard # for keyboard press  
#import os # for datalogging
#---------------------#
# Getting ID of PSU and preparing for configuration
rm = pyvisa.ResourceManager() # create resource manager to store ID of  Devices
print("\nResources detected:\n{}\n".format(rm.list_resources())) # list the avaiable VISA resources for Compatible Devices

#-- Need psu to be plugged in and it's id for the script to work--#
powerSupply = rm.open_resource('USB0::0x1AB1::0x0E11::DP8C243004769::INSTR') # open the VISA resource for the power supply unit | This is where you will add the ID of the PSU
#print(powerSupply.query("*IDN?")) # will open the VISA resource tied to the psu and print the name of the psu. - Can be used for testing purposes -

#---------------------#
# function for one channel test | Does not need any parameters, it will do everything within the function when called
def oneChannelPsuTest():
    testDone = False # for while loop condition
    userInput = 0 # stores the value of the user
    
    # arrays to store parameters for testing | Limit is 30V and 3A
    voltage = [0,3,5] 
    amps = [0,1,2]

    while testDone != True: # loop to repeat test if desired. Will repeat until testDone is equal to true.
        
        print("\nBeginning Test Of PSU with 1 channel")
        print("---------------------------------------------\n")
        # Controlling the PSU through channel_1
        powerSupply.write(':OUTP CH1, ON') # tell the psu to turn ON channel_1.
        print("Testing parameter 1")
        powerSupply.write(f':APPL CH1, {str(voltage[0])},{str(amps[0])}') # need to change the int values to strings, so it's readable to the PSU. Tells the psu to change the voltage and current of channel_1.
        time.sleep(0.6) # Delay is needed for the PSU to output the current measurements. | Recommend 0.6 and above, anything lower than this will result in the readings being inaccurate.
        print("Voltage: " + powerSupply.query(':MEAS:VOLT? CH1'))  # returns current voltage for channel 1
        print("Current: " + powerSupply.query(':MEAS:CURR? CH1')) # returns the current for channel 1
        time.sleep(0.6)

        print("Testing parameter 2")
        powerSupply.write(f':APPL CH1, {str(voltage[1])},{str(amps[1])}')
        time.sleep(0.6)
        print("Voltage: " + powerSupply.query(':MEAS:VOLT? CH1'))
        print("Current: " + powerSupply.query(':MEAS:CURR? CH1'))
        time.sleep(0.6)

        print("Testing parameter 3")
        powerSupply.write(f':APPL CH1, {str(voltage[2])},{str(amps[2])}')
        time.sleep(0.6)
        print("Voltage: " + powerSupply.query(':MEAS:VOLT? CH1'))
        print("Current: " + powerSupply.query(':MEAS:CURR? CH1'))
        time.sleep(0.6)
        print("PSU Test Done. Want to test it again? Y = yes | N == No")
        userInput = input("Input: ") # Will Ask for the User Input. 
        print("---------------------------------------------\n")

        # Continue the Testing or terminate it
        if userInput == 'N' or userInput == 'n':
            print("Turning off Channel 1\n")
            testDone = True
        elif userInput == 'Y' or userInput == 'y':
             print("Restarting Test") # it'll just exit out of the conditional statement and into the while loop again.
        else:
            print("Incorrect input. Turning off Channel 1\n") # Any other input will result in the channel being turned off

       
    powerSupply.write(':OUTP CH1, OFF') # turn off channel_1     
            
        
        
#---------------------#
# function for multiple channel test | Does not need any parameters, it will do everything within the function when called
def multipleChannelsPsuTest():
    testDone = False # for while loop condition
    userInput = 0  # stores the value of the user
    
    # arrays to store parameters for testing. | Also for each channel
    # Remember that Channel 1 and 2 have a different range of max values compared to Channel 3. | Channel 3 is limited to: 5V, 2A
    voltage_1,voltage_2,voltage_3 = [0,3,5], [0,3,5],  [0,3,5]
    amps_1,amps_2,amps_3 = [0,1,2], [0,1,2], [0,1,2]
    
    while testDone != True:
        print("\nBeginning Test of PSU with 3 Channels\n")
        print("---------------------------------------------\n")
        #--- Channel_1---#
        print("Channel 1: Testing parameter 1")
        powerSupply.write(':OUTP CH1, ON')
        powerSupply.write(f':APPL CH1, {str(voltage_1[0])},{str(amps_1[0])}')
        time.sleep(1.1) # Timer to give enough time for PSU to ouput the correct readings. | Anything less than this will cause inaccuracies, especially with multiple channels.
        print("Voltage: " + powerSupply.query(':MEAS:VOLT? CH1'))
        print("Current: " + powerSupply.query(':MEAS:CURR? CH1'))
        time.sleep(1.1)
        print("Channel 1: Testing parameter 2.")
        powerSupply.write(f':APPL CH1, {str(voltage_1[1])},{str(amps_1[1])}')
        time.sleep(1.1) 
        print("Voltage: " +  powerSupply.query(':MEAS:VOLT? CH1'))
        print("Current: " +  powerSupply.query(':MEAS:CURR? CH1'))
        time.sleep(1.1)
        print("Channel 1: Testing parameter 3.")
        powerSupply.write(f':APPL CH1, {str(voltage_1[2])},{str(amps_1[2])}')
        time.sleep(1.1)
        print("Voltage: " + powerSupply.query(':MEAS:VOLT? CH1'))
        print("Current: " + powerSupply.query(':MEAS:CURR? CH1'))
        time.sleep(1.2)
        print("Channel 1 Test Done. Moving to Channel 2.")
        print("---------------------------------------------\n")
        #--- Channel_2---#
        print("Testing Channel 2")
        print("---------------------------------------------")
        powerSupply.write(':OUTP CH2, ON') # tell the psu to turn ON channel_2.
        print("Channel 2: Testing parameter 1")
        powerSupply.write(f':APPL CH2, {str(voltage_2[0])},{str(amps_2[0])}')
        time.sleep(1.1) 
        print("Voltage: " + powerSupply.query(':MEAS:VOLT? CH2'))
        print("Current: " + powerSupply.query(':MEAS:CURR? CH2'))
        time.sleep(1.1)
        print("Channel 2: Testing parameter 2")
        powerSupply.write(f':APPL CH2, {str(voltage_2[1])},{str(amps_2[1])}')
        time.sleep(1.1)
        print("Voltage: " + powerSupply.query(':MEAS:VOLT? CH2'))
        print("Current: " + powerSupply.query(':MEAS:CURR? CH2'))
        time.sleep(1.1)
        print("Channel 2: Testing parameter 3")
        powerSupply.write(f':APPL CH2, {str(voltage_2[2])},{str(amps_2[2])}')
        time.sleep(1.1)
        print("Voltage: " + powerSupply.query(':MEAS:VOLT? CH2'))
        print("Current: " + powerSupply.query(':MEAS:CURR? CH2'))
        time.sleep(1.1)
        print("Channel 2 Test Done. Moving to Channel 3.")
        print("---------------------------------------------\n")

        #--- Channel_3---#
        print("Testing Channel 3")
        print("---------------------------------------------")
        powerSupply.write(':OUTP CH3, ON') # tell the psu to turn ON channel_3.
        print("Channel 3: Testing parameter 1")
        powerSupply.write(f':APPL CH3, {str(voltage_3[0])},{str(amps_3[0])}')
        time.sleep(1.1) 
        print("Voltage: " + powerSupply.query(':MEAS:VOLT? CH3'))
        print("Current: " + powerSupply.query(':MEAS:CURR? CH3') )
        time.sleep(1.1)
        print("Channel 3: Testing parameter 2")
        powerSupply.write(f':APPL CH3, {str(voltage_3[1])},{str(amps_3[1])}')
        time.sleep(1.1)
        print("Voltage: " + powerSupply.query(':MEAS:VOLT? CH3'))
        print("Current: " + powerSupply.query(':MEAS:CURR? CH3'))
        time.sleep(1.1)
        print("Channel 3: Testing parameter 3")
        powerSupply.write(f':APPL CH3, {str(voltage_3[2])},{str(amps_3[2])}')
        time.sleep(1.1)
        print("Voltage: " + powerSupply.query(':MEAS:VOLT? CH3'))
        print("Current: " + powerSupply.query(':MEAS:CURR? CH3'))
        time.sleep(1.1)
        print("Channel 3 Test Done.")
        print("---------------------------------------------\n")
        print("PSU Test Done. Want to test it again? Y = yes | N == No")
        userInput = input("Input: ")
        # Continue the Testing or terminate it
        if userInput == 'N' or userInput == 'n':
            print("Turning off Channels\n")
            testDone = True
        elif userInput == 'Y' or userInput == 'y':
             print("Restarting Test")
        else:
            print("Incorrect Value. Turning off all channels")
    
        print("---------------------------------------------\n")

    powerSupply.write(':OUTP CH1, OFF') # tell the psu to turn OFF channel_1.
    powerSupply.write(':OUTP CH2, OFF') # tell the psu to turn OFF channel_2.
    powerSupply.write(':OUTP CH3, OFF') # tell the psu to turn OFF channel_3.
    
#----------------------------#   
  # Timer function
def timerFunction(timeInSec):
    while timeInSec: # while timer is not 0. (1 = true, 0 = false) (True as long as it contains a val)
        mins, secs = divmod(timeInSec, 60) # modulo of timeInSec and 60. Returns the quotient and the remainder.
        timer = '{:02d}:{:02d}'.format(mins, secs) # format the variable as 00.00
        print("Time left:",timer, end="\r") # print the current timer value, create an end variable that creates a new line.
        time.sleep(1) 
        timeInSec -= 1 # reduce the total input time by 1 each repetition.

def stopWatchFunction():
    timeInSec = 0
    space_pressed = False 

    print("\nTimer is on. Hold space to stop PSU Channels")
    keyboard.press_and_release('space') 
    while space_pressed != True:   
        
        mins, secs = divmod(timeInSec, 60)
        timer = '{:02d}:{:02d}'.format(mins, secs) # format the variable as 00.00
        print("Time Active:",timer, end="\r") # print the current timer value, create an end variable that creates a new line.
        time.sleep(1) 
        timeInSec += 1
        
        if keyboard.is_pressed('space'):
            space_pressed = True   
                
    print(f"\nTotal Time: {timeInSec}s")     
             
#----------------------------#

#------AconityStudio Integration----------------------#
# Main function with one channel. | Voltage and Amps are float values. timeInSec is int
async def heatPadOneChannel(voltage,amps,timeInSec):  
    #-Getting ID of PSU and preparing for PILM Process-#
    rm = pyvisa.ResourceManager() # create resource manager to find id for PSU
    powerSupply = rm.open_resource('USB0::0x1AB1::0x0E11::DP8C243004769::INSTR') # open the VISA resource for the power supply unit
    powerSupply.write(':OUTP CH1, ON')  
    print("Channel 1 is Active\n")
    #--------------------------------------------------#
    powerSupply.write(f':APPL CH1, {str(voltage)},{str(amps)}') # applies chosen voltage and amps to CH1
    print("Voltage: " + str(voltage) + "V")
    print("Current: " + str(amps) + "A") 
    
    timerFunction(timeInSec) # call the timer function and start the timer at the selected seconds. | Will move on to the next code statement after it's finished.
    powerSupply.write(':OUTP CH1, OFF') # turn off the channel after the timer reaches 0.

# Main function with multiple channels. 
async def heatPadMutipleChannels(voltage,amps,timeInSec,numOfChannels): # numOfChannels is a int val. 
    rm = pyvisa.ResourceManager()
    powerSupply = rm.open_resource('USB0::0x1AB1::0x0E11::DP8C243004769::INSTR')
    
    
    if numOfChannels == 1:
        powerSupply.write(':OUTP CH1, ON') 
        print("Channel 1 is Active")
        powerSupply.write(f':APPL CH1, {str(voltage)},{str(amps)}') 
        print("Voltage: " + str(voltage) + "V")
        print("Current: " + str(amps) + "A") 
        
        timerFunction(timeInSec)
        powerSupply.write(':OUTP CH1, OFF')
    elif numOfChannels == 2:
        powerSupply.write(':OUTP CH1, ON')
        powerSupply.write(':OUTP CH2, ON')
        
        print("Channel 1 and Channel 2 are Active")
        powerSupply.write(f':APPL CH1, {str(voltage)},{str(amps)}')
        powerSupply.write(f':APPL CH2, {str(voltage)},{str(amps)}')
        print("Voltage: " + str(voltage) + "V")
        print("Current: " + str(amps) + "A") 
        
        timerFunction(timeInSec)
        powerSupply.write(':OUTP CH1, OFF')
        powerSupply.write(':OUTP CH2, OFF')     
    elif numOfChannels == 3:
        powerSupply.write(':OUTP CH1, ON')
        powerSupply.write(':OUTP CH2, ON')
        powerSupply.write(':OUTP CH3, ON')
        
        print("Channel 1, Channel 2, and Channel 3 are Active")
        powerSupply.write(f':APPL CH1, {str(voltage)},{str(amps)}')
        powerSupply.write(f':APPL CH2, {str(voltage)},{str(amps)}')
        powerSupply.write(f':APPL CH3, {str(voltage)},{str(amps)}')
        print("Voltage: " + str(voltage) + "V")
        print("Current: " + str(amps) + "A") 
        
        timerFunction(timeInSec)
        powerSupply.write(':OUTP CH1, OFF')
        powerSupply.write(':OUTP CH2, OFF')
        powerSupply.write(':OUTP CH3, OFF')     
    else:
        print("Wrong Input,Try Again. 1|2|3") # won't really be needed. Just in case.
    
#---------------------------------#
# Test Functions Here # 

# os.system('cls' if os.name == 'nt' else 'clear') # clears everything within the console.

def MutipleChannels_StopWatch(voltage,amps,numOfChannels): # numOfChannels is a int val. 
    rm = pyvisa.ResourceManager()
    powerSupply = rm.open_resource('USB0::0x1AB1::0x0E11::DP8C243004769::INSTR')
    
    
    if numOfChannels == 1:
        powerSupply.write(':OUTP CH1, ON') 
        print("Channel 1 is Active")
        powerSupply.write(f':APPL CH1, {str(voltage)},{str(amps)}') 
        print("Voltage: " + str(voltage) + "V")
        print("Current: " + str(amps) + "A") 

        stopWatchFunction()
        powerSupply.write(':OUTP CH1, OFF')

    elif numOfChannels == 2:
        powerSupply.write(':OUTP CH1, ON')
        powerSupply.write(':OUTP CH2, ON')
        
        print("Channel 1 and Channel 2 are Active")
        powerSupply.write(f':APPL CH1, {str(voltage)},{str(amps)}')
        powerSupply.write(f':APPL CH2, {str(voltage)},{str(amps)}')
        print("Voltage: " + str(voltage) + "V")
        print("Current: " + str(amps) + "A") 
        
        stopWatchFunction()
        powerSupply.write(':OUTP CH1, OFF')
        powerSupply.write(':OUTP CH2, OFF')     
    elif numOfChannels == 3:
        powerSupply.write(':OUTP CH1, ON')
        powerSupply.write(':OUTP CH2, ON')
        powerSupply.write(':OUTP CH3, ON')
        
        print("Channel 1, Channel 2, and Channel 3 are Active")
        powerSupply.write(f':APPL CH1, {str(voltage)},{str(amps)}')
        powerSupply.write(f':APPL CH2, {str(voltage)},{str(amps)}')
        powerSupply.write(f':APPL CH3, {str(voltage)},{str(amps)}')
        print("Voltage: " + str(voltage) + "V")
        print("Current: " + str(amps) + "A") 
        
        stopWatchFunction()
        powerSupply.write(':OUTP CH1, OFF')
        powerSupply.write(':OUTP CH2, OFF')
        powerSupply.write(':OUTP CH3, OFF')     
    else:
        print("Wrong Input,Try Again. 1|2|3")

MutipleChannels_StopWatch(10,2,2)