import aiohttp
import asyncio

import json

from collections import deque

import time
# from pytz import timezone, utc

import logging

class ConnectionAPI:

    '''
    The AconitySTUDIO Python Client. Allows for easy automation and job
    management.

    For example usages, please consult the examples folder
    in the root directory from this repository.

    To create the client call the `classmethod` create.
    '''

    def __init__(self, login_data):

        # #### LOGGING #### #

        self._logger = logging.getLogger("AconitySTUDIO Connection API")

        # #### Connections #### #

        self.rest_url = login_data['rest_url']

        self.login_url = self.rest_url + '/login'

        self.ws_url = login_data['ws_url']

        self.topic_url = self.ws_url + '/connect'

        # #### login data #### #

        self.email = login_data['email']
        self.password = login_data['password']
        self.time_between_pings = 25

        # #### REST handling #### #

        self._headers = {}

        # history of GET, POST requests #
        self.history = deque([], maxlen = 15)

        # #### Execution #### #

        self.start_time = time.time()

        self._logger.info(f'rest url: {self.rest_url}')

    def __str__(self):

        '''
        Print out some information about the client
        '''

        myself = f'\t\t\tLast {len(self.history)} requests:\n'

        for request in self.history:

            myself += f'\t\t\t\t{request}\n'

        # myself += f'\t\t\tInfo:'

        # infos = ['machine_name', 'machine_id', 'config_name', 'config_id', 'job_name', 'job_id', 'workunit_id', 'session_id']

        # for info in infos:

        #     information = getattr(self, info, 'Not available')

        #     myself += f'\n\t\t\t\t{info}: {information}'

        return myself

    #########
    # SETUP #
    #########

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

        await self._login()

        asyncio.create_task(self._ping(self.time_between_pings))

        self._logger.info('CLIENT SESSION CONNECTION ESTABLISHED')

        return self

    ###########
    # SESSION #
    ###########

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

    async def _login(self):

        '''
        Login function to the Server

        It creates the credentials needed for login and sends them to the
        WebSocket Server.

        The user does not need to call it, see the Factory method `create`.
        '''

        headers = {'content-type': 'application/json'}
        credentials = {'email': self.email, 'password': self.password}

        response_data = await self.post(url = 'login', data= credentials, headers = headers)

        token = 'XSRF-TOKEN=' + response_data['authToken']

        self.user_id = response_data['userId']

        headers = {
            'Cookie': token,
            'X-XSRF-TOKEN': response_data['authToken'],
            'Authorization': token
        }

        self._headers = headers

        self._logger.info(f'token: {token}')

        self._logger.info(f'user_id: {self.user_id}')

    ##############################
    # HTTP REQUESTS GET/PUT/POST #
    ##############################

    async def _http_request(self, method, url, log_level='info', headers={}, verbose=False, data=None, timeout=300):

        if method not in ['put','post','get']:

            raise AttributeError('Invalid http request method. Must be put/post/get')

        if 'none' in url or 'None' in url:

            raise ValueError(f'Invalid url: {url}. (contains "None")')

        if 'ping' not in url:

            self._logger.info(f'{method} {url}')

            self.history.append(f'{method} {url}')

        if headers == {}:

            headers = self._headers.copy()

        url = self.rest_url + '/' + url

        # #### request #### #

        if data is not None:

            headers['content-type'] = 'application/json'

            if type(data) == dict:

                msg = 'post request:\n\n'
                msg += f'\t\theaders:\n\n{headers}\n\n'

                for key, value in data.items():

                    msg += f'\t\t{key}:\n\n{value}\n\n'

                self._logger.debug(msg)

                data = json.dumps(data)

            else:

                self._logger.warning('deprecated input! use dictionary instead of json/string')

        timeout = aiohttp.ClientTimeout(total=timeout)

        async with aiohttp.ClientSession(raise_for_status=True, timeout=timeout) as session:

            try:

                # print(f'starting the {url} request')

                async with session.request(method, url, headers=headers, data=data, timeout=timeout) as resp:

                    # print(f'the {url} request answered with status {resp.status}')

                    if resp.status == 401:

                        text = await resp.text()

                        raise Exception(f'It appears The client has lost the connection (something went wrong with the ping?): {text}')

                    if resp.status == 500:

                        text = await resp.text()
                        self._logger.debug(f'response body 500 error:\n{text}')
                        self._logger.error(f'HTML return value 500, {resp.reason}. Return body has been logged with mode debug')

                    elif resp.status != 200 and resp.status != 500:

                        self._logger.error(f'HTML return value: {resp.status}, reason: {resp.reason}')
                        self._logger.error(f'{resp.request_info}')

                    # resp.raise_for_status() #does nothing if resp.status < 400

                    try:

                        result = await resp.json(content_type=None)

                    except Exception as e:

                        logging.exception(f'response is 200, but data is not in json format: {e} . I return response.text() (instead of response.json())')

                        result = await resp.text()

            except asyncio.TimeoutError:

                self._logger.exception(f'Timeout Error (timeout={timeout})')

                raise

        if 'ping' not in url:

            if log_level not in ['info', 'debug', 'error', 'warning']:

                self._logger.warning(f'wrong log_level received :{log_level}. manually setting it to "info"')
                log_level = 'info'

            # getattr(self._logger, log_level)(f'received:\n{json.dumps(result, indent=3)}')

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

        return await self._http_request(method='post', url=url, data=data, headers=headers, timeout=timeout)

    async def download_chunkwise(self, url, save_to, chunk_size=1024, tries=3):

        download_url = self.rest_url + '/' + url

        headers = self._headers

        for download_try in range(1, tries + 1):

            try:

                async with aiohttp.ClientSession(raise_for_status = True) as session:
                    async with session.get(download_url, headers = headers) as resp:
                        self._logger.info(f'starting to download batch_data to {save_to}')
                        with open(save_to, 'wb') as fd:
                            while True:
                                chunk = await resp.content.read(chunk_size)
                                if not chunk:
                                    break
                                fd.write(chunk)

            except aiohttp.client_exceptions.ClientResponseError:

                self._logger.exception(f'Something went wrong with {url}. Please Check if the file is corrupted, if all tries fail. Try Number {download_try}')

                if download_try == tries:

                    return False

                else:

                    await asyncio.sleep(1)

                    continue

            self._logger.info(f'succeed download {url} on try {download_try}')

            return True

        return False

    #############
    # WEBSOCKET #
    #############

    def _is_ws_open(self, event):

        if event.type == aiohttp.WSMsgType.CLOSED:

            logging.warning('->WS CLOSED')

            return False

        elif event.type == aiohttp.WSMsgType.ERROR:

            logging.warning('->WS ERROR')

            return False

        return True

    async def process_websocket_data(self, processor):

        self._logger.info(f'START PROCESS WEBSOCKET DATA')

        async with aiohttp.ClientSession(headers=self._headers) as session:

            async with session.ws_connect(self.topic_url) as self._ws:

                async for msg in self._ws:

                    if msg.type == aiohttp.WSMsgType.CLOSED:

                        self._logger.warning('->WS CLOSED')

                        return

                    elif msg.type == aiohttp.WSMsgType.ERROR:

                        self._logger.warning('->WS ERROR')

                        return

                    msg = msg.json()

                    processor(msg)
