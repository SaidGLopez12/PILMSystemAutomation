import asyncio
import sys
import signal

signal.signal(signal.SIGINT, signal.SIG_DFL)
from AconitySTUDIOpy.AconitySTUDIO_client import AconitySTUDIO_client as AconitySTUDIOPythonClient

async def execute(login_data,info): # async is required, as it waits for a signal to continue
    #create client with Factory Method
    '''
    Factory Method is a Creatinal Design Pattern that allows an
    interface or a class to create an object, but lets subclasses
    decide which class or object to instantiate
    '''
    
    
    
    # can I put any value or doees it need to be very specific
    
    ### Create Client ##
    client = await AconitySTUDIOPythonClient.create(login_data,studio_version = info['studio_version'])
    
    ### Logging Method (Optional) ###

    
    ### Session State ###
    print('\n\n ### Session State ### \n\n')
    
    ### Machine ### | MACHINE ID is required to execute a task
    machine_name = info['machine_name']
    machine_id = await client.gateway.get_machine_id(machine_name)
    
    '''
    ### (START) CONFIG ### | The ID of the configuration is REQUIRED for it to work
    config_name = info['config_name']
    config_id = await client.gateway.get_config_id(config_name)
    
    if await client.gateway.config_state(config_id) == "inactive":
        await client.gateway.start_config(config_id)
    else:
        print("Config is already starting")
    
    '''
    
    ### COMPONENTS ###
    component_id = 'light' # backlight
    
    ### TASK EXECUTION ###
    await client.task.off(machine_id,component_id)
    await asyncio.sleep(2)
    await client.task.on(machine_id, component_id)
    
    '''
   ### JOB ###
    job_name = info['job_name']
    job_id = await client.job.get_job_id(job_name)
    
   '''
     
if __name__ == '__main__':


    '''
    Example on how to use the python client for executing scripts.
    Please change login_data and info to your needs.
    '''

    # #### LOGIN DATA #### #

    login_data = {
        'rest_url' : f'http://localhost:9000',
        'ws_url' : f'ws://localhost:9000',
        'email' : 'admin@aconity3d.com',
        'password' : 'passwd'
    }

    # #### SESSION STATE #### #

    info = {
        'machine_name' : 'SimMIDI',
        'config_name' : 'AconityMidi_Three_Scanner_Simulator',
        'job_name': 'python_script_job',
        'studio_version' : 2
    }

    result = asyncio.run(execute(login_data, info), debug=True)
    

    
    