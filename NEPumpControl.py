import nesp_lib
import asyncio
import pyvisa
import time
from nesp_lib import Port,Pump,PumpingDirection
# Constructs the port to which the pump is connected.
port = Port('COM6')
# Constructs the pump connected to the port.
pump = Pump(port)
# Sets the syringe diameter of the pump in units of millimeters.
pump.syringe_diameter = 30.0
# Sets the pumping direction of the pump.
pump.pumping_direction = PumpingDirection.INFUSE
# Sets the pumping volume of the pump in units of milliliters.
pump.pumping_volume = 1.0
# Sets the pumping rate of the pump in units of milliliters per minute.
pump.pumping_rate = 20.0

pump.run(False)

print("Hello World")