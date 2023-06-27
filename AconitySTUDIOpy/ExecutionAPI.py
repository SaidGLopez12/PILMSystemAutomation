import json

import asyncio
import aiohttp

import logging

class ExecutionAPI:

    '''
    The AconitySTUDIO Python Client. Allows for easy automation and job
    management.

    For example usages, please consult the examples folder
    in the root directory from this repository.

    To create the client call the `classmethod` create.
    '''

    def __init__(self, connection_api):

        # #### LOGGING #### #

        self._logger = logging.getLogger("AconitySTUDIO Execution API")

        # #### CONNECTION API #### #

        self._connection_api = connection_api

        # #### CHANNEL STATE #### #

        self.blocked = {
            'manual': False,
            'manual_move': False,
            'manual_switch': False,
            'manual_gas': False,
            'run0': False,
            'run0_0': False,
            'run0_1': False,
            'run0_2': False,
            'run0_3': False
        }

        self.resumed = {}
        self.paused = {}
        self.finished  = {}
        self.stopped  = {}

        self.safety_sleep = 0.15

    #############
    # EXECUTION #
    #############

    async def stop_channel(self, channel='manual_move'):

        '''
        Stops the running execution on the given channel.

        :param channel: Example: 'manual_move'.
        :type channel: string
        '''

        # #### GET #### #

        url = f"stop/channel/{channel}"

        return await self._connection_api.get(url)

    async def execute_Script(self, machine_id, channel, script, wait=True):

        '''
        Sends scripts (commands) to the WebSocket Server.

        :param machine_id: Machine ID.
        :type machine_id: string
        :param channel: Currently only "manual" is supported.
        :type channel: string
        :param script: The command(s) that the Server executes.
        :type script: string
        '''

        if machine_id == None:

            raise ValueError('please provide a valid machine_id.')

        # #### CHECK BLOCKED CHANNEL #### #

        if wait == True:

            if self.blocked[channel]:

                self._logger.error(f'Can"t execute new command on channel {channel}. It is already running')

                return False

            # create channel observer #
            channel_done = asyncio.create_task(self._wait(channel=channel, event='halted'))

            # give the channel_done task a chance to catch the start before we execute the script #
            await asyncio.sleep(self.safety_sleep)

        # #### START TASK #### #

        started = await self._start_task(machine_id, channel, script)

        if wait == True:

            # wait until the channel is done #
            print(f"Wait until done")

            await channel_done

            if started and self.finished[channel] == True:

                return True

            return False


        # self._logger.info(f'execution response: {response}, {response.ok}, {response.text}')

        return started

    async def stop_ScriptRun(self, channel, workunit_id, timeout):

        url = f"script/{workunit_id}/stop/{channel}"

        try:

            result = await self._connection_api.get(url=url, verbose=True, timeout=timeout)

            return result

        except asyncio.TimeoutError:

            self._logger.exception('Timeout may have happened because a process with no longer existing workunit_id should be stopped. Stop prematurely, as no answer can be expected from the Server in this case.')

            return

    async def current_ScriptRun(self, result=None):

        '''
        Retrieves workunit_id and channel_id. If successfull,
        saves them in self.channel_id and self.workunit_id and returns them

        If not successfull, raises a ValueError.

        :return: workunit_id, channel_id
        :rtype: tuple
        '''

        self._logger.info(f'trying to gather workunit_id from {result}')

        channel_id = None
        workunit_id = None

        if result == None:

            result = await self._connection_api.get('script')

        if result == {'success': 'script received', 'script': None}:

            self._logger.error(f'could not retrieve workunit/channel id. Result of the last request: {str(result)}). Please post a script first.')

        # TODO: Why multiple formats? #

        # There can be different formats of the result.
        # Go through them one by one, return the first one that works

        # #### FORMAT 1 #### #

        try:

            channel_id = result['script']['execution']['channel']
            workunit_id = result['script']['execution']['workUnit']['workUnitId']

            self._logger.info(f'successfully gathered workunit_id and channel_id')

            return channel_id, workunit_id

        except:

            self._logger.debug(f'get script type information for wid + channel id failed')

        # #### FORMAT 2 #### #

        try:

            channel_id = result['execution']['channel']
            workunit_id = result['execution']['workUnit']['workUnitId']

            self._logger.info(f'successfully gathered workunit_id and channel_id')

            return channel_id, workunit_id

        except:

            self._logger.debug(f'post script result type information for wid + channel id failed')

        # #### FORMAT 3 #### #

        try:

            channel_id = 'run0'
            workunit_id = result['execution']

            self._logger.info(f'successfully gathered workunit_id and channel_id (manually setting channel_id to "run0", as this could not be gathered)')

            return channel_id, workunit_id

        except:

            self._logger.debug(f'studio version 1 type information for wid+channel failed')

        self._logger.error(f'the workunit could not be gathered from:\n{json.dumps(result, indent=3)}')

    async def start_ScriptRun(self, init_script='', execution_script='', workunit_id=None, channel_id='run0', init_script_is_a_filepath=False, execution_script_is_a_filepath=False):

        # TODO: Change to execute_script_run
        '''
        The client posts execution and init/resume scripts to the Server.

        If the response status is != 200, raises Exception.
        Returns the body of the return json.

        It is recommended that the API function `start_job` is used instead of this function, because `start_job` generates the init_script automatically.

        :param data: Data to be posted.
        :type data: dict

        :param workunit_id: id of the workunit.
        :type workunit_id: string

        :param channel_id: channel_id of the job, for instance "run0".
        :type channel_id: string

        :param execution_script: execution script.
        :type execution_script: string

        :param init_script: init script.
        :type init_script: string

        :param execution_script_is_a_filepath: False by default. If changed to True, the parameter execution_script gets interpreted as a filepath. The execution script will then get read in from that file.
        :param execution_script_is_a_filepath: bool

        :param init_script_is_a_filepath: False by default. If changed to True, the parameter init_script gets interpreted as a filepath. The init script will then get read in from that file.
        :param init_script_is_a_filepath: bool

        :return: Returns the body of the return json from the request.
        :rtype: dict
        '''

        # #### CHECK WORK UNIT ID #### #

        if workunit_id == None:

            raise ValueError('please provide a valid workunit_id.')


        # ######## CHECK SCRIPTS ######## #


        if not isinstance(init_script_is_a_filepath, bool) or not isinstance(execution_script_is_a_filepath, bool):

            self._logger.error(f"execution_script_is_a_filepath and init_script_is_a_filepath must be of type bool.")

            raise ValueError(f"execution_script_is_a_filepath and init_script_is_a_filepath must be of type bool.")

        # #### INIT SCRIPT #### #

        if init_script_is_a_filepath:

            try:

                with open(init_script) as init_file:

                    init_script = init_file.read()

            except FileNotFoundError:

                self._logger.exception(f'POST script failed, init script file not found. Abort.')

                raise

        if init_script == '':

            self._logger.error('please provide init script. init_script == "", error.')

            raise ValueError('please provide init script. init_script == "", error.')

        # #### EXECUTION SCRIPT #### #

        if execution_script_is_a_filepath:

            try:

                with open(execution_script) as exec_file:

                    execution_script = exec_file.read()

            except FileNotFoundError:

                self._logger.exception(f'POST script failed, execution script file not found. Abort.')

                raise

        if execution_script == '':

            self._logger.error('please provide execution script. execution_script == "", error.')

            raise ValueError('please provide execution script. execution_script == "", error.')

        # self._headers['Accept'] = 'application/json, text/plain, */*'
        # self._headers['Accept-Encoding'] = 'gzip, deflate, br'
        # self._headers['content-type'] ='application/json, multipart/form-data'

        self._logger.debug(f'POST init script:\n{init_script}\n')
        self._logger.debug(f'POST execution script:\n{execution_script}\n')

        # #### MSG #### #

        data = {
            'workunitId': workunit_id,
            'typ': 'job_',
            'exec': execution_script,
            'init': init_script
        }

        # #### POST #### #

        url = 'script/' + channel_id

        response = await self._connection_api.post(url = url, data=data, timeout=300)

        return response

    async def resume_ScriptRun(self, init_resume_script, workunit_id=None, channel_id='run0', file_path_given=False):

        '''
        Resumes the running script on the given channel and workunit.

        :param init_resume_script: the init/resume script.
        :type init_resume_script: string


        :param workunit_id: the route GET /script yields information about the current workunit_id. If workunit_id = None, the client attempts to use its own attribute workunit_id. If that fails, raises ValueError.
        :type workunit_id: string
        :param channel: the route GET /script yields information about the current workunit_id
        :type password: string
        '''

        # #### CHECK WORK UNIT ID #### #

        if workunit_id == None:

            raise ValueError('please provide a valid workunit_id.')

        if file_path_given:

            with open(init_resume_script) as initfile:

                init_resume_script = initfile.read()

        self._logger.debug(f'trying to resume the init_resume_script:\n {init_resume_script}')

        # #### MSG #### #

        data = {
            'init' : init_resume_script
        }

        # #### POST #### #

        url = 'script/' + workunit_id + '/resume/' + channel_id

        response = await self._connection_api.post(url, data=data, timeout=300)

        success_confirmation = 'execution will resume ...'

        try:

            if (response['success'] == success_confirmation) and (response['resumed'] == True or response['resumed'] == 'true'):

                self.workunit_id = response['execution']

                self._logger.info(f'new self.workunit_id: {self.workunit_id}')

            else:

                print('execution not resumed ?')

                print(response)

                raise Exception

        except Exception as e:

            self._logger.error(f'resuming script failed: {e}\n{response}')

            raise

        self._logger.info(f'{response}')

        return response

    ###################################################################################

     # TODO REMOVE

    def wait_test(event):

        print(event)



    async def _wait(self, channel, event, number_of_checks = 1):

        '''websocket connection used internally to listen on the run report to see when a channel finished its work'''

        async with aiohttp.ClientSession(headers=self._connection_api._headers) as session:

            async with session.ws_connect(self._connection_api.topic_url) as ws:

                # #### REGISTER #### #

                task = {
                    'type': 'run',
                    'name': 'run',
                    'task': 'register'
                }

                await ws.send_json(task)

                #print(f'WS: created run report {channel}')
                #print('->checking if channel starts')

                if event == 'started':

                    # #### STARTED #### #

                    async for msg in ws:

                        if self._channel_started(msg, channel):

                            break

                    print(f'WS: channel started {channel}')
                    #print('->checking if channel halted')

                    async for msg in ws:

                        if self._channel_halted(msg, channel):

                            break

                    print(f'WS: channel halted {channel}')
                    #print('-> apparently channel halted')

                if event == 'halted':

                    # #### HALTED #### #

                    async for msg in ws:

                        if self._channel_resumed(msg, channel):

                            print(f'WS: channel resumed {channel}')

                            break

                    print(f'WS: WAIT FOR HALTED {channel}')
                    #print('->checking if channel halted')

                    async for msg in ws:

                        if self._channel_halted(msg, channel):

                            break

                    print(f'WS: channel halted {channel}')
                    #print('-> apparently channel halted')

                elif event == 'paused':

                    # #### PAUSED #### #

                    for check in range(1, number_of_checks + 1):

                        self._logger.info(f'pause check #{check}')

                        async for msg in ws:

                            if self._channel_paused(msg, channel):

                                break

                #await ws.close() # hopefully never neccessary

    async def execute_until(self, event, fn, channel='run0', number_of_checks = 1):

        '''websocket connection used internally to listen on the run report to see when a channel finished its work'''

        print(f'WS: start observing {channel}', flush=True)

        async with aiohttp.ClientSession(headers=self._connection_api._headers) as session:

            #print(f'WS: created client session {channel}')

            async with session.ws_connect(self._connection_api.topic_url) as ws:

                #print(f'WS: created ws session {channel}')

                task = {
                    'type': 'run',
                    'name': 'run',
                    'task': 'register'
                }

                await ws.send_json(task)

                print(f'WS: created run report {channel}', flush=True)
                #print('->checking if channel starts')

                if event == 'started':

                    # #### STARTED #### #

                    async for msg in ws:

                        if self._channel_started(msg, channel):

                            break

                        else:

                            fn(msg, channel)

                    print(f'WS: channel started {channel}', flush=True)
                    #print('->checking if channel halted')

                if event == 'halted':

                    print(f"EXECUTE UNTIL HALTED", flush=True)

                    # #### HALTED #### #

                    async for msg in ws:


                        print(f"WAIT FOR RESUMED (msg={msg})", flush=True)

                        if self._channel_resumed(msg, channel):

                            print("CHANNEL IS RESUMED")

                            break

                    print(f'CHANNEL IS RESUMED (channel={channel})', flush=True)

                    #print('->checking if channel halted')

                    async for msg in ws:

                        print(f"WAIT FOR HALTED (msg={msg})", flush=True)

                        if self._channel_halted(msg, channel):

                            break

                        else:

                            fn(msg, channel)

                    #print(f'WS: channel halted {channel}')
                    #print('-> apparently channel halted')

                elif event == 'paused':

                    # #### PAUSED #### #

                    for check in range(1, number_of_checks + 1):

                        print(f'pause check #{check}', flush=True)

                        async for msg in ws:

                            if self._channel_paused(msg, channel):

                                break

                            else:

                                fn(msg, channel)

                #await ws.close() # hopefully never neccessary

    def _channel_started(self, event, channel):

        if not self._connection_api._is_ws_open(event):

            return

        event = event.json()

        if self._check_event(event, 'run', channel, 'started'):

            self._logger.info(f'a script execution started on channel {channel}!')

            self.blocked[channel] = True

            self.resumed[channel] = True
            self.paused[channel] = False
            self.finished[channel] = False
            self.stopped[channel] = False

            return True

        return False

    def _channel_paused(self, event, channel):

        if not self._connection_api._is_ws_open(event):

            return

        event = event.json()

        if self._check_event(event, 'run', channel, 'paused'):

            self._logger.info(f'a command paused on channel {channel}!')

            self.blocked[channel] = True

            self.resumed[channel] = False
            self.paused[channel] = True
            self.finished[channel] = False
            self.stopped[channel] = False

            return True

        return False

    def _channel_resumed(self, event, channel):

        if not self._connection_api._is_ws_open(event):

            return

        event = event.json()

        if self._check_event(event, 'run', channel, 'resumed'):

            self._logger.info(f'a command resumed on channel {channel}!')

            self.blocked[channel] = True

            self.resumed[channel] = True
            self.paused[channel] = False
            self.finished[channel] = False
            self.stopped[channel] = False

            return True

        return False

    def _channel_halted(self, event, channel):

        if not self._connection_api._is_ws_open(event):

            return

        event = event.json()

        if self._check_event(event, 'run', channel, 'stopped'):

            self._logger.info(f'a command stopped on channel {channel}.')

            self.blocked[channel] = False

            self.resumed[channel] = False
            self.paused[channel] = False
            self.finished[channel] = False
            self.stopped[channel] = True

            return True

        if self._check_event(event, 'run', channel, 'finished'):

            self._logger.info(f'a command finished on channel {channel}.')

            self.blocked[channel] = False

            self.resumed[channel] = False
            self.paused[channel] = False
            self.finished[channel] = True
            self.stopped[channel] = False

            return True

        if self._check_event(event, 'run', channel, 'paused'):

            self._logger.info(f'a command paused on channel {channel}.')

            self.blocked[channel] = False

            self.resumed[channel] = False
            self.paused[channel] = True
            self.finished[channel] = False
            self.stopped[channel] = False

            return True

        return False

    def _check_event(self, event, topic, channel, msg):

        try:

            if event['topic'] == topic:

                event_data = event['data'][0]

                if event_data['execution']['channel'] == channel and event_data['msg'] == msg:

                    return True

                else:

                    return False
            else:

                return False

        except KeyError:

            return False

        except Exception:

            self._logger.exception('\nunexpected exception in msg:\n{msg}------\n')

            raise

    #########################################################################################

    async def _start_task(self, machine_id, channel, script):

        url = f"machine/{machine_id}/execute/{channel}"

        self._logger.info(f'START TASK (script={script}, channel={channel},url={url}')

        task = {
            'code': script,
            'partRefs': []
        }

        response = await self._connection_api.post(url, data=task)

        started = self._check_started(response)

        return started

    def _console_output(self, msg, response):

        print(f'{self._current_time()} -- executed {msg} {response}\n')

    def _check_started(self, response):

        if response is None:

            return False

        started = response["started"]

        if started is not None or started == True:

            return True

        return False