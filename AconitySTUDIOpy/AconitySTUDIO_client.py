import time
import datetime
import sys
from pytz import timezone, utc

import logging

from AconitySTUDIOpy import ConnectionAPI
from AconitySTUDIOpy import ExecutionAPI
from AconitySTUDIOpy import GatewayAPI
from AconitySTUDIOpy import DataAPI
from AconitySTUDIOpy import JobAPI
from AconitySTUDIOpy import TaskAPI

class AconitySTUDIO_client:

    '''
    The AconitySTUDIO Python Client. Allows for easy automation and job
    management.

    For example usages, please consult the examples folder
    in the root directory from this repository.

    To create the client call the `classmethod` create.
    '''

    def __init__(self, connection_api, gateway_api, execution_api, data_api, job_api, task_api, time_zone="Europe/Berlin"):

        self._logger = logging.getLogger("AconitySTUDIO_client")

        self.connection = connection_api
        self.gateway = gateway_api
        self.execution = execution_api
        self.data = data_api

        self.job = job_api
        self.task = task_api

        self.studio_version = 2

        self.time_out_script_routes = 5

        # #### Execution #### #

        self.time_zone = time_zone

        self.start_time = time.time()

        # self._logger.info(f'rest url: {self.rest_url}')

    def __str__(self):

        '''
        Print out some information about the client
        '''

        myself = f'\t\t\tLast {len(self.connection.history)} requests:\n'

        for request in self.connection.history:

            myself += f'\t\t\t\t{request}\n'

        myself += f'\t\t\tInfo:'

        infos = ['machine_name', 'machine_id', 'config_name', 'config_id', 'job_name', 'job_id', 'workunit_id', 'session_id']

        for info in infos:

            information = getattr(self, info, 'Not available')

            myself += f'\n\t\t\t\t{info}: {information}'

        return myself

    #########
    # SETUP #
    #########

    @classmethod
    async def create(cls, login_data, studio_version, time_zone="Europe/Berlin"):

        '''
        Factory class method to initialize a client.
        Convenient as this function takes care of logging in and creating a websocket connection.
        It will also set set up a ping, to ensure the connection will not be lost.

        :param login_data: required keys are `rest_url`, `ws_url`, `password` and `email`.
        :type login_data: dictionary

        :param studio_version: specify version 1/2/higher
        :type studio_version: int

        :param time_zone: optional timezone specification for timestamp conversion; default is "Europe/Berlin"
        :type time_zone: string

        Usage::

            login_data = {
                'rest_url' : 'http://192.168.1.1:2000',
                'ws_url' : 'ws://192.168.1.1:2000',
                'email' : 'admin@yourcompany.com',
                'password' : '<password>'
            }
            client = await AconitySTUDIO_client.create(login_data, 2)

        '''

        # #### ConnectionAPI #### #

        connection_api = ConnectionAPI.ConnectionAPI(login_data)

        await connection_api.connect()

        # #### DataAPI #### #

        data_api = DataAPI.DataAPI(connection_api)

        await data_api.connect()

        # #### GatewayAPI #### #

        gateway_api = GatewayAPI.GatewayAPI(connection_api)

        # #### ExecutionAPI #### #

        execution_api = ExecutionAPI.ExecutionAPI(connection_api)

        # #### JobAPI #### #

        job_api = JobAPI.JobAPI(connection_api, gateway_api, execution_api, studio_version)

        await job_api.connect()

        task_api = TaskAPI.TaskAPI(execution_api, job_api, studio_version)

        self = AconitySTUDIO_client(connection_api, gateway_api, execution_api, data_api, job_api, task_api, time_zone)

        self._logger.info('CLIENT CREATED')

        return self

    def customTime(self, *args):

        utc_dt = utc.localize(datetime.datetime.utcnow())

        my_tz = timezone(self.time_zone)
        converted = utc_dt.astimezone(my_tz)

        return converted.timetuple()

    def log_setup(self, filename, directory_path=''):

        t = self.customTime()

        now = str(t.tm_year) + '-' + str(t.tm_mon) + '-'  + str(t.tm_mday) + '_' + str(t.tm_hour) + '-' + str(t.tm_min)

        filename = filename.split('.py')[0] + '_' + str(now) + '.log'

        file_handler = logging.FileHandler(filename=directory_path + filename)
        file_handler.setLevel(logging.DEBUG)

        stdout_handler = logging.StreamHandler(sys.stdout)
        stdout_handler.setLevel(logging.INFO)

        handlers = [file_handler, stdout_handler]

        logging.Formatter.converter = self.customTime

        Format = "[%(asctime)s - %(funcName)15s()] %(levelname)s %(message)s"

        logging.basicConfig(
            level=logging.DEBUG,
            handlers=handlers,
            format=Format,
            datefmt='%d.%m.%Y %H:%M:%S',
        )

        logger = logging.getLogger('LOGGER_NAME')
        asyncio_logger = logging.getLogger('asyncio').setLevel(logging.WARNING)

    def get_time_string(raw_time_stamp, format='%b %d %H:%M:%S'):

        time_string = ''

        try:

            unix_time = int(float(raw_time_stamp) / 1000)
            delta = datetime.timedelta(hours=1)

            t = datetime.datetime.fromtimestamp(unix_time)
            t += delta
            time_string = ' (' + t.strftime(format) + ')'

        except Exception:

            logging.exception('exception trying to get datetime from timestamp')

        return time_string
