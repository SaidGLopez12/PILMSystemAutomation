# -- Importing Libraries and Files -- # 
import asyncio
import os
import signal
signal.signal(signal.SIGINT, signal.SIG_DFL)


from AconitySTUDIO_client import AconitySTUDIOPythonClient 
from AconitySTUDIO_client import utils

#from powerSupplyControls import timerFunction, heatPadOneChannel, heatPadMultipleChannels
from syringeDispenserControls import dispenseOperation
#-------------------------------------#

# -- Initial Variables and Scripts -- # 

# -- Slider Movement Variables And AconityScripts-- #

# default positions for slider
positiveEndPos = "300"
centerSlidePos = "260"
platformInFrontPos = "210"
platformRearPos = "30"

# AconityScripts for Slider
#returnPos = f'$m.move_abs($c[slider], {positiveEndPos}, 250)'
initalPos = '$m.move_abs($c[slider], 50,250)' # move slider to first pos of deposition process
finalPos = '$m.move_abs($c[slider], 165,10)' # move slider to final pos of deposition process | Get's called with the syringe operation function
centerPos = f'$m.move_abs($c[slider],{centerSlidePos},250)' # this will be used to move slider away from the laser during the sintering process | Default Pos too
 
# ------------------------------------ #

# -- Platform Movement Variables And AconityScripts-- #
defaultHeight = "17.70"
layersProcessed = 0
platformIncrementUp = -2
platfromDecrementDown = 2 

# AconityScript for Platform Movement
defaultPlatformHeight = f'$m.move_abs($c[platform],{defaultHeight}, 200)'
slotDiePlatFormHeight_UP = f'$m.move_rel($c[platform],-1.95,200)' # decreasing the value makes the platform go up
slotDiePlatFormHeight_DOWN = f'$m.move_rel($c[platform],2,200)' #increasing the value makes the platform go down

slotDiePlatFormHeight_UP2 = f'$m.move_rel($c[platform],{platformIncrementUp},200)'
slotDiePlatFormHeight_DOWN2 = f'$m.move_rel($c[platform],{platfromDecrementDown},200)'

#-------------------------------------#

# --- Execution Scripts and Variables for Single and Multi-Layer Process --- #

SinteringProcess = \
'''layerProcess = function(){
    for(p:$p){
        $m.expose(p[next;$h],$c[scanner_1])
    }
    
}
repeat(layerProcess)'''

ExecutionScripts = {
      'Sinter' : SinteringProcess
}

execution_script = ExecutionScripts['Sinter']
build_parts = 'all'
start_layer = 8
currentLayer = start_layer
initalLayer = start_layer
end_layer = 8

# ---------------------------------------------------------------#

async def executeFunc(login_data, info):
    
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
     

async def multiLayerPILMFun(client, currentLayer):
    
     await client.execute(channel = 'manual_move', script = defaultPlatformHeight)
     
     # Main Process # 
     print ("Starting PILM Process ")    
     print(f"Inital Layer: {initalLayer}\n")
     
     # Loop for Layering Process
     while currentLayer <= end_layer:
         print(f"Current Layer: {currentLayer}\n")
         
         if layersProcessed == 0 & layersProcessed < 0:
             await client.execute(channel = 'manual_move', script = defaultPlatformHeight) # incase the platfrom is not in this position
         else:
             platformIncrementUp += 0.05
             await client.execute(channel = 'manual_move', script = slotDiePlatFormHeight_UP2)
    
    # Deposition Process Preparation
     await asyncio.sleep(1)
     await client.execute(channel = 'manual_move', script = centerPos)
     await asyncio.sleep(2)
     await client.execute(channel = 'manual_move', script = initalPos)
     await asyncio.sleep(2)
     
     # Slot Die Deposition Process
     