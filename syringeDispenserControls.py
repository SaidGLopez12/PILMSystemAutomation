import nidaqmx # library for national instruments controls| For DAC USB 6009
import time # for delay functions

#--Analog Output Channels--#
task = nidaqmx.Task() 
task.ao_channels.add_ao_voltage_chan('Dev1/ao0', 'outputChan_0', min_val = 0.00, max_val = 5.00) # create a analog output channel for voltage at channel ao0 called channel_1
task.start() # Required | Turn on the channel


#--Analog Input Channels--#
task_read = nidaqmx.Task() # creating a function to read voltage from the Syringe Dispenser
task_read.ai_channels.add_ai_voltage_chan('Dev1/ai0', 'inputChan_0', min_val= 0.00, max_val = 5.00) # create an analog input channel
task_read.start() # start the analog input channel

#------------------------#
#----Operations----#

value = input("Value: ")
task.write(0) # Set the Channel's voltage to 2
time.sleep(2)
task.write(value) # Set the Channel's voltage to 5

value = task_read.read()
print(f"The current voltage for the voltage channel is: {value}")
#-----------------#

task.stop() # Required | Stop the analog output channel
task.close() # Required | Close the channel

task_read.stop() # Required | Stop the analog input channel
task_read.close()# Required | Close the channel



# possible process
# send voltage to start the cycle
# wait until the cycle is over for the dispenser to send voltage to the end-of-cycle pins
# detect voltage input and state that the process is done
# set the voltage for the output channel to 0V.
#repeat this process when called.

# Questions
# can I loop the process?
# or can the number of repetitions be configured with the syringe dispenser functions?
