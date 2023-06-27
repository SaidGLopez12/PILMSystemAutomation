import json

import logging

from time import strftime

class TaskAPI:

    def __init__(self, execution_api, job_api, studio_version):
        
        self._logger = logging.getLogger("AconitySTUDIO TASK API")

        self.studio_version = studio_version

        self.wait = True

        if studio_version is not None and studio_version == 1:

            self.wait = False

        self._execution_api = execution_api

        self._job_api = job_api
       
    def _current_time(self):
        
        return strftime('%Y-%m-%d %H:%M:%S')

    async def on(self, machine_id, component, channel="manual_switch"):
        
        script_on = f"$m.on($c[{component}])"
    
        return await self._execution_api.execute_Script(machine_id=machine_id, channel=channel, script=script_on, wait=self.wait)

    async def on_value(self, machine_id, component, value, channel="manual_switch"):

        script_on = f"$m.on($c[{component}], {value})"
    
        return await self._execution_api.execute_Script(machine_id=machine_id, channel=channel, script=script_on, wait=self.wait)

    async def off(self, machine_id, component, channel="manual_switch"):

        script_off = f"$m.off($c[{component}])"
    
        return await self._execution_api.execute_Script(machine_id=machine_id, channel=channel, script=script_off, wait=self.wait)

    async def move_rel(self, machine_id, component, distance, channel="manual_move"):
        
        move_script = f"$m.move_rel($c[{component}],{distance})"
    
        return await self._execution_api.execute_Script(machine_id=machine_id, channel=channel, script=move_script, wait=self.wait)

    async def move_abs(self, machine_id, component, distance, channel="manual_move"):
        
        move_script = f"$m.move_abs($c[{component}], {distance})"
    
        return await self._execution_api.execute_Script(machine_id=machine_id, channel=channel, script=move_script, wait=self.wait)

    async def ramp_heating(self, machine_id, target_temp, duration, p_gain, i_gain, d_gain, channel="manual"):
        
        heating_script = f"$m.ramp_heating({target_temp},{duration},{p_gain},{i_gain},{d_gain})"
    
        return await self._execution_api.execute_Script(machine_id=machine_id, channel=channel, script=heating_script, wait=self.wait)

    async def add_layer(self, machine_id, channel="manual"):
        
        add_layer_script = f"$m.add_layer($g)"
    
        return await self._execution_api.execute_Script(machine_id=machine_id, channel=channel, script=add_layer_script, wait=self.wait)
    
    async def expose(self, machine_id, job_id, layer, parts, scanner="scanner_1", channel="manual"):
        
        jobHandler = await self._job_api.create_JobHandler(job_id, self.studio_version)

        expose_script = jobHandler.create_init_script(layers=[layer, layer+1], parts=parts)
    
        expose_script += "\nfor(p:$p){\n"
        expose_script += f"$m.expose(p[next;$h],$c[{scanner}])"
        expose_script +="\n}"
      
        return await self._execution_api.execute_Script(machine_id=machine_id, channel=channel, script=expose_script, wait=self.wait)
    
    