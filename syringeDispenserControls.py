import nidaqmx # library for national instruments controls
import time # for delay functions
task = nidaqmx.Task() 

task.ao_channels.add_ao_voltage_chan('Dev1/ao0', 'Channel_0', min_val = 0.00, max_val = 5.00) # create a analog output channel for voltage at channel ao0 called channel_1
task.start() # Required | Turn on the channel
value = 2
task.write(value) # Set the Channel's voltage to 2
time.sleep(2)
task.write(value+3) # Set the Channel's voltage to 5

task_2 = nidaqmx.Task()
task_2.ao_channels.add_ao_voltage_chan('Dev1/ao1', 'Channel_1', min_val = 0.00, max_val = 5.00)
task_2.start() # required for channel 2
task_2.write(3)

task.stop() # Required | Stop the channel
task.close() # Required | Close the channel

task_2.stop()
task_2.close()

