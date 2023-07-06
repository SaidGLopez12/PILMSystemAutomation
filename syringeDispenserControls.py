import nidaqmx # library for national instruments controls| For DAC USB 6009
import time # for delay functions

#--Analog Output Channels--#
task = nidaqmx.Task() 
task.ao_channels.add_ao_voltage_chan('Dev1/ao0', 'Channel_0', min_val = 0.00, max_val = 5.00) # create a analog output channel for voltage at channel ao0 called channel_1
task.start() # Required | Turn on the channel


#--Analog Input Channels--#
task_read = nidaqmx.Task() # creating a function to read voltage from the Syringe Dispenser
task_read.ai_channels.add_ai_voltage_chan('Dev1/ao1') # create an analog input channel
task_read.start() # start the analog input channel

#------------------------#

value = input()
task.write(0) # Set the Channel's voltage to 2
time.sleep(2)
task.write(value) # Set the Channel's voltage to 5

value = task_read.read()
print(f"The current voltage for the voltage channel is: {value}")

task.stop() # Required | Stop the channel
task.close() # Required | Close the channel

task_read.stop()
task_read.close()

