#--importing libraries and files--# * Explain
import asyncio # Required for Server and Client communication
import os
import signal 
signal.signal(signal.SIGINT, signal.SIG_DFL)

from AconitySTUDIO_client import AconitySTUDIOPythonClient # Required | Imports libraries and the AconitySTUDIOPythonClient class from this file
from AconitySTUDIO_client import utils # Required | Imports libraries and the utils. This file does not have a utils class, so is it required?

# will require both devices to be plugged into the aconity machine for it to work
#from powerSupplyControls import timerFunction, heatPadOneChannel, heatPadMutipleChannels 
#from syringeDispenserControls import dispenseOperation
#--------------------------------------#

# -- Inital Variables and Instantiations -- #
# --- Slider Movement Variables --- #

# default aconity positions for slider 
positiveEndPos = "300" # the numbers are readable as strings
centerSlidePos = "260"
platformInFrontPos = "210"
platformRearPos = "30"

# -- Platform Movement Variables -- #
# dispenseHeight = "18"
defaultHeight = "15.95"
layersProcessed = 0
layerThickness_1 = -2 # will make it go up
layerThickness_2 = 2 # make it go down

#---------------------------------------#

# --- AconityScript Commands --- #
# They are stored in variables that can be used in the execute commands that are readable by the machine.
# Slider | AconityScript(reference, abs pos val, vel)
returnPos = f'$m.move_abs($c[slider], {positiveEndPos}, 250)' # 300 is max vel. Go less since a lot of error messages pop up when reaching this velocity
initalPos = '$m.move_abs($c[slider], 80,250)'
finalPos = '$m.move_abs($c[slider], 165,10)'
centerPos = f'$m.move_abs($c[slider],{centerSlidePos},250)' # this will be used to move slider away from the laser during the sintering process

# Platform
defaultPlatformHeight = f'$m.move_abs($c[platform],{defaultHeight}, 200)'
slotDiePlatFormHeight_UP = f'$m.move_rel($c[platform],-1.95,200)' # decreasing the value makes the platform go up
slotDiePlatFormHeight_DOWN = f'$m.move_rel($c[platform],2,200)' #increasing the value makes the platform go down
#---------------------------------#
# Init/Resume
# addParts

# preStart
# preStartParameters
#--------------------------#

# --- Execution Scripts and Variables for Multi-Layer Process --- #
SinteringProcess = \
'''layer= function(){
for(p:$p){
    $m.expose(p[next;$h],$c[scanner_1])
}
  $m.inc_h($g)
}

repeat(2,layer)'''

ExecutionScripts = {
      'Sinter' : SinteringProcess
}

execution_script = ExecutionScripts['Sinter']
build_parts = 'all'
start_layer = 1
end_layer = 40
currentLayer = start_layer
initalLayer = start_layer

# ---------------------------------------------------------------#

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
    # await client.execute(channel = 'manual_move', script = defaultPlatformHeight)
    # await asyncio.sleep(2)
    # await client.execute(channel = 'manual_move', script = slotDiePlatFormHeight_DOWN)
    # await asyncio.sleep(2)
    # await client.execute(channel = 'manual_move', script = slotDiePlatFormHeight_UP)
    # await client.start_job(execution_script = execution_script,layers = [start_layer, end_layer],parts = build_parts) 
    await PILMFun(client,currentLayer) # you need to await defined functions as well.
    



# AM Processes

# PILM
async def PILMFun(client,currentLayer):
      
      await client.execute(channel = 'manual_move', script = defaultPlatformHeight)

      print("Starting PILM Process\n")   
      print(f"Inital Layer: {initalLayer}\n")
      #Loop For Multi-Layer
      while currentLayer <= end_layer:
        print(f"Current Layer: {currentLayer}\n")
 
        await client.execute(channel = 'manual_move', script = centerPos) # incase the slider is not in this position from the start
        await asyncio.sleep(2)
        await client.execute(channel = 'manual_move', script = initalPos)
        await asyncio.sleep(3)
      
      
        #Slot Die Process
        await client.execute(channel = 'manual_move', script = finalPos)
        #dispenseOperation() # Start Dispensing Cycle

        await asyncio.sleep(15) # wait for the slider to dispense the ink on the substrate
        await client.execute(channel='manual_move', script=centerPos)
      
      
        # Sintering Process
        if initalLayer == start_layer:
           await client.start_job(execution_script = execution_script,layers = [start_layer, end_layer],parts = build_parts) 
           
        else:
            await client.resume_job() # resume the job, but at the next layer | inital is 7, then this will start at layer 8
        currentLayer += 1    
        await asyncio.sleep(5) # Varies. * Something to adjust *
        await client.pause_job() # pause the job
    
        # await client.execute(channel = 'manual_move', script = slotDiePlatFormHeight_DOWN)    
       

      await client.stop_job()

      
      
      
      
      


# Test functions - 
async def testPILMScript(client):
        #-----------------------------------#
        print("Testing PILM Process")
        print("====================\n")
        print("Moving Platform and Slider to default positions\n")
        #await client.execute(channel = 'manual_move', script = defaultPlatformHeight) # incase the platform is not in this position from the start
        await asyncio.sleep(1)
        await client.execute(channel = 'manual_move', script = returnPos) # incase the slider is not in this position from the start
        await asyncio.sleep(2)

        print("Preparing for slot die process")
        print("====================\n")

        print("Moving Slider to inital position")
        await client.execute(channel = 'manual_move', script = initalPos)
        await asyncio.sleep(1)
        print("Raising Platform\n")
        #await client.execute(channel='manual_move', script = slotDiePlatFormHeight) # set the platform to slotDieHeight
        #-----------------------------------#
        
        await asyncio.sleep(3)
        
         #-----------------------------------#
        print("Starting Slot Die Process")
        print("====================\n")
        await client.execute(channel='manual_move', script=finalPos)
        #dispenseOperation() # Start Dispense Cycle
        await asyncio.sleep(10)
        await asyncio.sleep(5)
        print("Drying Substrate")
        #heatPadOneChannel(20,2,30) # Turn on the PSU and Timer
        await asyncio.sleep(2) # works with heatpad timer

        print("\nMoving slider to Center Position\n")
        await client.execute(channel='manual_move', script=centerPos)
         #-----------------------------------#

         #-----------------------------------#
        print("Starting Sintering Process")
        print("====================\n")
        print("Initiating Job")
        await client.start_job(execution_script = execution_script,layers = [start_layer, end_layer],parts = build_parts)
        await asyncio.sleep(20) # will depend on how long the job will take. Look to add a boolean condition after the job finishes.
        print("Job Finished\n")
        await asyncio.sleep(5)
        #-----------------------------------#

        # --Reset Positions-- #
        print("Resetting Positions")
        print("====================\n")
        print("Moving Platform to default height")
        #await client.execute(channel='manual_move', script = defaultPlatformHeight)
        print("Moving slider to positive end position\n")
        await client.execute(channel='manual_move', script=returnPos)
        await asyncio.sleep(1)
        print("Test Done")
         #-----------------------------------#
        

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
    #CuO w/EG on PCB _various hatching
    
    result = asyncio.run(executeFun(login_data, info), debug = True) # required to control the machine * explain 
    
    
    # async def multiLayerPILMFun(client, currentLayer, PILM_Loop, platformIncrementUp, platfromDecrementDown):
#      await client.execute(channel = 'manual_move', script = defaultPlatformHeight) # REQUIRED for Absolute Movement
#      PILM_Loop += 1 # Start on the first PILM Loop

#      # Main Process # 
#      print ("Starting Multi-Layer PILM Process ")    
#      print(f"Inital Layer: {initalLayer}\n")
     
#      # Loop for Layering Process
#      while currentLayer <= end_layer:
#          print(f"\nCurrent Layer: {currentLayer}")
#          print(f"Loop: {PILM_Loop}\n")
        
#          if PILM_Loop > 1:
#              platformIncrementUp += layerThickness
#             #   platfromDecrementDown += layerThickness
             
#         # Deposition Process Preparation
#          await asyncio.sleep(1)
#          await client.execute(channel = 'manual_move', script = centerPos)
#          await asyncio.sleep(1)
         
#          # Lower platform for slider 
#          if PILM_Loop > 0:
#               await client.execute(channel = 'manual_move', script = slotDiePlatFormHeight_DOWN2)
              
#         # Slot Die Deposition Process
#          await client.execute(channel = 'manual_move', script = initalPos)
#          await asyncio.sleep(2)
#          await client.execute(channel = 'manual_move', script = finalPos)
#         #  dispenseOperation()
#         #  await dispenseFunction(client)
#          await asyncio.sleep(10) # wait for the slider to dispense the ink on the substrate
         
#         # Substrate Drying Process
#         #PSU function Goes Here
#         #  await heatPadMutipleChannels(5,2,10,3)
#          await client.execute(channel='manual_move', script=centerPos) # Move it back to starting position
#          await asyncio.sleep(7)
         
#         # Start Sintering Process
#          if currentLayer == start_layer:
#            await client.start_job(execution_script = execution_script,layers = [start_layer, end_layer],parts = build_parts) 
#          else:
#             await client.resume_job() # resume the job, but at the next layer | inital is 7, then this will start at layer 8
                
#          await asyncio.sleep(10) # Varies. * Something to adjust, time it for how long the sintering process takes 
#          await client.pause_job() # pause the job    
#          currentLayer += 1 # Increase after sintering is done
         
#         # Preparing for next layer
#          if PILM_Loop > 0:
#              await client.execute(channel = 'manual_move', script = slotDiePlatFormHeight_UP2)

            
#          PILM_Loop += 1  
             
#      await client.stop_job() # Stop the function after the while loop is false and terminates

    