import json

import asyncio
import aiohttp

import logging

from . import JobHandler

class JobAPI:

    def __init__(self, connection_api, gateway_api, execution_api, studio_version):

        # #### LOGGING #### #

        self._logger = logging.getLogger("AconitySTUDIO Job API")

        # #### CONNECTION API #### #

        self._connection_api = connection_api

        # #### GATEWAY API #### #

        self._gateway_api = gateway_api

        # #### EXECUTION API #### #

        self._execution_api = execution_api

        self.time_out_script_routes = 5

        self.jobHandler = None

        # saves layer information for a job (start, end, number of AddLayerCommand's) #
        self.job_info = {'AddLayerCommands': 0}

        self.studio_version = studio_version

    async def connect(self):

        '''
        Factory class method to initialize a client.
        Convenient as this function takes care of logging in and creating a websocket connection.
        It will also set set up a ping, to ensure the connection will not be lost.

        :param login_data: required keys are `rest_url`, `ws_url`, `password` and `email`.
        :type login_data: dictionary

        Usage::

            login_data = {
                'rest_url' : 'http://192.168.1.1:2000',
                'ws_url' : 'ws://192.168.1.1:2000',
                'email' : 'admin@yourcompany.com',
                'password' : '<password>'
            }
            client = await AconitySTUDIO_client.create(login_data)

        '''

        asyncio.create_task(self._track_AddLayerCommand())

        self._logger.info('JOB API CONNECTED')

        return self

    ###########
    # SCRIPTS #
    ###########

    EXECUTION_SCRIPT_STANDARD = \
    '''layer = function(){
        for(p:$p){
            $m.expose(p[next;$h],$c[scanner_1])
        }
        $m.add_layer($g)
    }
    repeat(layer)'''

    EXECUTION_SCRIPT_ONLY_EXPOSE = \
    '''layer = function(){
        for(p:$p){
            $m.expose(p[next;$h],$c[scanner_1])
        }
        $m.inc_h($g)
    }
    repeat($n, layer)'''

    EXECUTION_SCRIPT_MULTI_LASER_STANDARD = \
    '''scanner_1 = function(){
        for(p:$p[scanner_1]){
            $m.expose(p[0],$c[scanner_1])
        }
    }

    scanner_2 = function(){
        for(p:$p[scanner_2]){
            $m.expose(p[0],$c[scanner_2])
        }
    }

    scanner_3 = function(){
        for(p:$p[scanner_3]){
            $m.expose(p[0],$c[scanner_3])
        }
    }

    scanner_4 = function(){
        for(p:$p[scanner_4]){
            $m.expose(p[0],$c[scanner_4])
        }
    }

    layer = function(){
        $p[*][next;$h].map(none(),none(),group_order())
        parallel(scanner_1,scanner_2,scanner_3,scanner_4)
        $m.add_layer($g)
    }

    repeat(layer)
    '''

    EXECUTION_SCRIPTS = {
        'standard': EXECUTION_SCRIPT_STANDARD,
        'only_expose': EXECUTION_SCRIPT_ONLY_EXPOSE,
        'standard_multi': EXECUTION_SCRIPT_MULTI_LASER_STANDARD
    }

    ############
    # JOB DATA #
    ############

    async def get_jobs(self):

        jobs = await self._connection_api.get('jobs')

        return jobs

    async def get_job_id(self, job_name):

        '''
        Get the job id for a given jobname. If the job_name is unique, sets and returns the attribute job_id.
        If it is not unique or no job with the given name is found, raises a ValueError.
        In this case, start the Browser based GUI AconitySTUDIO and copy the id from the URL and manually set the attribute machine_id.

        :param job_name: jobname
        :type job_name: string

        :return: Job ID
        :rtype: string
        '''

        jobs = await self.get_jobs()

        job_id = None

        cnt = 0

        for job in jobs:

            if job['name'] == job_name:

                job_id = job['_id']['$oid']

                cnt += 1

        if cnt == 0:

            self._logger.error(f'job "{job_name}" cannot be found')

            raise ValueError(f'job "{job_name}" cannot be found')

        elif cnt > 1:

            self._logger.error(f'More than one job with the name {job_name} found! Please set the job_id attribute manually (start GUI AconitySTUDIO -> copy from URL)')

            raise ValueError(f'More than one job with the name {job_name} found! Please set the job_id attribute manually (start GUI AconitySTUDIO -> copy from URL)')

        else:

            self._logger.info(f'self.job_name: {job_name}')
            self._logger.info(f'self.job_id: {job_id}')

            return job_id

    async def create_JobHandler(self, job_id, studio_version):

        job = await self._connection_api.get(f'jobs/{job_id}')

        jobHandler = JobHandler.JobHandler(job, self._logger, studio_version)

        return jobHandler

    ##############################
    # JOB / SCRIPT API FUNCTIONS #
    ##############################

    async def start_job(self, layers, execution_script, job_id=None, channel_id='run0', parts='all', execution_script_is_a_filepath=False, studio_version=2):

        '''
        Starts a job. The init/resume script will be generated automatically from the current job.

        :param execution_script: The execution script which shall be executed.
        :type execution_script: string

        :param job_id: Id of the Job. Get it by calling get_job_id().
        :type job_id: string

        :param channel_id: 'run0'.
        :type channel_id: string

        :param layers: Specify the layers which shall be built. Must be given as list with 2 integer entries.
        :type layers: list

        :param parts: Specify the parts which shall be built. Can either be a list of integers or the string 'all'.
        :type parts: list/string

        :param execution_script_is_a_filepath: False by default. If changed to True, the parameter execution_script gets interpreted as a filepath. The execution script will then get read in from that file.
        :type execution_script_is_a_filepath: bool
        '''

        self.jobHandler = await self.create_JobHandler(job_id, studio_version)

        # #### LAYER #### #

        self.job_info['start_layer'] = layers[0]
        self.job_info['original_start_layer'] = layers[0]
        self.job_info['end_layer'] = layers[1]

        # #### INIT SCRIPT #### #

        init_script = self.jobHandler.create_init_script(layers=layers, parts=parts)

        print(f"INIT SCRIPT\n{init_script}")

        response = await self._execution_api.start_ScriptRun(init_script=init_script, execution_script=execution_script, workunit_id=job_id, channel_id=channel_id, execution_script_is_a_filepath=execution_script_is_a_filepath)

        channel, workunit_id = await self._execution_api.current_ScriptRun(response)

        if 'error' in response and 'error(s) in script. Could not execute! =>\n' in response['error']:

            self._logger.error(f'channel {channel_id} may be occupied. Try to shut it down ...')

            # #### STOP #### #

            stop_response = await self._connection_api.get(f'script/{workunit_id}/stop/{channel_id}')

            if 'success' in stop_response and stop_response['success'] == 'machine will stop ...':

                self._logger.info(f'channel {channel_id} successfully stopped')

            else:

                self._logger.warning(f'channel {channel_id} can not be stopped')

                raise ValueError(f'{response}')

        return response

    async def pause_job(self, job_id=None, channel_id='run0'):

        '''
        Pauses the running script on the given channel and workunit

        :param workunit_id: the route GET /script yields information about the current workunit_id.
        :type workunit_id: string
        :param channel: the route GET /script yields information about the current workunit_id.
        :type password: string
        '''

        self._logger.info(f'trying to pause running script')

        if job_id == 'none' or job_id == None:

            self._logger.error(f'job_id is "{job_id}"" (type{type(job_id)}). Abort!')

            raise ValueError(f'job_id is "{job_id}"" (type{type(job_id)}). Abort!')

        # #### create channel observer #### #

        number_of_checks = 1

        # if self.studio_version == 1:

        #     number_of_checks = 1

        # elif self.studio_version == 2:

        #     number_of_checks = 1

        channel_paused = asyncio.create_task(self._execution_api._wait(channel=channel_id, event='paused', number_of_checks=number_of_checks))

        # #### post the script #### #

        # give the channel_done task a chance to catch the start
        await asyncio.sleep(self._execution_api.safety_sleep)

        url = 'script/' + job_id + '/pause/' + channel_id

        try:

            result = await self._connection_api.get(url, verbose=True)

            # wait until the channel is done
            await channel_paused

            return result

        except asyncio.TimeoutError:

            self._logger.exception('Received TimeoutError. Something went wrong on the server side? Trying to wait until channel is paused ...')

            # wait until the channel is done
            await channel_paused

            return

        # TODO: SAFETY on PAUSE JOB #
        '''
        #save disc space. no more data needed
        if (await self.config_has_component('camera')):
            await self.execute(channel = 'manual',
                               script  = '$m.stop_record_sensor($s[hsCamera])')
        if (await self.config_has_component('PointCloud2PyrometerProcessSensor')):
            await self.execute(channel = 'manual',
                               script  = '$m.stop_record_sensor($s[2Pyrometer])')
        '''

        return result

    async def resume_job(self, job_id, layers=None, parts='all', workunit_id=None, channel_id='run0'):

        '''
        Resumes the running job on the given channel and workunit.

        :param init_resume_script: the init/resume script.
        :type init_resume_script: string

        :param workunit_id: the route GET /script yields information about the current workunit_id.
        :type workunit_id: string
        :param channel: the route GET /script yields information about the current workunit_id.
        :type password: string
        '''

        if self.jobHandler is None:

            self.jobHandler = await self.create_JobHandler(job_id, self.studio_version)

        try:

            if layers != None:

                self.job_info['start_layer'] = layers[0]
                self.job_info['end_layer'] = layers[1]

            else:

                self.job_info['start_layer'] = min(self.job_info['end_layer'], self.job_info['original_start_layer'] + self.job_info['AddLayerCommands'])

                layers = [self.job_info['start_layer'], self.job_info['end_layer']]

        except KeyError:

            self._logger.exception('This dictionary gets filled when start_job() is called')

            raise

        print(f'resuming job with new goal to build layers {layers}....jobinfo: {self.job_info}', flush=True)
        logging.info(f'resuming job with new goal to build layers {layers}....jobinfo: {self.job_info}')

        init_resume_script = self.jobHandler.create_init_resume_script(layers, parts)

        result = await self._execution_api.resume_ScriptRun(init_resume_script = init_resume_script, workunit_id = job_id, channel_id = channel_id, file_path_given = False)

        return result

    async def stop_job(self, job_id=None, channel='run0'):

        # TODO: Check Stop Channel

        '''
        Stops the running script on the given channel and workunit

        :param workunit_id: the route GET /script yields information about the current workunit_id.
        :type workunit_id: string
        :param channel: the route GET /script yields information about the current channel.
        :type channel: string
        '''

        if job_id == 'none' or job_id == None:

            self._logger.error(f'job_id is {job_id}. abort')

            return

        #create channel observer#create channel observer
        #channel_done = asyncio.create_task(self._channel_done(channel))

        result = await self._execution_api.stop_ScriptRun(channel, job_id, self.time_out_script_routes)

        # TODO: SAFETY on STOP JOB #

        '''
        #for safety reasons, disable laser emission
        laser_off_cmds = await self.get_lasers_off_cmds()
        for laser_off_cmd in laser_off_cmds:
            await self.execute(channel = 'manual',
                               script  = laser_off_cmd)

        #save disc space. no more data needed
        if (await self.config_has_component('camera')):
            await self.execute(channel = 'manual', script = '$m.stop_record_sensor($s[hsCamera])')
        if (await self.config_has_component('PointCloud2PyrometerProcessSensor')):
            await self.execute(channel = 'manual', script  = '$m.stop_record_sensor($s[2Pyrometer])')
        '''
        #wait until the channel is done
        #await channel_done

        return result

    async def update_job_info(self):

        '''

        '''
        session_id = await self._gateway_api.get_session_id()

        channel_id, workunit_id = await self._execution_api.current_ScriptRun()

        # #### UPDATE LAYER #### #
        result = await self._connection_api.get('script', verbose=True)

        if 'script' in result:

            script = result['script']

            if 'execScript' in script:

                self.job_info['execScript'] = result['script']['execScript']

            if 'initScript' in script:

                init_script = result['script']['initScript'].split('\n')

                self.job_info['initScript'] = result['script']['initScript']


                for a in init_script:

                    a = a.replace(" ", "")

                    if '$p.select' in a:

                        a = a.replace("$p.select(", "")
                        a = a.replace(")", "")

                        layers = a.split(',')

                        self.job_info['start_layer'] = int(layers[0])
                        self.job_info['original_start_layer'] = int(layers[0])
                        self.job_info['end_layer'] = int(layers[1])

                    if '$p.use' in a:

                        a = a.replace("$p.use(", "")
                        a = a.replace(")", "")

                        parts = a.split(',')

                        self.job_info['used_parts'] = [int(p) for p in parts]

    #################
    # JOB PARAMETER #
    #################

    async def _update_database(self, job_id, job):

        '''
        Updates the database with the job saved in the attribute job.

        :param job: The job, received by _get_job()
        :type job: AconitySTUDIO_Client.JobHandler
        '''

        try:

            url = f'jobs/{job_id}'

        except AttributeError:

            self._logger.exception('no job_id or job?')

            return

        result = await self._connection_api.put(url = url, data = job)

        return result

    async def change_global_parameter(self, job_id, param, value, check_boundaries=True):

        '''
        Change a global parameter in the locally saved job and synchronizes this change with the Server Database.

        If the parameter may only have values confined in a certain range, the new value will be changed to fit these requirements.
        (Example: The parameter must lie in the interval [1, 10]. If the attempted change is to set the value to 12 the function sets it to 10.)

        :param param: The parameter to be changed. Example: 'supply_factor'.
        :type param: string

        :param value: The new value of the parameter to be changed.
        :type value: int/float/bool

        :param check_boundaries: Ignore min and max values of a parameter.
        :type check_boundaries: bool

        Note: Calling this function does not mean that a running job
        will be paused and resumed with the updated value.
        '''

        if self.jobHandler is None:

            self.jobHandler = await self.create_JobHandler(job_id, self.studio_version)

        try:

            self.jobHandler.change_global_parameter(param, value, check_boundaries)

        except AttributeError as e:

            self._logger.exception(f'Error:{e}')

            return

        job = self.jobHandler.job

        return await self._update_database(job_id, job)

    # async def change_part_parameter(self, job_id, part_id, param, value, laser='*', check_boundaries=True):
    async def change_part_parameter(self, job_id, part_id, param, value, check_boundaries=True):

        '''
        Change a part parameter in the locally saved job and synchronizes this change with the Server Database.

        If the parameter may only have values confined in a certain range, the new value will be changed to fit these requirements.
        (Example: The parameter must lie in the interval [1, 10]. If the attempted change is to set the value to 12 the function sets it to 10.)

        Note: Calling this function does not mean that a running job
        will be paused and resumed with the updated value.

        :param part_id: The part id to be changed. For example, this number can be seen
                        in the GUI inside the jobs view -> clicking on a part -> expanding the part ->
                        a number within "[ ]" is appearing.
                        Other possibility: In the Script tab -> Init/Resume there are lines like
                        "$p.add(4,2,_modelsection_002_s1_vs)". part_id -> 4.
        :type part_id: int

        :param param: The parameter to be changed. Example: 'laser_power'.
        :type param: string

        :param value: The new value of the parameter to be changed.
        :type value: int/float/bool

        :param laser: Used to select the scanner. Either '*' (->"Scanner All") or 1, 2, 3, 4 etc ...
        :type laser: int

        :param check_boundaries: Ignore min and max values of a parameter.
        :type check_boundaries: bool
        '''

        if self.jobHandler is None:

            self.jobHandler = await self.create_JobHandler(job_id, self.studio_version)

        try:

            self.jobHandler.change_part_parameter(part_id, param, value, check_boundaries)

        except AttributeError as e:

            self._logger.exception(f'Python Client does not know about any job. Please call _get_job():{e}\n')

            return

        job = self.jobHandler.job

        return await self._update_database(job_id, job)

    #####################
    # LAYER INFORMATION #
    #####################

    async def _track_AddLayerCommand(self):

        '''websocket connection used internally to listen to the number of finished AddLayerCommands or IncreaseHeightCommands'''

        print(f"_track_AddLayerCommand")

        async with aiohttp.ClientSession(headers=self._connection_api._headers) as session:

            async with session.ws_connect(self._connection_api.topic_url) as ws:

                try:
                    task = {
                        'type': 'cmds',
                        'name': 'cmds',
                        'task': 'register'
                    }

                    await ws.send_json(task)

                    async for msg in ws:

                        if msg.type == aiohttp.WSMsgType.CLOSED:

                            print('->WS CLOSED')

                            return

                        elif msg.type == aiohttp.WSMsgType.ERROR:

                            print('->WS ERROR')

                            return

                        msg = msg.json()

                        if 'topic' in msg and msg['topic'] == 'cmds' and 'data' in msg:

                            for data in msg['data']:

                                if 'name' in data and 'value' in data and data['name'] == 'report':

                                    value = json.loads(data['value'])

                                    if 'counts' in value and 'AddLayerCommand' in value['counts']:

                                        AddLayerCommand = value['counts']['AddLayerCommand']

                                        self.job_info['AddLayerCommands'] = AddLayerCommand

                                        print(f"FOUND NEXT ADDLAYER COMMAND" , flush=True)

                                    if 'counts' in value and 'IncreaseHeightCommand' in value['counts']:

                                        IncreaseHeightCommand = value['counts']['IncreaseHeightCommand']

                                        self.job_info['AddLayerCommands'] = IncreaseHeightCommand

                                        print(f"FOUND NEXT INCREASE HEIGHT COMMAND", flush=True)

                except asyncio.CancelledError:

                    self._logger.info('received cancellation')

                    await ws.close()

    async def get_last_built_layer(self):

        '''
        When a job is running, a websockets receives information about how many addLayerCommands have been executed.
        This information is used to calculate the current layer number by adding it to the starting layer which was specified when a job was started.

        :return: current layer number during a job
        :rtype: int
        '''

        start = self.job_info['start_layer']
        addlayer = self.job_info['AddLayerCommands']

        current_layer = start + addlayer

        self._logger.info(f'current layer: start({start}) + number of addLayerCommands({addlayer}) = {current_layer}')

        return current_layer

    ############
    # COMMANDS #
    ############

    async def get_lasers_off_cmds(self, machine_id):

        try:

            url = f'machines/{machine_id}/functions'

        except AttributeError:

            self._logger.exception('Client does not have attribute machine_id set? Failure.')

            return

        functions = await self._connection_api.get(url)

        laser_off_cmds = []

        for func in functions['functions']:

            if func['call'] == '$m.off':

                off_cmds = func['components']

                for off_cmd in off_cmds:

                    if 'laser_emission' in off_cmd:

                        laser_off_cmds.append(f'$m.off({off_cmd})')

        return laser_off_cmds

    async def get_lasers(self, config_id):

        '''
        Returns a list with all lasers.

        If no config_id is set, raises an AttributeError
        '''

        try:

            url = f'configurations/{config_id}/components'

        except AttributeError:

            self._logger.exception('failing to get_lasers, attribute config_id missing?')

            raise

        lasers = set()
        components = await self._connection_api.get(url)

        #type(components)==list, type(component)==dict
        for component in components:

            if 'laser_beam_source::' in component['id']:

                try:

                    potential_number = component['id'].split('::')[1].split('::')[0]

                    if potential_number.isdigit():

                        laser_number = int(potential_number)

                except ValueError:

                    self._logger.exception(f'get lasers failed with value error at {component["id"]}')

                lasers.add(laser_number)

        self._logger.info(f'detected lasers: {lasers}')

        return lasers
