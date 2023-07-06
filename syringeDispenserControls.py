import nidaqmx # library for national instruments controls| For DAC USB 6009
import time # for delay functions
'''
#--Analog Input Channels--#
task_read = nidaqmx.Task() # creating a function to read voltage from the Syringe Dispenser
task_read.ai_channels.add_ai_voltage_chan('Dev1/ai0', 'inputChan_0', min_val= 0.00, max_val = 5.00) # create an analog input channel
task_read.start() # start the analog input channel
'''

#----Operations----#

def dispenseOperation():
    #--Analog Output Channels--#
    task = nidaqmx.Task() 
    task.ao_channels.add_ao_voltage_chan('Dev1/ao0', 'outputChan_0', min_val = 0.00, max_val = 5.00) # create a analog output channel for voltage at channel ao0 called channel_1
    task.start() # Required | Turn on the channel
    
    print("Starting Dispense Cycle\n")
    task.write(0)
    time.sleep(1)
    task.write(5) # set the voltage channel to 5v | Will trigger the cycle
    

    task.stop() # Required | Stop the analog output channel
    task.close() # Required | Close the channel

    #Note: You have to wait for the cycle to finish to call it again.
    # You also can't just set it to 0V after it's changed to 5v 
    #It's best to configure the cycle settings if you want a faster cycle
#-----------------#

dispenseOperation()
time.sleep(30)
dispenseOperation()
