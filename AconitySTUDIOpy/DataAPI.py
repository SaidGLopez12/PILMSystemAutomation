import time

import json
import asyncio
import os

import aiohttp

from pymongo import MongoClient



import logging

class DataAPI:

    '''
    The AconitySTUDIO Python Client. Allows for easy automation and job
    management.

    For example usages, please consult the examples folder
    in the root directory from this repository.

    To create the client call the `classmethod` create.
    '''

    def __init__(self, connection_api):

        # #### LOGGING #### #
        
        self._logger = logging.getLogger("AconitySTUDIO Data API")

        # #### CONNECTION API #### #

        self._connection_api = connection_api

        # # #### MongoDB #### #

        self.pymongo_database = False

        self.processors = {}

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
    
        self.ws_processing_task = asyncio.create_task(self._connection_api.process_websocket_data(self._process_topic_data))

        self._logger.info('CLIENT TOPIC DATA CONNECTION ESTABLISHED')

        return self

    ##############
    # BATCH DATA #
    ##############

    async def get_meta_data(self, config_id, workunit_id, log_level):

        # this route gives us information about the batch data we can get
        url = f'data/{config_id}/workUnit/{workunit_id}'

        batch_infos = set([])

        # extract informaton
        metaData = await self._connection_api.get(url, log_level = log_level)

        return metaData

    async def get_download_urls(self, session_id, config_id, workunit_id, topics):
        '''
        This function analyses what is received by the route
        data/{client.config_id}/workUnit/{client.job_id}.

        The main purpose is to create the download url.
        '''

        workunit_metadata = await self.get_meta_data(config_id, workunit_id, log_level = 'debug')
         
        info = set()

        for data in workunit_metadata:
        
            sid = data['sessionId']
            cid = data['configId']
            jid = data['workId']
            hub = data['topic']
        
            creation = data['workCreation']
        
            #print(sid, cid, jid, hub)
            if (sid == session_id and cid.split('_')[2] == config_id and jid.split('_')[2] == workunit_id and hub in topics):

                #data we are interested in! If interested in all data, simply remove ore change the statement.
                for attr in data['attributes']:
                
                    sensorId = attr['id']
                
                    for group in attr['groups']:
                
                        subpIdx = group['id']
                
                        for height in group['data']:
                
                            url = f'sessions/{sid}/configId/{cid}/jobIdx/{jid}/hub/{hub}/sensorId/{sensorId}/subpIdx/{subpIdx}/z/{height}'
                
                            info.add((url, sid, cid, jid, hub, sensorId, subpIdx, height, creation))
        
        return info

    async def download_batch_data(self, batch_infos, base_path_pyrometer_data, url_appendix, path_prefix):

        tasks = []
        
        for info in batch_infos:
            
            url = info[0]
            info_tuple = info[1:]
        
            info = {
                'session_id': info_tuple[0],
                'config_id': info_tuple[1],
                'job_id': info_tuple[2],
                'topic': info_tuple[3],
                'sensor_id': info_tuple[4],
                'subpart_id': info_tuple[5],
                'height': info_tuple[6],
                'creation_time': str(int(info_tuple[7]) / 1000)
            }

            url += url_appendix

            base_path = f'{base_path_pyrometer_data}/{info["session_id"]}/{info["config_id"]}/{info["job_id"]}/sensors/{info["topic"]}/{info["sensor_id"]}/{info["subpart_id"]}'
            
            os.makedirs(base_path, exist_ok = True)

            save_to = base_path + '/' + path_prefix + '_layer_' + info["height"]
            
            if not os.path.isfile(save_to): #dont redownload files we already have
            
                tasks.append(asyncio.create_task(self._connection_api.download_chunkwise(url, save_to, chunk_size=1024)))
            
        results = await asyncio.gather(*tasks)
        
        return results

    ###############
    # STREAM DATA #
    ###############

    # async def subscribe_report(self, name):
        
    #     '''
    #     Subscribes to reports via the WebServer.
        
    #     To get information about the reports use the route configurations/{client.config_id}/topics).

    #     :param name: name of report, example reports: 'state', 'task'.
    #     :type name: string
    #     '''

    #     task = {
    #         'type': name,
    #         'name': name,
    #         'task': 'register'
    #     }

    #     while True:
        
    #         try:
        
    #             await self._ws.send_json(task)
        
    #             break
        
    #         except AttributeError:
        
    #             self._logger.debug('websocket connection not (yet) established, cant subscribe to report')
        
    #             await asyncio.sleep(0.01)
        
    #     self._logger.info(f'Subscription to report {name} sent!')

    # async def subscribe_topic(self, name):
        
    #     '''
    #     Subscribes to reports via the WebServer.
        
    #     To get information about the topics use the route configurations/{client.config_id}/topics).

    #     :param name: name of topic. Examples are 'State', 'Sensor','cmds' and 'Positioning'.
        
    #     :type name: string
    #     '''
        
    #     task = {
    #         'type': 'machine',
    #         'name': name,
    #         'task': 'register'
    #     }

    #     while True:
        
    #         try:
        
    #             await self._ws.send_json(task)
        
    #             break
        
    #         except AttributeError:
        
    #             self._logger.debug('websocket connection not (yet) established, cant subscribe to topic')
        
    #             await asyncio.sleep(0.01)

    #     self._logger.info(f'Subscription to topic {name} sent!')

    ########################################################

    def _process_topic_data(self, msg):
        
        topic = ""

        if 'topic' in msg and msg['topic'] is not None:

            topic =  msg['topic']

        elif 'report' in msg and msg['report'] is not None:

            topic =  msg['report']

        for processor in self.processors[topic]:
                                    
            try:
                
                processor(topic, msg)
            
            except Exception:
            
                self._logger.exception(f'processing ({processor}) ws msg raised an exception.\n')
            
            # loop = asyncio.get_running_loop()
            # await loop.run_in_executor(None, processor, msg_new)


        # call client.enable_pymongo_database to activate this feature

        if self.pymongo_database: 
            
            msg['_timestamp_db'] = time.time()
            
            post_id = self._db.insert_one(msg).inserted_id
            
            if self.keep_last > 0:
            
                delete_time = time.time() - self.keep_last
            
                self._db.remove({'_timestamp_db':{'$lt': delete_time}})


    ########################################################

    async def subscribe_event_topic(self, name):
        
        return await self._subscribe_topic("state", name)

    async def subscribe_engine_topic(self, name):

        return await self._subscribe_topic(name, name)

    async def subscribe_data_topic(self, name):

        return await self._subscribe_topic("machine", name)
    
    ##################################################################

    async def _subscribe_topic(self, topic_type, topic_name):

        self._logger.info(f'TRY SUBSCRIPTION (topic= {topic_name}, type={topic_type})')

        task = {
            'type': topic_type,
            'name': topic_name,
            'task': 'register'
        }

        while True:
        
            try:
        
                await self._connection_api._ws.send_json(task)

                break
        
            except AttributeError:
        
                self._logger.debug(f"websocket connection not (yet) established, can't subscribe (topic= {topic_name}, type={topic_type})")
        
                await asyncio.sleep(0.01)
        
        self._logger.info(f"SEND SUBSCRIPTION (topic= {topic_name}, type={topic_type})")

        return True


    def add_processor(self, topics, processor):

        self._logger.info(f"ADD PROCESSOR (topics={topics})")

        for topic in topics:

            self._logger.info(f"ADD PROCESSOR (topic={topic})")

            if topic not in self.processors:

                self.processors[topic] = []

            self.processors[topic].append(processor)

    ################################
    # PYTHON CLIENT'S OWN DATABASE #
    ################################

    def enable_pymongo_database(self, name='database_test', keep_last=120):

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

            self._logger.exception('Error while connecting to PyMongoDB. Possibly check if MongoDB Community Edition is installed and running?')
            
            return

        self.keep_last = keep_last
        self.pymongo_database = True

        self._logger.info(f'connected to mongo database {name}')

    async def save_data_to_pymongo_db(self):

        '''
        Continually saves the output of the WebSocket Server
        by saving it into a Mongo database.
        Call enable_pymongo_database() before calling this function.
        '''
        
        if self.pymongo_database == False:

            self._logger.error('No database configured. Call enable_pymongo_database')
            
            return
        
        while True:

            msg = await self._ws.recv()
            msg = self.fix_ws_msg(msg)
            
            msg_json = json.loads(msg)
            
            self._logger.info(f'received data from websocket: {str(msg_json)[:30]}...')

            msg_json['_timestamp_db'] = time.time()
            
            post_id = self._db.insert_one(msg_json).inserted_id
            
            if self.keep_last > 0:
            
                delete_time = time.time() - self.keep_last
            
                self._db.remove({'_timestamp_db':{'$lt': delete_time}})

    def fix_ws_msg(msg, replace_value = - 1):

        '''
        A Helper function.
        Sometimes, nans get passed from the websocket to the client.
        Until this is fixed, we simply get rid of them and
        replace them with %s
        ''' % (replace_value)
        
        if '"value":nan' in msg:
        
            replacement = '"value":%s' % replace_value
        
            msg = msg.replace('"value":nan', replacement)
    
            logging.warning(f'replaced nan(s) with {replace_value}')
    
        return msg

    