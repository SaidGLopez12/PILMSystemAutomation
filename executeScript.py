#--importing libraries and files--# * Explain
import asyncio # Required for Server and Client communication
import os
import signal 
signal.signal(signal.SIGINT, signal.SIG_DFL)

from aconityAPIfiles.AconitySTUDIO_client import AconitySTUDIOPythonClient # Required | Imports libraries and the AconitySTUDIOPythonClient class from this file
#from aconityAPIfiles.AconitySTUDIO_client import utils # Required | Imports libraries and the utils. This file does not have a utils class, so is it required?
from aconityAPIfiles import AconitySTUDIO_utils

from powerSupplyControls import timerFunction, heatPadOneChannel, heatPadMutipleChannels
from syringeDispenserControls import dispenseOperation
#--------------------------------------#

# -- Inital Variables and Instantiations -- #
# --- Slider Movement Variables --- #

# default aconity positions for slider 
positiveEndPos = "395" # the numbers are readable as strings
centerSlidePos = "260"
platformInFrontPos = "210"
platformRearPos = "30"

# -- Platform Movement Variables -- #
dispenseHeight = "17"
defaultHeight = "18"

#---------------------------------------#

# --- AconityScript Commands --- #
# They are stored in variables that can be used in the execute commands that are readable by the machine.
# Slider
returnPos = f'$m.move_abs($c[slider], {positiveEndPos}, 250)' # 300 is max vel. Go less since a lot of error messages pop up when reaching this velocity
initalPos = '$m.move_abs($c[slider], 75,250)'
finalPos = '$m.move_abs($c[slider], 180,10)'
centerPos = f'$m.move_abs($c[slider],{centerSlidePos},250)' # this will be used to move slider away from the laser during the sintering process

# Platform
slotDiePlatFormHeight = f'$m.move_abs($c[platform],{dispenseHeight},200)'
defaultPlatformHeight = f'$m.move_abs($c[platform],{defaultHeight}, 200)'

#---------------------------------#
    
async def executeFun(login_data, info): # main function that will be used  to control the aconity machine for PILM, macroscale SLS process and more.
    
    # create client with factory method
    client = await AconitySTUDIOPythonClient.create(login_data)
    client.studio_version = info['studio_version']
    
    # IMPORTANT:
    # the following CONVENIENCE FUNCTIONS (get_job_id etc) only work if the job_name, machine_name or config_name are unique.
    # If this is not the case, set the attributes job_name, config_name, machine_name manually
    await client.get_job_id(info['job_name'])
    await client.get_machine_id(info['machine_name'])
    await client.get_config_id(info['config_name'])


    os.system('cls' if os.name == 'nt' else 'clear') # clears everything above this code statement. To reduce clutter and confusion when running the script.
    await testPILMScript(client) # you need to await defined functions as well.

async def jobProcess(client):
        # Start a job. 
        execution_script = AconitySTUDIO_utils.EXECUTION_SCRIPTS['only_expose']
        build_parts = 'all'
        start_layer = 7
        end_layer = 7

        await client.start_job(execution_script = execution_script,
                                layers = [start_layer, end_layer],
                                parts = build_parts)
        

# AM Processes

# PILM
async def PILMFun(client):
      print("Starting PILM Process")
      await client.execute(channel = 'manual_move', script = defaultPlatformHeight) # incase the platform is not in this position from the start
      await asyncio.sleep(1)
      await client.execute(channel = 'manual_move', script = returnPos) # incase the slider is not in this position from the start
      await asyncio.sleep(2)
      await client.execute(channel = 'manual_move', script = initalPos)
      await asyncio.sleep(3)
      
      
      #Slot Die Process
      await client.execute(channel = 'manual_move', script = slotDiePlatFormHeight)
      await client.execute(channel = 'manual_move', script = finalPos)
      dispenseOperation() # Start Dispensing Cycle
      await asyncio.sleep(10) # wait for the slider to dispense the ink on the substrate
      await asyncio.sleep(5) # wait for ink to settle onto the substrate
      heatPadOneChannel(20,2,30) # Turn on PSU and Timer
      #await asyncio.sleep(5) | could wait for the substrate to cool down, but this might result in bad sintering
      await client.execute(channel = 'manual_move', script = defaultPlatformHeight)
      await client.execute(channel='manual_move', script=centerPos)
      
      # Sintering Process
      await jobProcess(client)
      await asyncio.sleep(20) # Varies. * Something to fix *
      
      
      # Resetting Positions
      await asyncio.execute(channel = 'manual_move', script = returnPos) # move slider back
      
      
      


# Test functions
async def testPILMScript(client):

        # Test Process
        print("Starting Test of PILM process")
        # print("Moving slider to positive end position\n")
        await client.execute(channel='manual_move', script=returnPos) # in case the slider starts off somewhere else at the start.
        await asyncio.sleep(3)
        print("Moving slider to initial position\n")
        await client.execute(channel='manual_move', script=initalPos)
        await asyncio.sleep(5)
        print("Raising platform for Slot Die Process")
        await client.execute(channel='manual_move', script = defaultPlatformHeight) # set the platform to slotDieHeight
        await asyncio.sleep(5)
        #-----------------------------------#

        # --Slot die process-- #
        print("Starting Slot Die Process\n")
        await client.execute(channel='manual_move', script=finalPos)
        await asyncio.sleep(10)
        print("Moving slider to Center position\n")
        await client.execute(channel='manual_move', script=centerPos)
        await asyncio.sleep(5)
        print("Drying Substrate\n")
        heatPadOneChannel(20,2,30) # Turn on the PSU and Timer
        print('\n')
        await asyncio.sleep(2) # works with heatpad timer
        #-----------------------------------#

        # --Sintering Process-- #
        print("Initiating Job\n")
        await jobProcess(client)
        await asyncio.sleep(20) # will depend on how long the job will take. Look to add a boolean condition after the job finishes.
        print("Job Finished\n")
        await asyncio.sleep(5)
        #-----------------------------------#

        # --Resetting Positions-- #
        print("Lowering Platform\n")
        await client.execute(channel='manual_move', script = defaultPlatformHeight)
        print("Moving slider to positive end position\n")
        await client.execute(channel='manual_move', script=returnPos)
        await asyncio.sleep(2)
        print("Test Done")
        
        

# Conditional statment will cause the program to be executed if it's condition is met.
if __name__ == '__main__': # Required * Explain *
    
    #change login_data to your needs
    login_data = {
        'rest_url' : f'http://192.168.2.201:9000',
        'ws_url' : f'ws://192.168.2.201:9000',
        'email' : 'mshuai@stanford.edu',
        'password' : 'aconity'
    }
   
    #change info to your needs
    info = {
        'machine_name' : '1.4404',
        'config_name': 'LinearizedPower_AlignedAxisToChamber',
        'job_name': 'Said',
        'studio_version': 1
    }
    
    result = asyncio.run(executeFun(login_data, info), debug = True) # required to control the machine * explain 