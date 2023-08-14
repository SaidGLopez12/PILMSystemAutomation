# -- Importing Libraries and Files -- # 
import asyncio # for AconityStudio Integration
import os # to clear and clean console
import sys # to exit out of program when needed
import time # time delays
import keyboard # for keyboard inputs | For PSU with Stopwatch
import signal 
signal.signal(signal.SIGINT, signal.SIG_DFL)

# import AconityStudio classes, functions and variables
from AconitySTUDIO_client import AconitySTUDIOPythonClient 
from AconitySTUDIO_client import utils

# import PSU control functions and Syringe Dispense control functions
from powerSupplyControls import timerFunction, MutipleChannels_StopWatch, heatPadOneChannel, heatPadMutipleChannels
from syringeDispenseControls import PILMDispenseOperation
#------------------------------------------------------------------------------------#


# ----------- Initial Variables and Scripts ----------- # 

# --- Slider Movement Variables And AconityScripts --- #

# default positions for SLIDER 
positiveEndPos = "300"
centerPos = "300"
platformInFrontPos = "210"
platformRearPos = "30"

# Slot-die + Slider Positions
start_postion = "105"
end_position = "145"

# AconityScripts for SLIDER
slotDieStartPos = f'$m.move_abs($c[slider], {start_postion},250)' # move slider to first pos of deposition process
slotDieEndPos = f'$m.move_abs($c[slider], {end_position},10)' # move slider to final pos of deposition process | Get's called with the syringe operation function
centerPos_Slider = f'$m.move_abs($c[slider],{centerPos},250)' # this will be used to move slider away from the laser during the sintering process | Default Pos too
 

# --- Platform Movement Variables And AconityScripts --- #

# Platform variables for Multi-Layer PILM Process
defaultHeight = "18.70" # default height of the platform from the start, adjust when needed
PILM_Loop = 0 # keep count of the total PILM iterations
layerThickness = 0.20 # adjust platform for desired layer thickness for each iteration
platformIncrementUp = -2.00 + layerThickness
platfromDecrementDown = 2.00

# AconityScript for PLATFORM Movement
defaultPlatformHeight = f'$m.move_abs($c[platform],{defaultHeight}, 200)'
slotDiePlatFormHeight_UP = f'$m.move_rel($c[platform],{platformIncrementUp},200)' # 
slotDiePlatFormHeight_DOWN = f'$m.move_rel($c[platform],{platfromDecrementDown},200)'

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
start_layer = 2
end_layer = 2
currentLayer = start_layer # Used to tell the current layer within the single and multi-layer process.
initalLayer = start_layer # This is only ever used in the multi layer, but only once



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
     await check_List()
    #  await client.start_job(execution_script = execution_script,layers = [start_layer, end_layer],parts = build_parts) 
     await singleLayerPILMFunc(client)
    #  await multiLayerPILMFun(client, currentLayer, PILM_Loop, platformIncrementUp)

#------------------------------------------------------------------------------------#
async def check_List():   
 checkListApproved = False
 userInput = ' '
 
 print("\nChecklist Before PILM Process")
 print("============================\n")
    
 print("P.I.L.M Configuration")
 print("----------------------------------\n")
 print("Info")
 print("-----\n")
 print(f"Job Name: {info['job_name']}")
 print(f"Config Name: {info['config_name']}\n")
    
 print("Layer Configuration")
 print("-------------------\n")
 print(f"Start Layer: {start_layer}")
 print(f"End Layer: {end_layer}")
 print(f"Starting Platform Height: {defaultHeight}")
 print(f"Layer Thickness: {layerThickness}")
 print(f"platformIncrementUp: {platformIncrementUp}")
 print(f"platformDecrementDown: {platfromDecrementDown}\n")   

 while checkListApproved != True:       
  print("Are you okay with this? Y or N")
  userInput = input()
  
  if userInput == 'Y' or userInput == 'y':
    #  print("Starting P.I.L.M Process")
     checkListApproved == True
     return True
  elif userInput == 'N' or userInput == 'n':
    print("Reconfigure Settings.\n")
    sys.exit()
  else:
      print("Wrong Input, try again. \n")
      checkListApproved == False 
    
    

 
# -------------------------------------------------------------------------------------------------------------#

# Function for slot-die dispensing process 
async def dispenseFunction(client):
    await client.execute(channel = 'manual_move', script = slotDieEndPos)
    await PILMDispenseOperation()
    
    
async def multiLayerPILMFun(client, currentLayer, PILM_Loop, platformIncrementUp):
    # things to do before loop statement
    await client.execute(channel = 'manual_move', script = defaultPlatformHeight)
    PILM_Loop += 1 # Start on the first PILM Loop
    
    # Print the Inital Layer of the PILM Process
    print ("Starting Multi-Layer PILM Process ")    
    print(f"Inital Layer: {initalLayer}\n")
    
    #-------------------------------------------#
    
    while currentLayer <= end_layer:
        print(f"\nCurrent Layer: {currentLayer}")
        print(f"Loop: {PILM_Loop}")
        print(f"platformUp: {platformIncrementUp}")
        print(f"layerThickness: {layerThickness}\n")
        
        # Deposition Process Preparation
        if PILM_Loop == 1: # At the first loop, move slider to center position.
            await client.execute(channel = 'manual_move', script = centerPos_Slider)
        
        if PILM_Loop > 1: # After the first loop, start moving the platform DOWN each following loop
             await client.execute(channel = 'manual_move', script = slotDiePlatFormHeight_DOWN)
             
        await asyncio.sleep(1)
        
        # Slot Die Deposition Process
        await client.execute(channel = 'manual_move', script = slotDieStartPos) # Move slider to the start position of the dispensing process
        await asyncio.sleep(2)

        if PILM_Loop > 1: # After the first loop, start moving the platform UP each following loop
            await client.execute(channel = 'manual_move', script = slotDiePlatFormHeight_UP)


        await dispenseFunction(client)
        await asyncio.sleep(5) # wait for the slider to dispense the ink on the PCB 
        
        
        await client.execute(channel='manual_move', script = centerPos_Slider) # Move the slider back to center position
        await asyncio.sleep(3)
        
        # Substrate Drying Process
        # PSU Functiton goes here
        # await MutipleChannels_StopWatch
        await heatPadMutipleChannels(9,3,600,2)

        # Start Sintering Process
        if currentLayer == start_layer:
            await client.start_job(execution_script = execution_script,layers = [start_layer, end_layer],parts = build_parts) 
        else:
            await client.resume_job() # resume the job, but at the next layer | inital is 7, then this will start at layer 8

        await asyncio.sleep(10) # Varies.  Something to adjust, time it for how long the sintering process takes 
        await client.pause_job() # pause the job after the layer is done sintering
        currentLayer += 1 # Change the current layer to the next layer
        PILM_Loop += 1 # add 1 to the total loops processed
    #-------------------------------------------#
    
    await client.stop_job() # Stop the job after the while loop is false and exit the program
     
# -------------------------------------------------------------------------------------------------------------#

# Single Layer PILM Process
async def singleLayerPILMFunc(client):
     await client.execute(channel = 'manual_move', script = defaultPlatformHeight) # set the platform to the starting height
    
     print ("Starting Single-Layer PILM Process")    
     print(f"Current Layer: {currentLayer}\n")
        
     # Deposition Process Preparation
     await asyncio.sleep(1)
     await client.execute(channel = 'manual_move', script = centerPos_Slider)
     await asyncio.sleep(2)
     await client.execute(channel = 'manual_move', script = slotDieStartPos)
     
     # Slot Die Deposition Process
     await asyncio.sleep(1)
     await dispenseFunction(client) # calls the slotDieStartPos and the PILMDispenseOperation
     await asyncio.sleep(5) # wait for the slider to dispense the ink on the substrate

     # Prepare for the Sintering Process
     await client.execute(channel='manual_move', script=centerPos_Slider) # Move it back to starting position
    
    # Substrate Drying Process
    #PSU function Goes Here
     await asyncio.sleep(3)
      # await MutipleChannels_StopWatch
     await heatPadMutipleChannels(9,3,5,2)

    # # Sintering Process
     await client.start_job(execution_script = execution_script,layers = [start_layer, end_layer],parts = build_parts) 
     await asyncio.sleep(10) # Varies. * Something to adjust depending on how long each layer takes*   
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

    # LinearizedPower_AlignedAxisToChamber
    # http://192.168.2.201:9000
    # //192.168.2.201:9000
   
    #change info to your needs
    info = {
        'machine_name' : '1.4404',
        'config_name': 'LinearizedPower_AlignedAxisToChamber',
        'job_name': 'CuO_multilayer',
        'studio_version': 1
    }
    result = asyncio.run(executeFunc(login_data, info), debug = True) # required to control the machine * explain 
  
    
     