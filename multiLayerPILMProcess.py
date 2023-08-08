import asyncio

defaultPlatformHeight = "Hello"
centerPos = "Yeah"
initalPos = "Yea"
finalPos = "Ye"
execution_script = "1"
slotDiePlatFormHeight_UP2 = "1"
slotDiePlatFormHeight_DOWN2 = "2"


initalLayer = 1
currentLayer = initalLayer
start_Layer = 1
end_Layer = 5
PILM_Loop = 0

platFormIncrementUp = -2.00
layerThickness = 0.05


async def multiLayerPILMFun(client, currentLayer,PILM_Loop):
    # things to do before loop statement
    await client.execute(channel = 'manual_move', script = defaultPlatformHeight)
    PILM_Loop += 1 # Start on the first PILM Loop
    
    # Print the Inital Layer of the PILM Process
    print ("Starting Multi-Layer PILM Process ")    
    print(f"Inital Layer: {initalLayer}\n")
    
    #-------------------------------------------#
    
    while currentLayer <= end_Layer:
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
        await client.execute(channel='manual_move', script=centerPos) # Move it back to starting position
        await asyncio.sleep(7)
        
        # Start Sintering Process
        if currentLayer == start_Layer:
           await client.start_job(execution_script = execution_script,layers = [start_Layer, end_Layer],parts = build_parts) 
        else:
            await client.resume_job() # resume the job, but at the next layer | inital is 7, then this will start at layer 8
                
        await asyncio.sleep(10) # Varies. * Something to adjust, time it for how long the sintering process takes 
        await client.pause_job() # pause the job    
        currentLayer += 1 # Increase after sintering is done
        
        if PILM_Loop > 2:
              await client.execute(channel = 'manual_move', script = slotDiePlatFormHeight_DOWN2)

        PILM_Loop += 1
    #-------------------------------------------#
    
    await client.stop_job() # Stop the function after the while loop is false and terminates