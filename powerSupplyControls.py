#------Libraries------#
import pyvisa # frontend to the VISA library
import time # for delays
import os # for datalogging
#---------------------#
# Getting ID of PSU and preparing for configuration
rm = pyvisa.ResourceManager() # create resource manager to store in USB ID
print("\nResources detected:\n{}\n".format(rm.list_resources())) # list the avaiable VISA resources

#-- Need psu to be plugged in and it's id --#

powerSupply = rm.open_resource() # open the VISA resource for the power supply unit | This is where you will add the id of the PSU

#---------------------#
# function for test | Does not need any parameters, it will do everything within the function
def oneChannelPsuTest():

    # arrays to store parameters for testing
    voltage = [0,3,5]
    amps = [0,1,2]

    print(powerSupply.query("*IDN?")) # will open the VISA resource tied to the psu and print the name of the psu
    print("Beginning Test Of PSU with 1 channel \n")
    # Controlling the PSU through channel_1
    powerSupply.write(':OUTP CH1, ON') # tell the psu to turn ON channel_1.
    print("Testing Channel 1.")

    powerSupply.write(':APPL CH1,' + str(voltage[0]) + str(amps[0])) # need to change the int to strings, so it's readable to the PSU
    print("Current Voltage: " + 'MEAS? CH1' + "V")
    time.sleep(2)

    print("Testing parameter 2.")
    powerSupply.write(':APPL CH1,' + str(voltage[1]) + str(amps[1]))
    print("Current Voltage: " + 'MEAS? CH1' + "V")
    time.sleep(2)

    print("Testing parameter 3.")
    powerSupply.write(':APPL CH1,' + str(voltage[2]) + str(amps[2]))
    print("Current Voltage: " + 'MEAS? CH1' + "V")
    time.sleep(2)
    print("PSU Test Done")
    powerSupply.write(':OUTP CH1, OFF') # tell the psu to turn OFF channel_1.
    
    
def multipleChannelsPsuTest():
    # arrays to store parameters for testing. | Also for each channel
    # Remember that Channel 1 and 2 have a different range of max values compared to Channel 3
    voltage_1,voltage_2,voltage_3 = [0,3,5], [0,3,5],  [0,3,5]
    amps_1,amps_2,amps_3 = [0,1,2], [0,1,2], [0,1,2]
    
    print("Beginning Test of PSU with 3 Channels\n")
    #--- Channel_1---#
    print("Channel 1: Testing parameter 1")
    powerSupply.write(':OUTP CH1, ON') # tell the psu to turn ON channel_1.
    powerSupply.write(':APPL CH1,' + str(voltage_1[0]) + str(amps_1[0])) # need to change the int to strings, so it's readable to the PSU
    print("Current Voltage: " + 'MEAS? CH1' + "V") # returns current voltage for channel 1
    time.sleep(2)
    print("Channel 1: Testing parameter 2.")
    powerSupply.write(':APPL CH1,' + str(voltage_1[1]) + str(amps_1[1]))
    print("Current Voltage: " + 'MEAS? CH1' + "V")
    time.sleep(2)
    print("Channel 1: Testing parameter 3.")
    powerSupply.write(':APPL CH1,' + str(voltage_1[2]) + str(amps_1[2]))
    print("Current Voltage: " + 'MEAS? CH1' + "V")
    time.sleep(2)
    print("Channel 1 Test Done. Moving to Channel 2. \n")
    
    #--- Channel_2---#
    print("Testing Channel 2")
    powerSupply.write(':OUTP CH2, ON') # tell the psu to turn ON channel_2.
    print("Channel 2: Testing parameter 1")
    powerSupply.write(':APPL CH2,' + str(voltage_2[0]) + str(amps_2[0])) # need to change the int to strings, so it's readable to the PSU
    print("Current Voltage: " + 'MEAS? CH2' + "V")
    time.sleep(2)
    print("Channel 2: Testing parameter 2")
    powerSupply.write(':APPL CH2,' + str(voltage_2[1]) + str(amps_2[1]))
    print("Current Voltage: " + 'MEAS? CH2' + "V")
    time.sleep(2)
    print("Channel 2: Testing parameter 3")
    powerSupply.write(':APPL CH2,' + str(voltage_2[2]) + str(amps_2[2]))
    print("Current Voltage: " + 'MEAS? CH2' + "V")
    time.sleep(2)
    print("Channel 2 Test Done. Moving to Channel 3. \n")

    #--- Channel_3---#
    print("Testing Channel 3")
    powerSupply.write(':OUTP CH3, ON') # tell the psu to turn ON channel_3.
    print("Channel 3: Testing parameter 1")
    powerSupply.write(':APPL CH3,' + str(voltage_3[0]) + str(amps_3[0])) # need to change the int to strings, so it's readable to the PSU
    print("Current Voltage: " + 'MEAS? CH3' + "V")
    time.sleep(2)
    print("Channel 3: Testing parameter 2")
    powerSupply.write(':APPL CH3,' + str(voltage_3[1]) + str(amps_3[1]))
    print("Current Voltage: " + 'MEAS? CH3' + "V")
    time.sleep(2)
    print("Channel 3: Testing parameter 3")
    powerSupply.write(':APPL CH3,' + str(voltage_3[2]) + str(amps_3[2]))
    print("Current Voltage: " + 'MEAS? CH3' + "V")
    time.sleep(2)
    print("Channel 3 Test Done.\n")


    print("PSU Test Done. Turning off all channels.")
    powerSupply.write(':OUTP CH1, OFF') # tell the psu to turn OFF channel_1.
    powerSupply.write(':OUTP CH2, OFF') # tell the psu to turn OFF channel_2.
    powerSupply.write(':OUTP CH3, OFF') # tell the psu to turn OFF channel_3.
        
    
    
# Do the main function with one channel. With extra time, attempt the multi channel version.
