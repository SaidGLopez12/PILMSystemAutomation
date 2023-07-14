#--importing libraries and files--# * Explain
import asyncio # Required
import aiohttp
import json
import sys
import os
import time
import logging
from datetime import datetime
from pytz import timezone, utc
import signal
signal.signal(signal.SIGINT, signal.SIG_DFL)

from AconitySTUDIO_client import AconitySTUDIOPythonClient # Required * Explain *
from AconitySTUDIO_client import utils # Required * Explain *

import powerSupplyControls
import syringeDispenserControls
#--------------------------------#

async def pauser(pause,messages):
    print('')
    for i in range(pause):
        sys.stdout.write(f'\rWaiting for {pause-i} seconds {messages}')
        sys.stdout.flush()
        await asyncio.sleep(1) # simulating waiting time.
    print('')

   
    
async def mainFunction(login_data, info):
    
    # create client with factory method
    client = await AconitySTUDIOPythonClient.create(login_data)
    client.studio_version = info['studio_version']
    
    # IMPORTANT:
    # the following CONVENIENCE FUNCTIONS (get_job_id etc) only work if the job_name, machine_name or config_name are unique.
    # If this is not the case, set the attributes job_name, config_name, machine_name manually
    await client.get_job_id(info['job_name'])
    await client.get_machine_id(info['machine_name'])
    await client.get_config_id(info['config_name'])


    os.system('cls' if os.name == 'nt' else 'clear') # clears everything within the console.
    await testScript(client) # you need to await the function as well
    
# Test functions (will be called in mainFunction())
async def testScript(client):
    # -- Slider Movement Variables -- #
        #default aconity positions for slider
        positiveEndPos = "395" # the numbers are readable as strings
        centerSlidePos = "260"
        platformInFrontPos = "210"
        platformRearPos = "30"
    #--------------------------------#
    # -- Platform Movement Variables -- #
        dispenseHeight = "17"
        defaultHeight = "18"

    #-----------------------------------#
        # AconitySCRIPT commands #   
        returnPos = f'$m.move_abs($c[slider], {positiveEndPos}, 299)' # 300 is max vel
        # initalPos = '$m.move_abs($c[slider], 180,300)' # 20mm/s for dispensing
        # finalPos = '$m.move_abs($c[slider], 75,20)' # 20mm/s for dispensing
        initalPos = '$m.move_abs($c[slider], 75,300)'
        finalPos = '$m.move_abs($c[slider], 180,10)'
        centerPos = f'$m.move_abs($c[slider],{centerSlidePos},299)'

        slotDieHeight = f'$m.move_abs($c[platform],{dispenseHeight},200)'
        defaultPos = f'$m.move_abs($c[platform],{defaultHeight}, 200)'

        #-----------------------#
        # Test Process
        print("Starting Test of PILM process")
        await asyncio.sleep(2)
        # # print("Moving slider to positive end position\n")
        await client.execute(channel='manual_move', script=returnPos) # in case the slider starts off somewhere else.
        await asyncio.sleep(5)
        print("Moving slider to initial position\n")
        await client.execute(channel='manual_move', script=initalPos)
        await asyncio.sleep(5)
        print("Raising platform")
        await client.execute(channel='manual_move', script = slotDieHeight) # set the platform to slotDieHeight
        await asyncio.sleep(5)

        #slot die process
        print("Starting Slot Die Process\n")
        await client.execute(channel='manual_move', script=finalPos)
        syringeDispenserControls.dispenseOperation()
        await asyncio.sleep(10)
        print("Moving slider to Center position\n")
        await client.execute(channel='manual_move', script=centerPos)
        await asyncio.sleep(5)
        print("Drying Substrate\n")
        powerSupplyControls.heatPadOneChannel(20,2,30)
        print('\n')
        await asyncio.sleep(2) # works with heatpad timer

        #Sintering Process
        print("Initiating Job\n")
        await jobProcess(client)
        await asyncio.sleep(20) # will depend on how long the job will take. Look to add a boolean condition after the job finishes.
        print("Job Finished\n")
        await asyncio.sleep(5)

        # Setting to default settings
        print("Lowering Platform\n")
        await client.execute(channel='manual_move', script = defaultPos)
        print("Moving slider to positive end position\n")
        await client.execute(channel='manual_move', script=returnPos)
        await asyncio.sleep(2)
        print("Test Done")
        

        
      
async def jobProcess(client):
        # Start a job. 
        execution_script = utils.EXECUTION_SCRIPTS['only_expose']
        build_parts = 'all'
        start_layer = 7
        end_layer = 7

        await client.start_job(execution_script = execution_script,
                                layers = [start_layer, end_layer],
                                parts = build_parts)
        

if __name__ == '__main__': # Required * Explain *
    
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
    
    result = asyncio.run(mainFunction(login_data, info), debug = True) # required to control the machine * explain 