import requests
import aiohttp
import asyncio
import websockets
import decorator

import itertools, json, sys, os
from collections import deque

from pymongo import MongoClient

import time
from pytz import timezone, utc
import logging
logger = logging.getLogger(__package__)

import AconitySTUDIO_utils

class AconitySTUDIO_client:
    '''
    The AconitySTUDIO Python Client. Allows for easy automation and job
    management.

    For example usages, please consult the examples folder
    in the root directory from this repository.

    To create the client call the `classmethod` create.
    '''
    def __init__(self, login_data):
        # login data
        self.rest_url = login_data['rest_url']
        self.login_url = self.rest_url + '/login'
        self.ws_url = login_data['ws_url']
        self.topic_url = self.ws_url + '/connect'

        self.email = login_data['email']
        self.password = login_data['password']
        self.time_between_pings = 25
        self.studio_version = 1

        # ws handling
        self.processors = []
        self.msg_json = {}
        self.ws_messages = deque([])

        # book keeping
        self.history = deque([], maxlen = 15) #history of GET, POST requests
        self.job_info = {'AddLayerCommands': 0} # saves layer information for a job (start, end, number of AddLayerCommand's)
        self.pymongo_database = False
        self.start_time = time.time()
        self.blocked = {
            'manual': False,
            'manual_move': False,
            'run0': False
        }

        # entities
        self.config_id = None
        self.job_id = None
        self.session_id = None
        self.machine_id = None
        self.workunit_id = None

        # job management
        self.time_out_script_routes = 5
        self.savety_sleep = 0.15

        logger.info(f'rest url: {self.rest_url}')

    def __str__(self):
        '''
        Print out some information about the client
        '''
        myself = f'\t\t\tLast {len(self.history)} requests:\n'
        for request in self.history:
            myself += f'\t\t\t\t{request}\n'
        myself += f'\t\t\tInfo:'

        infos = ['machine_name', 'machine_id', 'config_name', 'config_id', 'job_name', 'job_id',
                 'workunit_id', 'session_id']

        for info in infos:
            information = getattr(self, info, 'Not available')
            myself += f'\n\t\t\t\t{info}: {information}'
        return myself

    #########
    # SETUP #
    #########

    @classmethod
    async def create(cls, login_data):
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

        self = AconitySTUDIO_client(login_data)
        await self._login()

        self.ws_processing_task = asyncio.create_task(self._receive_websocket_data())
        asyncio.create_task(self._ping(self.time_between_pings))
        asyncio.create_task(self._track_AddLayerCommand())


        logger.info('created client')
        return self

    async def _ping(self, time=5):
        '''
        If no ping is sent, the connection will be lost after some time.
        The user does not need to call this, as the login() function takes care of this.

        :param time: time between pings
        :type time: double
        '''
        while True:
            await asyncio.sleep(time)
            await self.get('ping', log_level='debug')

    async def _connect(self):
        '''
        Connects to the Websocket

        This function needs the Credentials created during login.

        The user does not need to call it, see the Factory method `create`.
        '''
        logger.info('creating websocket connection')
        self._conn = websockets.connect(
            self.ws_url + '/connect',
            extra_headers=self._headers
        )
        self._ws = await self._conn.__aenter__()

    async def _login(self):
        '''
        Login function to the Server

        It creates the credentials needed for login and sends them to the
        WebSocket Server.

        The user does not need to call it, see the Factory method `create`.
        '''
        headers = {'content-type': 'application/json'}
        credentials = {'email': self.email, 'password': self.password}

        response_data = await self.post(url = 'login',
                                        data= credentials,
                                        headers = headers)

        token = 'XSRF-TOKEN=' + response_data['authToken']
        self.user_id = response_data['userId']
        headers = {
            'content-type': 'application/json',
            'Cookie': token,
            'X-XSRF-TOKEN': response_data['authToken'],
            'Authorization': token
        }

        self._headers = headers
        logger.info(f'token: {token}')
        logger.info(f'user_id: {self.user_id}')

    ##############################
    # HTTP REQUESTS GET/PUT/POST #
    ##############################

    async def _http_request(self, method, url, log_level='info', headers={}, verbose=False, data=None, timeout = 300):
        '''
        Processes an http request.
        '''
        if method not in ['put','post','get']:
            raise AttributeError('Invalid http request method. Must be put/post/get')
        if 'none' in url or 'None' in url:
            raise ValueError(f'Invalid url: {url}. (contains "None")')
        if 'ping' not in url:
            logger.info(f'{method} {url}')
            self.history.append(f'{method} {url}')
        if headers == {}:
            headers = self._headers

        url = self.rest_url + '/' + url
        #####request

        if data != None:
            if type(data) == dict:
                msg = 'post request:\n\n'
                msg += f'\t\theaders:\n\n{headers}\n\n'
                for key, value in data.items():
                    msg += f'\t\t{key}:\n\n{value}\n\n'
                logger.debug(msg)
                data = json.dumps(data)
            else:
                logger.warning('deprecated input! use dictionary instead of json/string')

        if timeout == self.time_out_script_routes:
            logger.info(f'different timeout used for script routes: {self.time_out_script_routes}')
        timeout = aiohttp.ClientTimeout(total = timeout)

        async with aiohttp.ClientSession(raise_for_status = True, timeout = timeout) as session:
            try:
                #print(f'starting the {url} request')
                async with session.request(method, url, headers = headers, data = data) as resp:
                    #print(f'the {url} request answered with status {resp.status}')
                    if resp.status == 401:
                        text = await resp.text()
                        raise Exception(f'It appears The client has lost the connection (something went wrong with the ping?): {text}')
                    if resp.status == 500:
                        text = await resp.text()
                        logger.debug(f'response body 500 error:\n{text}')
                        logger.error(f'HTML return value 500, {resp.reason}. '\
                                    f'Return body has been logged with mode debug')
                    elif resp.status != 200 and resp.status != 500:
                        logger.error(f'HTML return value: {resp.status}, reason: {resp.reason}')
                        logger.error(f'{resp.request_info}')
                    #resp.raise_for_status() #does nothing if resp.status < 400
                    try:
                        result = await resp.json(content_type = None)
                    except Exception as e:
                        logging.exception(f'response is 200, but data is not in json format: {e} . I return response.text() (instead of response.json())')
                        result = await resp.text()
            except asyncio.TimeoutError:
                logger.exception('Timeout Error')
                raise

        if 'ping' not in url:
            if log_level not in ['info', 'debug', 'error', 'warning']:
                logger.warning(f'wrong log_level received :{log_level}. manually setting it to "info"')
                log_level = 'info'

            getattr(logger, log_level)(f'received:\n{json.dumps(result, indent=3)}')

        return result

    async def get(self, url, log_level='debug', logger=True, headers={}, verbose=False, timeout=300):
        '''
        The client sends a get request to the Server.
        If the response status is != 200, raises a http Exception.
        If the response status is 200, returns the body of the return json.

        :param url: request url, which will get added to self.rest_url.
            For example, to call the route http://192.168.1.123:9000/machines/functions
            the url is "machines/functions".
        :type url: string
        '''
        if 'script/' in url:
            timeout = self.time_out_script_routes

        return await self._http_request('get', url, headers=headers, log_level=log_level, timeout=timeout)

    async def put(self, url, data=None, files=None, headers={}):
        '''
        The client sends a put request to the Server.
        If the response status is 200, returns the body of the return json,
        else a http exception is raised.

        :param url: request url, will get added to self.rest_url (for details see get())
        :type url: string

        :param data: data to be posted
        :type data: dict
        '''
        return await self._http_request('put', url, data = data, headers = headers)

    async def post(self, url, data=None, files=None, headers={}, timeout=300):
        '''
        The client sends a post request to the Server.
        If the response status is 200, returns the body of the return json,
        else a http exception is raised.

        :param url: request url, will get added to self.rest_url (for details see get())
        :type url: string

        :param data: data to be posted
        :type data: dict
        '''
        if 'script/run0' in url:
            timeout = self.time_out_script_routes
        return await self._http_request(method='post', url=url, data=data, headers=headers, timeout=timeout)

    async def download_chunkwise(self, url, save_to, chunk_size = 1024):
        url = self.rest_url + '/' + url
        headers = self._headers
        try:
            async with aiohttp.ClientSession(raise_for_status = True) as session:
                async with session.get(url, headers = headers) as resp:
                    logger.info(f'saving batchdata to {save_to}')
                    with open(save_to, 'wb') as fd:
                        while True:
                            chunk = await resp.content.read(chunk_size)
                            if not chunk:
                                break
                            fd.write(chunk)
        except aiohttp.client_exceptions.ClientResponseError:
            logger.exception(f'Something went wrong with {url}. Please check if the file is corrupted in some way.')
            return None
        return save_to

    ##############################
    # JOB / SCRIPT API FUNCTIONS #
    ##############################

    async def start_job(self, layers, execution_script,
                        job_id=None, channel_id = 'run0', parts='all'):
        '''
        Starts a job. The init/resume script will be generated automatically from the current job.

        :param execution_script: The execution script which shall be executed.
        :type execution_script: string

        :param job_id: Id of the Job. Get it by calling get_job_id().
        :type job_id: string

        :param channel_id: 'run0'.
        :type channel_id: string

        :param layers: Specify the layers which shall be built. Must be given as list with 2 integer entries
        :type layers: list

        :param parts: Specify the parts which shall be built. Can either be a list of integers or the string 'all'.
        :type parts: list/string
        '''
        job = await self._get_job()

        self.job_info['start_layer'] = layers[0]
        self.job_info['end_layer'] = layers[1]

        init_script = job.create_init_script(layers = layers, parts = parts)

        response = await self.post_script(init_script = init_script,
                                        execution_script = execution_script,
                                        job_id = job_id,
                                        channel_id = channel_id)

        await self.get_workunit_and_channel_id(response)

        if 'error' in response and 'error(s) in script. Could not execute! =>\n' in response['error']:
            logger.error(f'channel {channel_id} may be occupied. Try to shut it down ...')

            stop_response = await self.get(f'script/{self.workunit_id}/stop/{channel_id}')
            if 'success' in stop_response and stop_response['success'] == 'machine will stop ...':
                logger.info(f'channel {channel_id} successfully stopped')
            else:
                logger.warning(f'channel {channel_id} can not be stopped')
                raise ValueError(f'{response}')

        return response

    async def pause_job(self, workunit_id=None, channel_id='run0'):
        '''
        Pauses the running script on the given channel and workunit

        :param workunit_id: the route GET /script yields information about the current workunit_id
        :type workunit_id: string
        :param channel: the route GET /script yields information about the current workunit_id
        :type password: string
        '''
        logger.info(f'trying to pause running script')
        workunit_id = AconitySTUDIO_utils._gather(self, logger, 'workunit_id', workunit_id)  # orignally set to _utils.gather, but it was undefined

        if workunit_id == 'none' or workunit_id == None:
            logger.error(f'workunit_id is "{workunit_id}"" (type{type(workunit_id)}). Abort!')
            raise ValueError(f'workunit_id is "{workunit_id}"" (type{type(workunit_id)}). Abort!')

        #create channel observer
        if self.studio_version == 1:
            number_of_checks = 1
        elif self.studio_version == 2:
            number_of_checks = 1
        channel_paused = asyncio.create_task(self._wait(channel=channel_id, event='paused', number_of_checks=number_of_checks))

        #post the script
        await asyncio.sleep(self.savety_sleep) # give the channel_done task a chance to catch the start

        url = 'script/' + workunit_id + '/pause/' + channel_id

        try:
            result = await self.get(url, verbose=True)
            await channel_paused # wait until the channel is done
            return result
        except asyncio.TimeoutError:
            logger.exception('Received TimeoutError. Something went wrong on the server side? Trying to wait until channel is paused ...')
            await channel_paused # wait until the channel is done
            return

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

    async def resume_job(self, layers=None, parts = 'all', workunit_id = None, channel_id = 'run0'):
        '''
        Resumes the running job on the given channel and workunit.

        :param init_resume_script: the init/resume script.
        :type init_resume_script: string

        :param workunit_id: the route GET /script yields information about the current workunit_id
        :type workunit_id: string
        :param channel: the route GET /script yields information about the current workunit_id
        :type password: string
        '''

        await self._get_job()

        try:
            if layers != None:
                self.job_info['start_layer'] = layers[0]
                self.job_info['end_layer'] = layers[1]
            else:
                self.job_info['start_layer'] += self.job_info['AddLayerCommands']
                layers = [self.job_info['start_layer'], self.job_info['end_layer']]
        except KeyError:
            logger.exception('This dictionary gets filled when start_job() is called')
            raise

        logging.info(f'resuming job with new goal to build layers {layers}....jobinfo: {self.job_info}')
        init_resume_script = self.job.create_init_resume_script(layers, parts)

        result = await self.resume_script(init_resume_script = init_resume_script,
                                          workunit_id = workunit_id,
                                          channel_id = channel_id,
                                          file_path_given = False)

        return result

    async def stop_job(self, workunit_id=None, channel='run0'):
        '''
        Stops the running script on the given channel and workunit

        :param workunit_id: the route GET /script yields information about the current workunit_id
        :type workunit_id: string
        :param channel: the route GET /script yields information about the current channel
        :type channel: string
        '''
        workunit_id = AconitySTUDIO_utils._gather(self, logger, 'workunit_id', workunit_id)
        if workunit_id == 'none' or workunit_id == None:
            logger.error(f'workunit_id is {workunit_id}. abort')
            return

        #create channel observer#create channel observer
        #channel_done = asyncio.create_task(self._channel_done(channel))

        url = 'script/' + workunit_id + '/stop/' + channel
        try:
            timeout = self.time_out_script_routes
            result = await self.get(url=url, verbose=True, timeout=timeout)
        except asyncio.TimeoutError:
            logger.exception('Timeout may have happened because a process with no longer existing workunit_id should be stopped. Stop prematurely, as no answer can be expected from the Server in this case.')
            return

        '''
        #for savety reasons, disable laser emission
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

    async def change_global_parameter(self, param, value, check_boundaries=True):
        '''
        Change a global parameter in the locally saved job and synchronizes this change with the Server Database.

        If the parameter may only have values confined in a certain range, the new value will be changed to fit these requirements.
        (Example: The parameter must lie in the interval [1, 10]. If the attempted change is to set the value to 12 the function sets it to 10.)

        :param param: The parameter to be changed. Example: 'supply_factor'
        :type param: string

        :param value: The new value of the parameter to be changed
        :type value: int/float/bool

        :param check_boundaries: Ignore min and max values of a parameter.
        :type check_boundaries: bool

        Note: Calling this function does not mean that a running job
        will be paused and resumed with the updated value.
        '''
        await self._get_job()
        try:
            self.job.change_global_parameter(param, value, check_boundaries)
        except AttributeError as e:
            logger.exception(f'Error:{e}')
            return
        return await self._update_database()

    async def change_part_parameter(self, part_id, param, value, laser='*', check_boundaries=True):
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

        :param param: The parameter to be changed. Example: 'laser_power'
        :type param: string

        :param value: The new value of the parameter to be changed
        :type value: int/float/bool

        :param laser: Used to select the scanner. Either '*' (->"Scanner All") or 1, 2, 3, 4 etc ...
        :type laser: int

        :param check_boundaries: Ignore min and max values of a parameter.
        :type check_boundaries: bool
        '''
        await self._get_job()
        try:
            self.job.change_part_parameter(part_id, param, value, laser, check_boundaries)
        except AttributeError as e:
            logger.exception(f'Python Client does not know about any job. Please call _get_job():{e}\n')
            return
        return await self._update_database()

    async def stop_channel(self, channel='manual_move'):
        '''
        Stops the running execution on the given channel.

        :param channel: Example: 'manual_move'
        :type channel: string
        '''
        url = 'stop/channel/' + channel
        return await self.get(url)

    async def execute(self, channel, script, machine_id=None):
        '''
        Sends scripts (commands) to the WebSocket Server.

        :param machine_id: Machine ID
        :type machine_id: string
        :param channel: currently only "manual" is supported
        :type channel: string
        :param script: The command(s) that the Server executes
        :type script: string
        '''

        machine_id = AconitySTUDIO_utils._gather(self, logger, 'machine_id', machine_id)

        url = 'machine/' + machine_id + '/execute/' + channel
        task = {
            'code': script,
            'partRefs': []
        }
        logger.info(f'POST {script} to channel {channel}')

        if self.studio_version == 2:
            if self.blocked[channel]:
                logger.error(f'Can"t execute new command on channel {channel}. It is already running')
                return

            #create channel observer
            channel_done = asyncio.create_task(self._wait(channel=channel, event='halted'))
            await asyncio.sleep(self.savety_sleep) # give the channel_done task a chance to catch the start

        #post the script
        response = await self.post(url, data=task)

        if self.studio_version == 2:
            #wait until the channel is done
            await channel_done

        #logger.info(f'execution response: {response}, {response.ok}, {response.text}')
        return response

    async def post_script(self, init_script='', execution_script='',
                          job_id=None, channel_id = 'run0',
                          file_path_init_script = None, file_path_execution_script = None):
        '''
        The client posts execution and init/resume scripts to the Server.

        If the response status is != 200, raises Exception.
        Returns the body of the return json.

        It is recommended that the API function `start_job` is used instead of this function, because `start_job` generates the init_script automatically.

        :param data: data to be posted
        :type data: dict

        :param job_id: job_id of the job
        :type job_id: string

        :param channel_id: channel_id of the job, for instance "run0".
        :type channel_id: string

        :param execution_script: execution script
        :type execution_script: string

        :param init_script: init script
        :type init_script: string

        :param file_path_execution_script: If != None, gets interpreted as a filepath. The file will be read and any string given to parameter execution_script is ignored.
        :param file_path_execution_script: string

        :param file_path_init_script: If != None, gets interpreted as a filepath. The file will be read and any string given to parameter init_script is ignored.
        :param file_path_init_script: string

        :return: Returns the body of the return json from the request.
        :rtype: dict
        '''

        job_id = AconitySTUDIO_utils._gather(self, logger, 'job_id', job_id)

        if file_path_init_script != None:
            try:
                with open(file_path_init_script) as init_file:
                    init_script = init_file.read()
            except FileNotFoundError:
                logger.exception(f'POST script failed, init script file not found. Abort.')
                raise

        if file_path_execution_script != None:
            try:
                with open(file_path_execution_script) as exec_file:
                    execution_script = exec_file.read()
            except FileNotFoundError:
                logger.exception(f'POST script failed, execution script file not found. Abort.')
                raise

        if init_script == '':
            raise ValueError('please provide init script. init_script == "", error.')
        if execution_script == '':
            raise ValueError('please provide execution script. execution_script == "", error.')
        #self._headers['Accept'] = 'application/json, text/plain, */*'
        #self._headers['Accept-Encoding'] = 'gzip, deflate, br'
        #self._headers['content-type'] ='application/json, multipart/form-data'

        logger.debug(f'POST init script:\n{init_script}\n')
        logger.debug(f'POST execution script:\n{execution_script}\n')

        url = 'script/' + channel_id
        data = {
            'workunitId': job_id,
            'typ': 'job_',
            'exec': execution_script,
            'init': init_script
        }

        response = await self.post(url = url, data=data)


        return response

    async def resume_script(self, init_resume_script, workunit_id = None, channel_id='run0', file_path_given = False):
        '''
        Resumes the running script on the given channel and workunit.

        :param init_resume_script: the init/resume script.
        :type init_resume_script: string


        :param workunit_id: the route GET /script yields information about the current workunit_id. If workunit_id = None, the client attempts to use its own attribute workunit_id. If that fails, raises ValueError.
        :type workunit_id: string
        :param channel: the route GET /script yields information about the current workunit_id
        :type password: string
        '''

        workunit_id = AconitySTUDIO_utils._gather(self, logger, 'workunit_id', workunit_id)

        if file_path_given:
            with open(init_resume_script) as initfile:
                init_resume_script = initfile.read()

        logger.debug(f'trying to resume the init_resume_script:\n {init_resume_script}')
        url = 'script/' + workunit_id + '/resume/' + channel_id
        data = {'init' : init_resume_script}
        response = await self.post(url, data=data)

        success_confirmation = 'execution will resume ...'
        try:
            if (response['success'] == success_confirmation)\
               and (response['resumed'] == True or response['resumed'] == 'true'):

                self.workunit_id = response['execution']
                logger.info(f'new self.workunit_id: {self.workunit_id}')
            else:
                print('execution not resumed ?')
                print(response)
                raise Exception
        except Exception as e:
            logger.error(f'resuming script failed: {e}\n{response}')
            raise

        logger.info(f'{response}')

        return response

    async def restart_config(self):
        '''
        The attribute "config_id" must be set.
        Restarts the config with that id.

        If no ``config_id`` is set, raises a ValueError.
        '''
        if self.config_id != None:
            for cmd in ('stop', 'init', 'start'):
                url = f'configurations/{self.config_id}/{cmd}'
                try:
                    t1 = time.time()
                    await self.get(url)
                    logger.info(f'{cmd} {self.config_name} took {time.time()-t1} s')
                    state = (await self.get(f'configurations/{self.config_id}'))['state']
                    logger.info(f'config {self.config_name} is in state {state}')
                except:
                    logger.error(f'problem with {url}, abort restarting config')
                    break
        else:
            logger.error('could not restart config, no config_id known')
            raise ValueError('could not restart config, no config_id known')

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
        logger.info(f'current layer: start({start}) + number of addLayerCommands({addlayer}) = {current_layer}')
        return current_layer

    async def _update_database(self):
        '''
        Updates the database with the job saved in the attribute job.

        :param job: The job, received by _get_job()
        :type job: AconitySTUDIO_Client.JobHandler
        '''
        try:
            url = f'jobs/{self.job_id}'
            job = self.job.job
        except AttributeError:
            logger.exception('no job_id or job?')
            return

        result = await self.put(url = url,
                                data = job)
        return result

    def _channel_paused(self, msg, channel):
        '''
        Pauses a channel.
        '''
        if msg.type == aiohttp.WSMsgType.CLOSED:
            logging.warning('->WS CLOSED')
            return
        elif msg.type == aiohttp.WSMsgType.ERROR:
            logging.warning('->WS ERROR')
            return
        msg = msg.json()

        try:
            if msg['topic'] == 'run' and \
                msg['data'][0]['msg'] == 'paused' and \
                msg['data'][0]['channel'] == channel:

                logger.info(f'a command paused on channel {channel}!')
                self.blocked[channel] = True
                return True
        except KeyError:
            return False
        except:
            logger.exception(f'\nunexpected exception in msg:\n{msg}------\n')
            raise

    def _channel_resumed(self, msg, channel):
        '''
        Resumes a channel.
        '''
        if msg.type == aiohttp.WSMsgType.CLOSED:
            logging.warning('->WS CLOSED')
            return
        elif msg.type == aiohttp.WSMsgType.ERROR:
            logging.warning('->WS ERROR')
            return
        msg = msg.json()
        try:
            print
            if msg['topic'] == 'run' and \
                msg['data'][0]['msg'] == 'resumed' and \
                msg['data'][0]['channel'] == channel:

                logger.info(f'a command resumed on channel {channel}!')
                self.blocked[channel] = True
                return True
        except KeyError:
            return False
        except:
            logger.exception('\nunexpected exception in msg:\n{msg}------\n')
            raise

    def _channel_halted(self, msg, channel):
        '''
        Halts a channel.
        '''
        if msg.type == aiohttp.WSMsgType.CLOSED:
            logging.warning('->WS CLOSED')
            return
        elif msg.type == aiohttp.WSMsgType.ERROR:
            logging.warning('->WS ERROR')
            return
        msg = msg.json()
        try:
            if msg['topic'] == 'run' and \
                msg['data'][0]['channel'] == channel:
                    _msg = msg['data'][0]['msg']
                    if _msg == 'stopped':
                        logger.info(f'a command stopped on channel {channel}.')
                        self.blocked[channel] = False
                        return True
                    if _msg == 'finished':
                        logger.info(f'a command finished on channel {channel}.')
                        self.blocked[channel] = False
                        return True
                    if _msg == 'paused':
                        logger.info(f'a command paused on channel {channel}.')
                        self.blocked[channel] = False
                        return True
        except KeyError:
            return False
        except Exception:
            logger.exception('\nunexpected exception in msg:\n{msg}------\n')
            raise

    #############
    # WEBSOCKET #
    #############
    async def subscribe_report(self, name):
        '''
        Subscribes to reports via the WebServer.

        To get information about the reports use the route configurations/{client.config_id}/topics).

        :param name: name of report, example reports: 'state', 'task'.
        :type name: string
        '''
        task = {
            'type': name,
            'name': name,
            'task': 'register'
        }
        while True:
            try:
                await self._ws.send_json(task)
                break
            except AttributeError:
                logger.debug('websocket connection not (yet) established, cant subscribe to report')
                await asyncio.sleep(0.01)

        logger.info(f'Subscription to report {name} sent!')

    async def subscribe_topic(self, name):
        '''
        Subscribes to reports via the WebServer.

        To get information about the topics use the route configurations/{client.config_id}/topics).

        :param name: name of topic. Examples are 'State', 'Sensor','cmds' and 'Positioning'.

        :type name: string
        '''
        task = {
            'type': 'machine',
            'name': name,
            'task': 'register'
        }
        while True:
            try:
                await self._ws.send_json(task)
                break
            except AttributeError:
                logger.debug('websocket connection not (yet) established, cant subscribe to topic')
                await asyncio.sleep(0.01)

        logger.info(f'Subscription to topic {name} sent!')

    async def _receive_websocket_data(self):
        '''Process data received from the websocket'''
        ws_url = self.ws_url + '/connect'
        async with aiohttp.ClientSession(headers=self._headers) as session:
            async with session.ws_connect(ws_url) as self._ws:
                async for msg in self._ws:
                    if msg.type == aiohttp.WSMsgType.CLOSED:
                        logging.warning('->WS CLOSED')
                        return
                    elif msg.type == aiohttp.WSMsgType.ERROR:
                        logging.warning('->WS ERROR')
                        return

                    msg = msg.json()

                    for processor in self.processors:
                        await asyncio.sleep(0)
                        #print(f'\nCLIENT:starting processor {processor}')
                        try:
                            processor(self, msg)
                        except Exception:
                            logger.exception(f'processing ({processor}) ws msg raised an exception.\n')
                        # loop = asyncio.get_running_loop()
                        # await loop.run_in_executor(None, processor, msg_new)


                    if self.pymongo_database: #call client.enable_pymongo_database to activate this feature
                        msg['_timestamp_db'] = time.time()
                        post_id = self._db.insert_one(msg).inserted_id
                        if self.keep_last > 0:
                            delete_time = time.time() - self.keep_last
                            self._db.remove({'_timestamp_db':{'$lt': delete_time}})

    async def _track_AddLayerCommand(self):
        '''websocket connection used internally to listen to the number of finished AddLayerCommands'''
        ws_url = self.ws_url + '/connect'

        async with aiohttp.ClientSession(headers=self._headers) as session:
            async with session.ws_connect(ws_url) as ws:
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
                except asyncio.CancelledError:
                    logger.info('received cancellation')
                    await ws.close()

    async def _wait(self, channel, event, number_of_checks = 1):
        '''websocket connection used internally to listen on the run report to see when a channel finished its work'''
        ws_url = self.ws_url + '/connect'
        #print(f'WS: start observing {channel}')
        async with aiohttp.ClientSession(headers=self._headers) as session:
            #print(f'WS: created client session {channel}')
            async with session.ws_connect(ws_url) as ws:
                #print(f'WS: created ws session {channel}')
                task = {
                    'type': 'run',
                    'name': 'run',
                    'task': 'register'
                }
                await ws.send_json(task)
                #print(f'WS: created run report {channel}')
                #print('->checking if channel starts')
                if event == 'halted':
                    async for msg in ws:
                        if self._channel_resumed(msg, channel):
                            break
                    #print(f'WS: channel resumed {channel}')
                    #print('->checking if channel halted')
                    async for msg in ws:
                        if self._channel_halted(msg, channel):
                            break
                    #print(f'WS: channel halted {channel}')
                    #print('-> apparently channel halted')
                elif event == 'paused':
                    for check in range(1, number_of_checks + 1):
                        logger.info(f'pause check #{check}')
                        async for msg in ws:
                            if self._channel_paused(msg, channel):
                                break
                #await ws.close() # hopefully never neccessary

    #######################################
    # MACHINE INFORMATION AND SERVER DATA #
    #######################################
    async def get_session_id(self, n = -1):
        '''
        Get all session ids. If successfull, saves the session ID in self.session_id

        :param n: With the default parameter `n=-1`, the most recent session id gets saved to self.session_id (second last session, use n=-2 etc).
        :type n: int

        :return: Session ID
        :rtype: string
        '''
        self.session_ids = await self.get('sessions') #all recorded sessions
        #print('ids...')
        #for i, id in enumerate(self.session_ids):
        #    print(i, id)
        self.session_id = self.session_ids[n]  #take most recent one if n=-1
        logger.info(f'self.session_id: {self.session_id}')
        return self.session_id

    async def get_machine_id(self, machine_name):
        '''
        Get the machine_id from a given Machine Name.

        If no or multiple machines with the given name are given, raises ValueErrors.
        In this case, start the Browser based GUI AconitySTUDIO and copy the id from the URL and manually set the attribute machine_id.

        If successfull, returns the machine_id and saves it to self.machine_id.

        :param machine_name: Name of Machine
        :type machine_name: string

        :return: Machine ID
        :rtype: string
        '''
        result = await self.get('machines')

        cnt = 0
        for machine in result:
            if machine['name'] == machine_name: #found it!
                cnt += 1
                self.machine_name = machine['name']
                self.machine_id = machine['_id']['$oid']

        if cnt == 0:
            logger.error(f'machine "{machine_name}" cannot be found')
        elif cnt > 1:
            logger.error('More than one machine with the same name found! Please set the machine_id attribute manually. (start GUI AconitySTUDIO -> copy from URL)')
            raise ValueError('More than one machine with the same name found! Please set the machine_id attribute manually. (start GUI AconitySTUDIO -> copy from URL)')
        else:
            logger.info(f'self.machine_id: {self.machine_id}')
            logger.info(f'self.machine_name: {self.machine_name}')
            return self.machine_id

    async def get_workunit_and_channel_id(self, result=None):
        '''
        Retrieves workunit_id and channel_id. If successfull,
        saves them in self.channel_id and self.workunit_id and returns them

        If not successfull, raises a ValueError.

        :return: workunit_id, channel_id
        :rtype: tuple
        '''
        logger.info(f'trying to gather workunit_id from {result}')

        if result == None:
            result = await self.get('script')

        if result == {'success': 'script received', 'script': None}:
            logger.error(f'could not retrieve workunit/channel id. '\
                          f'Result of the last request: {str(result)}). '\
                          f'Please post a script first.')

        # There can be different formats of the result.
        # Go through them one by one, return the first one that works

        try:
            self.workunit_id = result['script']['execution']['workUnit']['workUnitId']
            self.channel_id = result['script']['execution']['channel']
            logger.info(f'successfully gathered workunit_id and channel_id')
            return self.workunit_id, self.channel_id
        except:
            logger.info(f'get script type information for wid + channel id failed')

        try:
            self.workunit_id = result['execution']['workUnit']['workUnitId']
            self.channel_id = result['execution']['channel']
            logger.info(f'successfully gathered workunit_id and channel_id')
            return self.workunit_id, self.channel_id
        except:
            logger.info(f'post script result type information for wid + channel id failed')

        try:
            self.workunit_id = result['execution']
            self.channel_id = 'run0'
            logger.info(f'successfully gathered workunit_id and channel_id (manually setting channel_id to "run0", as this could not be gathered')
            return self.workunit_id, self.channel_id
        except:
            logger.info(f'studio version 1 type information for wid+channel failed')

        logger.error(f'the workunit could not be gathered from:\n{json.dumps(result, indent=3)}')

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
        jobs = await self.get('jobs')
        cnt = 0
        for job in jobs:
            if job['name'] == job_name:
                self.job_id = job['_id']['$oid']
                self.job_name = job_name
                cnt += 1
        if cnt == 0:
            logger.error(f'job "{job_name}" cannot be found')
            raise ValueError(f'job "{job_name}" cannot be found')
        elif cnt > 1:
            logger.error(f'More than one job with the name {job_name} found! Please set the job_id attribute manually (start GUI AconitySTUDIO -> copy from URL)')
            raise ValueError(f'More than one job with the name {job_name} found! Please set the job_id attribute manually (start GUI AconitySTUDIO -> copy from URL)')
        else:
            logger.info(f'self.job_name: {self.job_name}')
            logger.info(f'self.job_id: {self.job_id}')
            return self.job_id

    async def _get_job(self, job_id=None):
        ''' Returns the `JobHandler` object for the current job.'''
        job_id = AconitySTUDIO_utils._gather(self, logger, 'job_id', job_id)
        job = await self.get(f'jobs/{job_id}')
        self.job = AconitySTUDIO_utils.JobHandler(job, logger, self.studio_version)
        return self.job

    async def get_config_id(self, config_name):
        '''
        Returns the config_id of the config with the given name.

        If it is not unique or no config with the given name is found, raises a ValueError.
        In this case, start the Browser based GUI AconitySTUDIO and copy the id from the URL and manually set the attribute config_id.

        Saves the config_id into self.config_id.
        Saves the name of the operational config into self.config_name.

        :return: Config ID
        :rtype: string
        '''
        configs = await self.get('configurations')

        cnt = 0
        for config in configs:
            if config['name'] != config_name:
                continue
            cnt += 1
            if self.studio_version == 2:
                self.config_operational = config['state'] == 'operational'
            elif self.studio_version == 1:
                self.config_operational = config['state'] == 'started'
            self.config_name = config['name']
            self.config_id = config['_id']['$oid']
            config_state = config['state']

        if cnt == 0:
            logger.error(f'config "{config_name}" cannot be found')
            raise ValueError(f'config "{config_name}" cannot be found')
        elif cnt > 1:
            logger.error(f'More than one config with the name {config_name} found! Please set the config_id attribute manually (start GUI AconitySTUDIO -> copy from URL)')
            raise ValueError(f'More than one config with the name {config_name} found! Please set the config_id attribute manually (start GUI AconitySTUDIO -> copy from URL')
        else:
            logger.info(f'self.config_name: {self.config_name}\t({config_state})')
            logger.info(f'self.config_id: {self.config_id}')
            if not self.config_operational:
                logger.warning(f'config {config_name} exists, but is not operational')
                print(json.dumps(config,indent=3))
            return self.config_id

    async def config_has_component(self, component, config_id = None):
        '''
        Checks if a config has a certain component.

        :param component: The component to be checked.
        :type component: string

        :param config_id: Config Id. If `config_id == None`, the client uses its own attribute config_id.
        :type config_id: string

        :param config_name: Config Name.
        :type config_name: string

        :rtype: bool
        '''
        config_id = AconitySTUDIO_utils._gather(self, logger, 'config_id', config_id)

        url = f'configurations/{config_id}/components'

        if not (await self.config_exists(config_id=config_id)):
            logger.warning(f'no config with the config_id {config_id} found!')
            raise ValueError(f'no config with the config_id {config_id} found!')

        components = await self.get(url)
        for comp in components:
            if comp['id'] == component:
                logger.info(f'config has component {component}')
                return True
        logger.info(f'config does not have component {component}')
        return False

    async def config_exists(self, config_name=None, config_id=None):
        '''
        Checks if a config exists.

        One can *either* use the config_name or the config_id as a search parameter (XOR).
        If this is not done, raises a ValueError.

        :param config_name: Name of the config
        :type config_name: str

        :param config_id: Id of the config
        :type config_id: str

        :rtype: bool
        '''
        if (config_name == None and config_id == None) or \
           (config_name != None and config_id != None):
            logger.warning('please provide a config_name XOR config_id')
            raise ValueError('please provide a config_name XOR config_id')

        configs = await self.get('configurations')
        for config in configs:
            if config['name'] == config_name:
                logger.info(f'configuration {config_name} exists')
                return True
            if config['_id']['$oid'] == config_id:
                logger.info(f'configuration with config id {config_id} exists')
                return True
        logging.warning(f'no configuration with the given name/config_id could be found!')
        return False

    async def config_state(self, config_id=None):
        '''
        Returns the current state of the config

        :param config_id: Id of the config. If none is given, the client uses its own attribute `config_id`.
        :type config_id: str

        :return: 'operational', 'inactive', or 'initialized'
        :rtype: string
        '''
        config_id = AconitySTUDIO_utils._gather(self, logger, 'config_id', config_id)

        configurations = await self.get('configurations')

        for config in configurations:
            if config['_id']['$oid'] == self.config_id: #use clients own attribute self.config_id
                return config['state']

        raise ValueError('cant check state of config. config with config_id {config_id} can not be found!')

    async def get_lasers_off_cmds(self):
        ''' Returns the command to turn the laser off.'''
        try:
            url = f'machines/{self.machine_id}/functions'
        except AttributeError:
            logger.exception('Client does not have attribute machine_id set? Failure.')
            return

        functions = await self.get(url)

        laser_off_cmds = []
        for func in functions['functions']:
            if func['call'] == '$m.off':
                off_cmds = func['components']
                for off_cmd in off_cmds:
                    if 'laser_emission' in off_cmd:
                        laser_off_cmds.append(f'$m.off({off_cmd})')
        return laser_off_cmds

    async def get_lasers(self):
        '''
        Returns a list with all lasers.

        If no config_id is set, raises an AttributeError
        '''
        try:
            url = f'configurations/{self.config_id}/components'
        except AttributeError:
            logger.exception('failing to get_lasers, attribute config_id missing?')
            raise

        self.lasers = set()
        components = await self.get(url)

        for component in components: #type(components)==list, type(component)==dict
            if 'laser_beam_source::' in component['id']:
                try:
                    potential_number = component['id'].split('::')[1].split('::')[0]
                    if potential_number.isdigit():
                        laser_number = int(potential_number)
                except ValueError:
                    logger.exception(f'get lasers failed with value error at {component["id"]}')
                self.lasers.add(laser_number)
        logger.info(f'detected lasers: {self.lasers}')
        return self.lasers


    ################################
    # PYTHON CLIENT'S OWN DATABASE #
    ################################

    def enable_pymongo_database(self, name='database_test', keep_last = 120):
        '''
        Setup for the Mongodatabase

        :param mongodatabase: name of the database
        :type mongodatabase: string

        :param keep_last: If larger that zero, automatically delete entries older than keep_last seconds
        :type keep_last: float
        '''
        try:
            mongoclient = MongoClient()
            mongo_db = getattr(mongoclient, name)
            self._db = mongo_db.posts
        except Exception:
            logger.exception('Error while connecting to PyMongoDB. Possibly check if MongoDB Community Edition is installed and running?')
            return

        self.keep_last = keep_last
        self.pymongo_database = True
        logger.info(f'connected to mongo database {name}')

    async def save_data_to_pymongo_db(self):
        '''
        Continually saves the output of the WebSocket Server
        by saving it into a Mongo database
        Call enable_pymongo_database() before calling this function
        '''

        if self.pymongo_database == False:
            logger.error('No database configured. Call enable_pymongo_database')
            return
        while True:
            msg = await self._ws.recv()
            msg = AconitySTUDIO_utils.fix_ws_msg(msg)
            msg_json = json.loads(msg)
            logger.info(f'received data from websocket:'\
                         f'{str(msg_json)[:30]}...')
            msg_json['_timestamp_db'] = time.time()
            post_id = self._db.insert_one(msg_json).inserted_id
            if self.keep_last > 0:
                delete_time = time.time() - self.keep_last
                self._db.remove({'_timestamp_db':{'$lt': delete_time}})
