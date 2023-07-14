#------Libraries------#
import pyvisa # frontend to the VISA library
import time # for delays and timer function
import os # for datalogging
#---------------------#
# Getting ID of PSU and preparing for configuration
rm = pyvisa.ResourceManager() # create resource manager to store in USB ID
print("\nResources detected:\n{}\n".format(rm.list_resources())) # list the avaiable VISA resources

#-- Need psu to be plugged in and it's id --#
powerSupply = rm.open_resource('USB0::0x1AB1::0x0E11::DP8C243004769::INSTR') # open the VISA resource for the power supply unit | This is where you will add the id of the PSU
#print(powerSupply.query("*IDN?")) # will open the VISA resource tied to the psu and print the name of the psu.

#---------------------#
# function for one channel test | Does not need any parameters, it will do everything within the function
def oneChannelPsuTest():
    testDone = False # for loop
    userInput = 0
    
    # arrays to store parameters for testing
    voltage = [0,3,5]
    amps = [0,1,2]

    while testDone != True: # loop to repeat test if desired. Will repeat until testDone is equal to true.
        
        print("\nBeginning Test Of PSU with 1 channel")
        print("---------------------------------------------\n")
        # Controlling the PSU through channel_1
        powerSupply.write(':OUTP CH1, ON') # tell the psu to turn ON channel_1.
        print("Testing parameter 1")
        powerSupply.write(f':APPL CH1, {str(voltage[0])},{str(amps[0])}') # need to change the int to strings, so it's readable to the PSU. Use f strings to include variables/array values. Tells the psu to change the voltage and current of channel_1.
        time.sleep(0.6) # Delay is needed for the PSU to output the current measurements.
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
        userInput = input("Input: ")
        print("---------------------------------------------\n")

        # Continue the Testing or terminate it
        if userInput == 'N' or userInput == 'n':
            print("Turning off Channel 1\n")
            testDone = True
        elif userInput == 'Y' or userInput == 'y':
             print("Restarting Test") # it'll just exit out of the conditional statement and into the while loop again.

       
    powerSupply.write(':OUTP CH1, OFF') # turn off channel_1     
            
        
        
#---------------------#
# function for multiple channel test | Does not need any parameters, it will do everything within the function  
def multipleChannelsPsuTest():
    testDone = False # for loop
    userInput = 0
    
    # arrays to store parameters for testing. | Also for each channel
    # Remember that Channel 1 and 2 have a different range of max values compared to Channel 3.
    voltage_1,voltage_2,voltage_3 = [0,3,5], [0,3,5],  [0,3,5]
    amps_1,amps_2,amps_3 = [0,1,2], [0,1,2], [0,1,2]
    
    while testDone != True:
        print("\nBeginning Test of PSU with 3 Channels\n")
        print("---------------------------------------------\n")
        #--- Channel_1---#
        print("Channel 1: Testing parameter 1")
        powerSupply.write(':OUTP CH1, ON')
        powerSupply.write(f':APPL CH1, {str(voltage_1[0])},{str(amps_1[0])}')
        time.sleep(1.1) 
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
    
        print("---------------------------------------------\n")

    powerSupply.write(':OUTP CH1, OFF') # tell the psu to turn OFF channel_1.
    powerSupply.write(':OUTP CH2, OFF') # tell the psu to turn OFF channel_2.
    powerSupply.write(':OUTP CH3, OFF') # tell the psu to turn OFF channel_3.
    
#----------------------------#   
  # Timer function
def timerFunction(timeInSec):
    while timeInSec: # while timer is not 0. (1 = true, 0 = false)
        mins, secs = divmod(timeInSec, 60) # modulo of timeInSec and 60. Returns the quotient and the remainder.
        timer = '{:02d}:{:02d}'.format(mins, secs) # format the variable as 00.00
        print("Time left:",timer, end="\r") # print the current timer value, create a end variable that creates a new line.
        time.sleep(1)
        timeInSec -= 1 # reduce the total input time by 1 each repetition.
#----------------------------#
# Main function with one channel.
def heatPadOneChannel(voltage,amps,timeInSec):  
    #-Getting ID of PSU and preparing for PILM Process-#
    rm = pyvisa.ResourceManager() # create resource manager to find id for PSU
    powerSupply = rm.open_resource('USB0::0x1AB1::0x0E11::DP8C243004769::INSTR') # open the VISA resource for the power supply unit
    powerSupply.write(':OUTP CH1, ON')
    print("Channel 1 is Active")
    #--------------------------------------------------#
    powerSupply.write(f':APPL CH1, {str(voltage)},{str(amps)}')
    print("Voltage: " + str(voltage) + "V")
    print("Current: " + str(amps) + "A") 
    
    timerFunction(timeInSec) # call the timer function and start the timer at the selected seconds.
    powerSupply.write(':OUTP CH1, OFF') # turn off the channel after it reaches 0.

# Main function with multiple channels. 
def heatPadMutipleChannels(voltage,amps,timeInSec,numOfChannels):
    rm = pyvisa.ResourceManager()
    powerSupply = rm.open_resource('USB0::0x1AB1::0x0E11::DP8C243004769::INSTR')
    
    
    if numOfChannels == 1:
        powerSupply.write(':OUTP CH1, ON')
        print("Channel 1 is Active")
        powerSupply.write(f':APPL CH1, {str(voltage)},{str(amps)}') # channel_1 is set by the parameters
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


# os.system('cls' if os.name == 'nt' else 'clear') # clears everything within the console.
# time.sleep(5)
