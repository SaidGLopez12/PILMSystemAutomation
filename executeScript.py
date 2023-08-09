# -- Importing Libraries and Files -- # 
import asyncio # for AconityStudio Integration
import os # to clear and clean console
import time
import signal 
signal.signal(signal.SIGINT, signal.SIG_DFL)

# import AconityStudio classes, functions and variables
from AconitySTUDIO_client import AconitySTUDIOPythonClient 
from AconitySTUDIO_client import utils

# import PSU control functions and Syringe Dispense control functions
# from powerSupplyControls import timerFunction, heatPadOneChannel, heatPadMutipleChannels
from syringeDispenseControls import PILMDispenseOperation, dispenseOperation
#------------------------------------------------------------------------------------#


# ----------- Initial Variables and Scripts ----------- # 

# --- Slider Movement Variables And AconityScripts --- #

# default positions for SLIDER 
positiveEndPos = "300"
centerSlidePos = "260"
platformInFrontPos = "210"
platformRearPos = "30"

# AconityScripts for SLIDER
#returnPos = f'$m.move_abs($c[slider], {positiveEndPos}, 250)'
initalPos = '$m.move_abs($c[slider], 60,250)' # move slider to first pos of deposition process
finalPos = '$m.move_abs($c[slider], 165,10)' # move slider to final pos of deposition process | Get's called with the syringe operation function
centerPos = f'$m.move_abs($c[slider],{centerSlidePos},250)' # this will be used to move slider away from the laser during the sintering process | Default Pos too
 

# --- Platform Movement Variables And AconityScripts --- #

# Platform variables for Multi-Layer PILM Process
defaultHeight = "18.00" # default height of the platform from the start, adjust when needed
PILM_Loop = 0 # keep count of the total PILM iterations
layerThickness = 0.05 # adjust platform for desired layer thickness for each iteration
platformIncrementUp = -2.00 
platfromDecrementDown = 2.00

# AconityScript for PLATFORM Movement
defaultPlatformHeight = f'$m.move_abs($c[platform],{defaultHeight}, 200)'
slotDiePlatFormHeight_UP = f'$m.move_rel($c[platform],-1.95,200)' # decreasing the value makes the platform go up
slotDiePlatFormHeight_DOWN = f'$m.move_rel($c[platform],2,200)' #increasing the value makes the platform go down

slotDiePlatFormHeight_UP2 = f'$m.move_rel($c[platform],{platformIncrementUp},200)' # 
slotDiePlatFormHeight_DOWN2 = f'$m.move_rel($c[platform],{platfromDecrementDown},200)'

#------------------------------------------------------------------------------------#

# --- Execution Scripts and Variables for Single and Multi-Layer Process --- #

#--- Includes scripts for Single and Multi-Layer Sintering ---#

singleLayerSinter = \
'''layer= function(){
for(p:$p){
    $m.expose(p[next;$h],$c[scanner_1])
}
  $m.inc_h($g)
}

repeat(layer)'''

# Will not repeat the same layer. Example: If its from layers 1 to 10, the first iteration will be layers 1 and 2.
# It will not be layer 1 and then layer 1 again.
doubleLayerSinter = \
'''
layer = function(){
    for(p:$p){
        $m.expose(p[next;$h],$c[scanner_1])
    }
    $m.inc_h($g)
}
  
repeat(2,layer)

'''



multiLayerSinter = \
'''layer = function(){
    for(p:$p){
        $m.expose(p[next;$h],$c[scanner_1])
    }
    $m.inc_h($g)
}

repeat(3,layer)'''


sinterConfigs = {
      'single_Layer' : singleLayerSinter,
      'double_Layer' : doubleLayerSinter,
      'multi_Layer' :  multiLayerSinter
      
}

# Job Configurations | Select layers and sinter config here
execution_script = sinterConfigs['single_Layer'] # Select the configuration for laser sintering here.
build_parts = 'all' # Don't change. Will select all the existing parts within a job for the sintering process.
start_layer = 8 
currentLayer = start_layer # Used to tell the current layer within the single and multi-layer process.
initalLayer = start_layer # This is only ever used in the multi layer, but only once
end_layer = 10 


#-----------------------------------------------------------------------------------#

async def executeFunc(login_data, info): # main function to call for the PILM process
    
    # create client with factory method
     client = await AconitySTUDIOPythonClient.create(login_data)
     client.studio_version = info['studio_version']
     
    # IMPORTANT:
    # the following CONVENIENCE FUNCTIONS (get_job_id etc) only work if the job_name, machine_name or config_name are unique.
    # If this is not the case, set the attributes job_name, config_name, machine_name manually
     await client.get_job_id(info['job_name'])
     await client.get_machine_id(info['machine_name'])
     await client.get_config_id(info['config_name'])
     

     os.system('cls' if os.name == 'nt' else 'clear') # Clear everything above this code | To get rid of clutter
    #  await client.start_job(execution_script = execution_script,layers = [start_layer, end_layer],parts = build_parts) 
    #  await testScript(client)
    #  await singleLayerPILMFunc(client)
     await multiLayerPILMFun(client, currentLayer, PILM_Loop, platformIncrementUp, platfromDecrementDown)
     
#------------------------------------------------------------------------------------#


# Function for slot-die dispensing process 
async def dispenseFunction(client):
    # await client.execute(channel = 'manual_move', script = finalPos)
    # await PILMDispenseOperation()
    await PILMDispenseOperation()
    asyncio.sleep(1)
    await client.execute(channel = 'manual_move', script = finalPos)
    
# -------------------------------------------------------------------------------------------------------------#
def time_convert(sec):
        mins = sec // 60
        sec = sec & 60
        hours = mins // 60
        mins = mins & 60
        print("Time Lapsed for Sintering = {0}:{1}:{2}\n".format(int(hours),int(mins),sec))
        
async def jobProcess(client, execution_script, start_layer, end_layer, build_parts, currentLayer):
        if currentLayer == start_layer:
           await client.start_job(execution_script = execution_script,layers = [start_layer, end_layer],parts = build_parts) 
        else:
            await client.resume_job() # resume the job, but at the next layer | inital is 7, then this will start at layer 8
    
async def sinterProcess(client):
        loop = asyncio.get_event_loop()
        start_time = time.time()
        loop.run_until_complete(await jobProcess(client,execution_script, start_layer, end_layer, build_parts, currentLayer)) # calls the job process to either start or resume a job
        end_time = time.time()
        
        time_lapsed = end_time - start_time
        time_convert(time_lapsed)

async def multiLayerPILMFun(client, currentLayer,PILM_Loop):
    # things to do before loop statement
    await client.execute(channel = 'manual_move', script = defaultPlatformHeight)
    PILM_Loop += 1 # Start on the first PILM Loop
    
    # Print the Inital Layer of the PILM Process
    print ("Starting Multi-Layer PILM Process ")    
    print(f"Inital Layer: {initalLayer}\n")
    
    #-------------------------------------------#
    
    while currentLayer <= end_layer:
        print(f"\nCurrent Layer: {currentLayer}")
        print(f"Loop: {PILM_Loop}\n")
        
        if PILM_Loop > 2: # Loop 3 will decrease how much the platform will increase in height
            platFormIncrementUp += layerThickness

        # Deposition Process Preparation

        if PILM_Loop == 1:
            await client.execute(channel = 'manual_move', script = centerPos)
        
        if PILM_Loop > 2:
             await client.execute(channel = 'manual_move', script = slotDiePlatFormHeight_UP2)
             
        await asyncio.sleep(1)
        
        # Slot Die Deposition Process
        await client.execute(channel = 'manual_move', script = initalPos)
        await asyncio.sleep(2)
        await client.execute(channel = 'manual_move', script = finalPos)
        # dispenseOperation()
        await asyncio.sleep(10) # wait for the slider to dispense the ink on the PCB 
        
        # Substrate Drying Process
        # PSU Functiton goes here
        # await heatPadMultipleChannels(5,2,10,3)
        await client.execute(channel='manual_move', script = centerPos) # Move it back to starting position
        await asyncio.sleep(7)
        
        # Start Sintering Process
        await sinterProcess(client)
                
        await asyncio.sleep(10) # Varies. * Something to adjust, time it for how long the sintering process takes 
        await client.pause_job() # pause the job    
        currentLayer += 1 # Increase after sintering is done
        
        if PILM_Loop > 2:
              await client.execute(channel = 'manual_move', script = slotDiePlatFormHeight_DOWN2)

        PILM_Loop += 1
    #-------------------------------------------#
    
    await client.stop_job() # Stop the function after the while loop is false and terminates
    
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

    
# -------------------------------------------------------------------------------------------------------------#
#------------------------------------------------------------------------------------#
# Single Layer PILM Process
async def singleLayerPILMFunc(client):
     await client.execute(channel = 'manual_move', script = defaultPlatformHeight)
    
     print ("Starting Single-Layer PILM Process")    
     print(f"Current Layer: {currentLayer}\n")
        
     # Deposition Process Preparation
     await asyncio.sleep(1)
     await client.execute(channel = 'manual_move', script = centerPos)
     await asyncio.sleep(2)
     await client.execute(channel = 'manual_move', script = initalPos)
     
     # Slot Die Deposition Process
     await asyncio.sleep(1)
     await client.execute(channel = 'manual_move', script = finalPos)
     await dispenseFunction(client)
    #  await asyncio.sleep(15) # wait for the slider to dispense the ink on the substrate
     
     # Substrate Drying Process
     #PSU function Goes Here
     
     # Start Sintering Process
     await client.execute(channel='manual_move', script=centerPos) # Move it back to starting position
     await asyncio.sleep(3)
     await client.start_job(execution_script = execution_script,layers = [start_layer, end_layer],parts = build_parts) 
     await asyncio.sleep(10) # Varies. * Something to adjust *   
     await client.stop_job()
    
#------------------------------------------------------------------------------------#

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
    result = asyncio.run(executeFunc(login_data, info), debug = True) # required to control the machine * explain 