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
    await client.get_config_id(info['condig_name'])
    
    # change printing parameters
    os.system('cls' if os.name == 'nt' else 'clear') # clears everything within the console.
    testScript()
    
    
    


# Test functions (will be called in mainFunction())
async def testScript(client):
    # -- Slider Movement Variables --#
    returnPos = 'm.move_abs($c[slider], -120)'
    initalPos = 'm.move_abs($c[slider], 125)'
    finalPos = 'm.move_abs($c[slider], 100)'
    print("Starting Test of PILM process")
    await asyncio.sleep(1)
    await client.execute(channel='manual_move', script=returnPos)
    await asyncio.sleep(1)
    await client.execute(channel='manual_move', script=initalPos)
    await asyncio.sleep(1)
    await client.execute(channel='manual_move', script=finalPos)
    # slider movement (move to intial, final and then return position)
    # Start it at return
    # move it by 125 mm
    # Create the slot-die process
    # Final position should be 175mm (so move it 50mm)
    # move it 
    
    
    # - slider movement
    # - slot-die process
    # - intiating, pausing and ending job (for specifc amount of layers)
    

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