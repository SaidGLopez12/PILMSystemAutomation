import json

import time

import logging

class GatewayAPI:

    def __init__(self, connection_api):

        # #### LOGGING #### #
        
        self._logger = logging.getLogger("AconitySTUDIO GATEWAY API")

        # #### CONNECTION API #### #

        self._connection_api = connection_api

    ############
    # SESSIONS #
    ############

    async def get_sessions(self):

        sessions = await self._connection_api.get('sessions')   

        return sessions

    async def get_session_id(self, n = -1):
        
        '''
        Get all session ids. If successfull, saves the session ID in self.session_id

        :param n: With the default parameter `n=-1`, the most recent session id gets saved to self.session_id (second last session, use n=-2 etc).
        :type n: int

        :return: Session ID
        :rtype: string
        ''' 

        session_id = None

        # GET all recorded sessions #

        sessions = await self.get_sessions()          
        
        # print('ids...')
        # for i, id in enumerate(self.session_ids):
        #    print(i, id)
        
        # #### HANDLE all recorded sessions #### #

        studio_session_ids = []
        
        for sid in sessions:
        
            try:
        
                if sid.split('_')[1] in map(str, range(2000, 2100)):
        
                    studio_session_ids.append(sid)
        
            except IndexError:
        
                pass
        
        try:
            
            # take most recent one if n=-1 #
            session_id = studio_session_ids[n]  
        
        except IndexError:
        
            self._logger.warning(f'could not select session with index {n}. found sessions: {studio_session_ids}')
        
        self._logger.info(f'self.session_id: {session_id}')
        
        return session_id

    ############
    # MACHINES #
    ############

    async def get_machines(self):

        machine_ids = await self._connection_api.get('machines')

        return machine_ids

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
        
        machines = await self.get_machines()

        machine_id = None

        cnt = 0
        for machine in machines:
            
            if machine['name'] == machine_name: 
        
                cnt += 1
                
                machine_id = machine['_id']['$oid']
     
        if cnt == 0:
        
            self._logger.error(f'machine "{machine_name}" cannot be found')
        
        elif cnt > 1:
        
            self._logger.error('More than one machine with the same name found! Please set the machine_id attribute manually. (start GUI AconitySTUDIO -> copy from URL)')
        
            raise ValueError('More than one machine with the same name found! Please set the machine_id attribute manually. (start GUI AconitySTUDIO -> copy from URL)')
        
        else:
        
            self._logger.info(f'self.machine_id: {machine_id}')
            self._logger.info(f'self.machine_name: {machine_name}')
        
            return machine_id
  
    ###########
    # CONFIGS #
    ###########

    async def get_configs(self):

        configs = await self._connection_api.get('configurations')

        return configs

    async def config_exists(self, config_id):
        
        '''
        Checks if a config exists. 
        
        :param config_id: Id of the config
        :type config_id: str

        :rtype: bool
        '''
       
        configs = await self.get_configs()

        for config in configs:
                
            if config['_id']['$oid'] == config_id:
        
                self._logger.info(f'configuration with config id {config_id} exists')
        
                return True
        
        logging.warning(f'no configuration with the given name/config_id could be found!')
        
        return False

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
        
        configs = await self.get_configs()

        cnt = 0
        
        for config in configs:
        
            if config['name'] != config_name:
        
                continue

            cnt += 1

            # #### VERSION 3 #### #
            self.config_operational = config['state'] == 'operational'
                
            self.config_name = config['name']
            self.config_id = config['_id']['$oid']
            config_state = config['state']

        if cnt == 0:
        
            self._logger.error(f'config "{config_name}" cannot be found')
        
            raise ValueError(f'config "{config_name}" cannot be found')
        
        elif cnt > 1:
        
            self._logger.error(f'More than one config with the name {config_name} found! Please set the config_id attribute manually (start GUI AconitySTUDIO -> copy from URL)')
        
            raise ValueError(f'More than one config with the name {config_name} found! Please set the config_id attribute manually (start GUI AconitySTUDIO -> copy from URL')
        
        else:
        
            self._logger.info(f'self.config_name: {self.config_name}\t({config_state})')
            self._logger.info(f'self.config_id: {self.config_id}')
        
            if not self.config_operational:

                self._logger.warning(f'config {config_name} exists, but is not operational')#\n{json.dumps(config,indent=3)}')  

            return self.config_id

    async def config_has_component(self, config_id, component):

        '''
        Checks if a config has a certain component.

        :param config_id: Config Id. If `config_id == None`, the client uses its own attribute config_id.
        :type config_id: string

        :param component: The component to be checked.
        :type component: string

        :rtype: bool
        '''
        
        url = f'configurations/{config_id}/components'
        
        if not (await self.config_exists(config_id=config_id)):
        
            self._logger.warning(f'no config with the config_id {config_id} found!')
        
            raise ValueError(f'no config with the config_id {config_id} found!')

        components = await self._connection_api.get(url)
        
        for comp in components:
        
            if comp['id'] == component:
        
                self._logger.info(f'config has component {component}')
        
                return True
        
        self._logger.info(f'config does not have component {component}')
        
        return False
    
    async def config_state(self, config_id):
        
        '''
        Returns the current state of the config
        
        :param config_id: Id of the config. If none is given, the client uses its own attribute `config_id`.
        :type config_id: str

        :return: 'operational', 'inactive', or 'initialized'
        :rtype: string
        '''
        
        configs = await self.get_configs()

        for config in configs:
            
            # use clients own attribute self.config_id #
            if config['_id']['$oid'] == config_id: 
        
                return config['state']

        raise ValueError('cant check state of config. config with config_id {config_id} can not be found!')

    async def start_config(self, config_id):

        '''
        The attribute "config_id" must be set.
        Restarts the config with that id.

        If no ``config_id`` is set, raises a ValueError.
        '''
        
        if config_id != None:
        
            for cmd in ('init', 'start'):
        
                url = f'configurations/{config_id}/{cmd}'

                try:
        
                    t1 = time.time()
            
                    await self._connection_api.get(url)
            
                    self._logger.info(f'{cmd} {config_id} took {time.time()-t1:.2f} s')
            
                    state = await self.config_state(config_id)
            
                    self._logger.info(f'config {self.config_id} is in state {state}')

                except:
        
                    self._logger.error(f'problem with {url}, abort restarting config')

                    return False

            return True
            
        else:
        
            self._logger.error('could not restart config, no config_id known')
        
            raise ValueError('could not restart config, no config_id known')

    async def stop_config(self, config_id):

        '''
        The attribute "config_id" must be set.
        Restarts the config with that id.

        If no ``config_id`` is set, raises a ValueError.
        '''
        
        if config_id != None:
        
            for cmd in ('stop'):
        
                url = f'configurations/{config_id}/{cmd}'
        
                try:
        
                    t1 = time.time()
        
                    await self._connection_api.get(url)
        
                    self._logger.info(f'{cmd} {config_id} took {time.time()-t1:.2f} s')
        
                    state = await self.config_state(config_id)
        
                    self._logger.info(f'config {config_id} is in state {state}')
        
                except:
        
                    self._logger.error(f'problem with {url}, abort restarting config')

                    return False

            return True

        else:
        
            self._logger.error('could not restart config, no config_id known')
        
            raise ValueError('could not restart config, no config_id known')
