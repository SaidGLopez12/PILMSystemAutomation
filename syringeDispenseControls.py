import asyncio # for AconityStudio integration
import nidaqmx # library for national instruments controls| For DAC USB 6009
import time # for delay functions
'''
#--Analog Input Channels--# (Optional, not needed for overall program)
task_read = nidaqmx.Task() # creating a function to read voltage from the Syringe Dispenser
task_read.ai_channels.add_ai_voltage_chan('Dev1/ai0', 'inputChan_0', min_val= 0.00, max_val = 5.00) # create an analog input channel
task_read.start() # start the analog input channel
'''

# Timer for slot-die dispensing process
def timerFunction(timeInSec):
    while timeInSec: # while timer is not 0. (1 = true, 0 = false) (True as long as it contains a val)
        mins, secs = divmod(timeInSec, 60) # modulo of timeInSec and 60. Returns the quotient and the remainder.
        timer = '{:02d}:{:02d}'.format(mins, secs) # format the variable as 00.00
        print("Time left:",timer, end="\r") # print the current timer value, create an end variable that creates a new line.
        time.sleep(1) 
        timeInSec -= 1 # reduce the total input time by 1 each repetition.


#----Operations----#
# Function to Test the Syringe Dispenser only # 
def dispenseOperation(): # This function will serve as the signal to start the dispensing cycle 
    #--Analog Output Channels--#
    task = nidaqmx.Task() # Create a nidaqmx object that calls the Task() function. This will be used to control the DAQ
    task.ao_channels.add_ao_voltage_chan('Dev1/ao0', 'outputChan_0', min_val = 0.00, max_val = 5.00) # create a analog output channel for voltage at channel ao0 called channel_1
    task.start() # Required | Turn on the channel
    
    print("Starting Dispense Cycle\n")  
    task.write(0) # Set the voltage channel to 0V
    time.sleep(1) # wait one second
    task.write(5) # set the voltage channel to 5V | Will trigger the cycle
    time.sleep(1.5) # wait this time after the cycle is finished
    task.write(0)

    task.stop() # Required | Stop the analog output channel once it's not needed
    task.close() # Required | Close the channel when done.

    #Note: You have to wait for the cycle to finish to call it again.
    # You also can't just set it to 0V after it's changed to 5v 
    #It's best to configure the cycle settings manually if you want a faster cycle


# Function For PILM Automation # - tied with the dispenseFunction in executeScript.py
async def PILMDispenseOperation(): # This function will serve as the signal to start the dispensing cycle
    #--Analog Output Channels--#
    task = nidaqmx.Task()
    task.ao_channels.add_ao_voltage_chan('Dev1/ao0', 'outputChan_0', min_val = 0.00, max_val = 5.00) 
    task.start() 
    
    print("Starting Dispense Cycle\n")
    task.write(0) 
    time.sleep(1)
    task.write(5)
    timerFunction(3)
    task.write(0)

    task.stop() # Required | Stop the analog output channel once it's not needed
    task.close() # Required | Close the channel when done.

    #Note: You have to wait for the cycle to finish to call it again.
    # You also can't just set it to 0V after it's changed to 5v 
    #It's best to configure the cycle settings manually if you want a faster cycle
#--------------------------------#