import time
import keyboard # for keyboard press
space_pressed = False
timeInSec = 0

def stopWatchFunction(space_pressed,timeInSec):
    keyboard.press_and_release('space')
    while space_pressed != True:
        mins, secs = divmod(timeInSec, 60)
        timer = '{:02d}:{:02d}'.format(mins, secs) # format the variable as 00.00
        print("Time Active:",timer, end="\r") # print the current timer value, create an end variable that creates a new line.
        time.sleep(1) 
        timeInSec += 1
        
        if keyboard.is_pressed('space'):
            space_pressed = True   
        
        
    print(f"\nTotal Time: {timeInSec}")   
    
    
    
    
stopWatchFunction(space_pressed, timeInSec)