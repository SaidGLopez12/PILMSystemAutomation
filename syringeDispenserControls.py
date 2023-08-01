import asyncio
import nidaqmx # library for national instruments controls| For DAC USB 6009
import time # for delay functions
'''
#--Analog Input Channels--# (Optional, not needed for overall program)
task_read = nidaqmx.Task() # creating a function to read voltage from the Syringe Dispenser
task_read.ai_channels.add_ai_voltage_chan('Dev1/ai0', 'inputChan_0', min_val= 0.00, max_val = 5.00) # create an analog input channel
task_read.start() # start the analog input channel
'''

#----Operations----#
# Function to Test within The Program # 
def dispenseOperation(): # This function will serve as the signal to start the dispensing cycle
    #--Analog Output Channels--#
    task = nidaqmx.Task() # Create a nidaqmx object that calls the Task() function. This will be used to control the DAQ
    task.ao_channels.add_ao_voltage_chan('Dev1/ao0', 'outputChan_0', min_val = 0.00, max_val = 5.00) # create a analog output channel for voltage at channel ao0 called channel_1
    task.start() # Required | Turn on the channel
    
    print("Starting Dispense Cycle\n")
    task.write(0) # Set the voltage channel to 0V
    time.sleep(1)
    task.write(5) # set the voltage channel to 5V | Will trigger the cycle
    time.sleep(10.5)
    task.write(0)

    task.stop() # Required | Stop the analog output channel once it's not needed
    task.close() # Required | Close the channel when done.

    #Note: You have to wait for the cycle to finish to call it again.
    # You also can't just set it to 0V after it's changed to 5v 
    #It's best to configure the cycle settings manually if you want a faster cycle
#-----------------#

# Function For PILM Automation # - tied with the dispenseFunction in executeScript.py
async def PILMDispenseOperation(): # This function will serve as the signal to start the dispensing cycle
    #--Analog Output Channels--#
    task = nidaqmx.Task() # Create a nidaqmx object that calls the Task() function. This will be used to control the DAQ
    task.ao_channels.add_ao_voltage_chan('Dev1/ao0', 'outputChan_0', min_val = 0.00, max_val = 5.00) # create a analog output channel for voltage at channel ao0 called channel_1
    task.start() # Required | Turn on the channel
    
    print("Starting Dispense Cycle\n")
    task.write(0) # Set the voltage channel to 0V
    time.sleep(1)
    task.write(5) # set the voltage channel to 5V | Will trigger the cycle
    time.sleep(1.5) # Doesn't seen to work the way we want. Could it be a cycle issue?
    task.write(0)

    task.stop() # Required | Stop the analog output channel once it's not needed
    task.close() # Required | Close the channel when done.

    #Note: You have to wait for the cycle to finish to call it again.
    # You also can't just set it to 0V after it's changed to 5v 
    #It's best to configure the cycle settings manually if you want a faster cycle
#-----------------#