import logging, sys
from pytz import timezone, utc
import datetime

import decorator
import json
import asyncio

from collections import defaultdict

ADRESS = {
    'midi': '192.168.1.128:9000',
    'build': '192.168.1.62:9000',
    'test': '192.168.1.62:9000',
    'test_midi': '192.168.1.62:9000',
    'test_one': '192.168.1.62:9000',
    'localhost': '127.0.0.1:9000'
         }

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
repeat(layer)'''

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

def customTime(*args):
    ''' Converts time to the local machine timezone.'''
    utc_dt = utc.localize(datetime.datetime.utcnow())
    my_tz = timezone("Europe/Berlin")
    converted = utc_dt.astimezone(my_tz)
    return converted.timetuple()

def filter_out_keys(data, allowed = ['name', 'type', 'value']):
    ''' Loop through input dictionary and only retain the 'name', 'type', 'value' keys '''
    new = []
    for param in data:
        #loop through dict any only retain 'name', 'type', 'value'
        new_dict = {k: v for k, v in param.items() if k in allowed}
        new.append(new_dict)
    return new

class JobHandler:
    '''
    The Python Client uses this Class to modify a job locally (so it can later be uploaded to the Server database).
    Additionally, it uses the locally saved job to create init and init_resume scripts
    The user of the Python Client never needs to use this class directly.
    '''
    def __init__(self, job, logger, studio_version):
        ''' Initialises the class using the input job ID '''
        self.studio_version = studio_version
        self.job = job
        self.logger = logger
        self.laser_dict = {i : f'scanner_{i}' for i in range(64)}
        self.laser_dict.update({str(i) : f'scanner_{i}' for i in range(64)})
        self.laser_dict['*'] = '*'
        #self.names_global_params = [param['name'] for param in job['params']]

    def convert_to_string(self, data=None):
        '''Convert input data type into a sring.'''
        if data==None:
            data = self.job
        data = data.replace('False','false')
        data = data.replace('True','true')
        data = data.replace(' ', '')
        return data

    def set(self, job):
        ''' Set the internal job variable to the input job '''
        self.job = job

    def to_json(self):
        ''' Convert current job to json '''
        return json.dumps(self.job)

    def create_laser_beam_sources(self, lasers):
        ''' Creates and returns a dictionary containing the laser beam sources '''
        values = ['*'] + [f'scanner_{i}' for i in lasers]
        laser_beam_sources = {
            "index": 0.0,
            "name": "scanner",
            "type": "enum",
            "value": "*",
            "values": values,
            "unit": "",
            "color": "#ff0000",
            "dirty": False
        }
        return laser_beam_sources

    def get_mapping_parts_to_index(self):
        ''' Returns the indices of the job parts'''
        partRefs = self.job['partRefs']
        non_unique_names = False
        # simply a list with indices [1,2,3,...]
        self.part_indices = []
        # mapping from part -> subpart -> index. Only != None if all names are unique
        self.part_dictionary = {}

        #defaultdict_init = lambda: - 1
        #cnts_part = defaultdict(defaultdict_init)
        #cnts_subpart = {}
        for partRef in partRefs:
            name = partRef['name']
            if '[all]' not in name:
                if name in self.part_dictionary:
                    non_unique_names = True
                else:
                    self.part_dictionary[name] = {}

                #cnts_part[name] += 1
                #cnts_subpart[name] = defaultdict(defaultdict_init)

                for subpart in partRef['subparts']:
                    subpart_index = int(subpart['index'])
                    subpart_name = subpart['name']

                    self.part_indices.append(subpart_index)

                    #PART DICT
                    if subpart_name in self.part_dictionary:
                        non_unique_names = True
                    else:
                        self.part_dictionary[name][subpart_name] = subpart_index

        if non_unique_names:
            self.part_dictionary = {}
        return self.part_indices, self.part_dictionary

    def get_lasers(self):
        ''' Returns the available lasers '''
        params = self.job['partRefs'][0]['params']
        for param in params:
            if param['name'] == 'scanner':
                laser_list =  param['values']
                lasers = [int(elem[-1:]) for elem in laser_list[1:]]
                return lasers, laser_list

    def create_addParts(self):
        ''' Returns the commands to add parts to the job '''
        addParts = 'addParts = function(){'
        partRefs = self.job['partRefs']

        self.all_parts = {}

        self.part_indices = []
        for partRef in partRefs:
            name = partRef['name']
            if '[all]' not in name:
                self.all_parts[name] = [] #bookkeeping

                group_id = partRef['pid']['$oid']
                position = str(partRef['position'])
                group_index = str(int(partRef['key'][0]) + 1)
                addParts += f'\n    $p.addGroup({group_index},{group_id},{position})'
                #print(partRef['subparts'])
                for subpart in partRef['subparts']:
                    subpart_index = int(subpart['index'])
                    self.all_parts[name].append(subpart['name']) #bookkeeping
                    self.part_indices.append(subpart_index)
                    addParts += f'\n    $p.add({subpart_index},{group_index},{subpart["name"]})'
        addParts += '\n\n}'
        return addParts

    def create_preStartParams(self):
        ''' Returns the parameters set before the start of the build '''
        preStartParams = 'preStartParams = function(){'

        g = f"{self.job['params']}"

        if g == '[]':
            self.logger.error('global parameters not imported')
            raise ValueError('global parameters not imported')
        g = self.convert_to_string(g)

        preStartParams += f'\n    $g.params({g})'
        partRefs = self.job['partRefs']

        for partRef in partRefs:
            name = partRef['name']
            if '[all]' not in name:
                for subpart in partRef['subparts']:
                    #print('SUBPART', subpart['params'])
                    subpart_params = filter_out_keys(subpart['params'])
                    if subpart_params == []:
                        self.logger.error('part parameters not imported')
                        raise ValueError('part parameters not imported')
                    #print('\n\n\n\nADDING:', subpart_params,'\n\n\n')
                    subpart_pars = self.convert_to_string(f"{subpart_params}")
                    #subpart_pars = self.convert_to_string(f"{subpart['params']}")
                    idx = int(subpart['index'])
                    preStartParams += f'\n    $p[{idx}].params({subpart_pars})'

        preStartParams += '\n\n}'

        #TODO are these necessary? when?
        preStartParams = preStartParams.replace("'",'\"')
        #preStartParams = preStartParams.replace(' ','')
        return preStartParams

    def create_preStartSelection(self, layers, parts):
        ''' Select the parts to be used '''
        if parts == 'all':
            try:
                self.get_mapping_parts_to_index() #the only purpose of calling this function is to fill the list self.part_indices
                parts = ','.join(map(str, self.part_indices))
            except AttributeError as e:
                self.logger.exception(f'Dont know part_indices? Call create_addParts first')
                raise
        else:
            try:
                if not all(map(lambda x: type(x)==int, parts)):
                    raise ValueError('Not all elements of {parts} are type int')
                parts = ','.join(map(str, parts))
            except:
                self.logger.exception(f'Must give a list of ints for parts')
                raise

        preStartSelection = f'preStartSelection = function(){"{"}'
        preStartSelection += f'\n    $p.use({parts})'
        preStartSelection += f'\n    $p.select({layers[0]},{layers[1]})'
        preStartSelection += f'\n{"}"}'
        return preStartSelection

    def create_init_resume_script(self, layers, parts='all'):
        ''' Message to resume the execution of a script '''
        init_resume_script = self.create_preStartParams()
        init_resume_script += f'\n'
        init_resume_script += self.create_preStartSelection(layers, parts)
        init_resume_script += f'\npreStartParams()\npreStartSelection()'
        return init_resume_script

    def create_init_script(self, layers, parts='all'):
        ''' Message to start the execution of a script '''
        init_script = self.create_addParts()
        init_script += f'\n'
        init_script += self.create_preStartParams()
        init_script += f'\n'
        init_script += self.create_preStartSelection(layers, parts)
        init_script += f'\naddParts()\npreStartParams()\npreStartSelection()'
        return init_script

    def change_global_parameter(self, param, new_value, check_boundaries=True):
        ''' Function to change global build parameters '''
        if not check_boundaries:
            self.logger.info('enabling potentially hazardous mode where boundaries are ignored')

        global_params = self.job['params']

        for i, parameter in enumerate(global_params):
            if parameter['name'] == param:
                #now we consider the cases of Int/Double Interval and bool
                self.logger.info(f'before change: {param}={global_params[i]["value"]}')
                if 'Interval' in parameter['type']:
                    if 'intInterval' in parameter['type']:
                        try:
                            assert int(new_value) == new_value
                        except:
                            self.logger.exception(f'parameter {param}({new_value}) is not type int.')
                            raise
                    if 'doubleInterval' in parameter['type']:
                        try:
                            float(new_value)
                        except:
                            self.logger.exception(f'parameter {param}({new_value}) is not type double/float.')
                            raise
                    try:
                        minimum = global_params[i]['value']['min']
                        maximum = global_params[i]['value']['max']
                        outside_bounds = new_value < minimum or new_value > maximum
                        #print('outside bounds', outside_bounds)
                        if check_boundaries and outside_bounds:
                            corrected = min(max(minimum, new_value), maximum)
                            msg = f'value of {param} must be in [{minimum}, ' \
                                f'{maximum}], but received: {new_value}. Manually ' \
                                f'setting it to {corrected}'
                            new_value = corrected
                            self.logger.warning(msg)
                        elif outside_bounds:
                            self.logger.info(f'The new value {new_value} of parameter {param} was supposed to lie between inside [{minimum},{maximum}], but since check_boundaries==False, no modification was made')
                        global_params[i]['value']['value'] = new_value
                        global_params[i]['dirty'] = True
                    except TypeError:
                        global_params[i]['value'] = new_value
                        global_params[i]['dirty'] = True
                        self.logger.warning(f'parameter {param} has no min and max values defined.')

                elif parameter['type'] == 'bool':
                    try:
                        if new_value == 'True':
                            new_value = True
                        elif new_value == 'False':
                            new_value = False
                        assert(new_value is True or new_value is False)
                    except:
                        self.logger.exception(f'parameter {param} must be "True" or "False" (boolean), but received {new_value}, ({type(new_value)})')
                        raise
                    global_params[i]['value'] = new_value
                    global_params[i]['dirty'] = True
                elif parameter['type'] == 'double':
                    try:
                        new_value = float(new_value)
                    except:
                        self.logger.exception(f'parameter {param} must be set to a double value, but the value {new_value} could not be converted to double')
                        raise
                    global_params[i]['value'] = new_value
                    global_params[i]['dirty'] = True
                else:
                    msg = f'{param} has type {parameter["type"]}. Must be IntInterval, DoubleInterval or bool'
                    self.logger.error(msg)
                    raise ValueError(msg)

                self.logger.info(f'trying to set {param}={global_params[i]["value"]}')
                break
        else:
            self.logger.error(f'parameter {param} is not found in global parameters!'
                          f' Are all parameters imported from the configuration?')
            raise ValueError

    def change_part_parameter(self, part_id, param, new_value, laser = '*', check_boundaries=True):
        ''' Function to build parameters for individual parts '''
        if not check_boundaries:
            self.logger.info('enabling potentially hazardous mode where boundaries are ignored')

        if self.studio_version == 2:
            available_lasers, laser_list = self.get_lasers() # list: ["*", "scanner_1", ... , "scanner_4"]
            laser = self.laser_dict[laser] #mapping 1->"scanner_1", 2->"scanner_2", etc, "*"->"*"
            #print('AVAILABLE LASERS', available_lasers)
            if laser not in laser_list:
                raise ValueError(f'Cant select laser {laser}. choices: {laser_list}')

        partRefs = self.job['partRefs']

        for partRef in partRefs: #main parts
            for subpart in partRef['subparts']: #sub parts
                if int(subpart['index']) == int(part_id): #we found our part
                    #print('FOUND:', param, partRef['name'], subpart['name'])

                    found_laser = False
                    found_param = False
                    for i, parameter in enumerate(subpart['params']):
                        if parameter['name'] == 'scanner':
                            found_laser = True
                            if laser != '*':
                                self.logger.info(f'Changing laser from {parameter["value"]} to {laser}')
                                parameter['value'] = laser
                                parameter['dirty'] = True
                                #ignore parameter['force']
                        if parameter['name'] != param:
                            continue
                        #now we consider the cases of Int/Double Interval and bool
                        found_param = True
                        if 'Interval' in parameter['type']:
                            if 'intInterval' in parameter['type']:
                                try:
                                    assert int(new_value) == new_value
                                    new_value = int(new_value)
                                except:
                                    self.logger.exception(f'parameter {param}({new_value}) is not type int.')
                                    raise
                            if 'doubleInterval' in parameter['type']:
                                try:
                                    new_value = float(new_value)
                                except:
                                    self.logger.exception(f'parameter {param}({new_value}) is not type double/float.')
                                    raise

                            self.logger.info(f'param {param} before change: {partRef["name"]}, {subpart["name"]}, {subpart["params"][i]["value"]["value"]}')
                            try:
                                minimum = subpart['params'][i]['value']['min']
                                maximum = subpart['params'][i]['value']['max']

                                outside_bounds = new_value < minimum or new_value > maximum
                                if check_boundaries and outside_bounds:
                                        correction = min(max(minimum, new_value), maximum)
                                        msg = f'value of {param} must be in [{minimum}, ' \
                                            f'{maximum}], but received: {new_value}. Manually ' \
                                            f'setting it to {correction}'
                                        new_value = correction
                                        self.logger.warning(msg)
                                elif outside_bounds:
                                        self.logger.info(f'The new value {new_value} of parameter {param} was supposed to lie between inside [{minimum},{maximum}], but since check_boundaries==False, no modification was made')

                                subpart['params'][i]['value']['value'] = new_value
                                subpart['params'][i]['dirty'] = True
                                self.logger.info(f'trying to set: {partRef["name"]}, {subpart["name"]}, {subpart["params"][i]["value"]["value"]}')
                            except TypeError:
                                subpart['params'][i]['value'] = new_value
                                subpart['params'][i]['dirty'] = True
                                self.logger.warning(f'parameter {param} has no min and max values defined.')
                                self.logger.info(f'trying to set  {partRef["name"]}, {subpart["name"]}, {subpart["params"][i]["value"]}')



                            # COLOR
                            #subpart['params'][i]['color'] = "#0000ff" #cyan -> python client shall not be bothered with colors.
                            # SYNC -> ignore subpart['params'][i]['sync'] completely. It is not used anywhere anymore.

                        elif parameter['type'] == 'bool':
                            try:
                                if new_value == 'True':
                                    new_value = True
                                elif new_value == 'False':
                                    new_value = False
                                assert(new_value is True or new_value is False)
                            except:
                                self.logger.exception(f'parameter {param} must be "True" or "False" (boolean), but received {new_value}, ({type(new_value)})')
                                raise
                            subpart['params'][i]['value'] = new_value
                            subpart['params'][i]['dirty'] = True
                        elif parameter['type'] == 'double':
                            try:
                                new_value = float(new_value)
                            except:
                                self.logger.exception(f'parameter {param} must be set to a double value, but the value {new_value} could not be converted to double')
                                raise
                            subpart['params'][i]['value'] = new_value
                            subpart['params'][i]['dirty'] = True
                        else:
                            msg = f'{param} has type {parameter["type"]}. Only the cases IntInterval, DoubleInterval or bool get processed here.'
                            self.logger.error(msg)
                            raise ValueError(msg)
                    #for p in subpart['params']:
                    #    print(json.dumps(p, indent=3))
                    if not found_param:
                        self.logger.error(f'parameter {param} not found in parameters')
                        raise ValueError(f'parameter {param} not found in parameters')
                    else:
                        return

        self.logger.error(f'part id {part_id} does not exist')
        raise ValueError(f'part id {part_id} does not exist')

def get_adress(args):
    ''' Return the address of the machine '''
    if len(args) > 1:
        machine = args[1]
        if machine in ADRESS:
            adress = ADRESS[machine]
        else:
            sys.exit(f'machine {machine} not recognized, use {list(ADRESS.keys())}')
    else:
        adress = ADRESS['build']
    return adress

def _gather(self, logger, attribute, value):
    ''' Return attributes from the class object '''
    if value == None:
        if getattr(self, attribute) != None:
            value = getattr(self, attribute)
        else:
            logger.error(f'Please provide a value for the parameter {attribute} or set the attribute {attribute} manually')
            raise ValueError(f'Please provide a value for the parameter {attribute} or set the attribute {attribute} manually')
    return value

def log_setup(filename, directory_path = ''):
    ''' Initialise the logging functionality '''
    t = customTime()
    now = str(t.tm_year) + '-' + str(t.tm_mon) + '-'  + str(t.tm_mday) + \
        '_' + str(t.tm_hour) + '-' + str(t.tm_min)
    filename = filename.split('.py')[0] + '_' + str(now) + '.log'
    file_handler = logging.FileHandler(filename=directory_path + filename)
    file_handler.setLevel(logging.DEBUG)
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(logging.INFO)
    handlers = [file_handler, stdout_handler]

    logging.Formatter.converter = customTime

    Format = "[%(asctime)s - %(funcName)15s()] %(levelname)s %(message)s"

    logging.basicConfig(
        level = logging.DEBUG,
        handlers= handlers,
        format = Format,
        datefmt='%d.%m.%Y %H:%M:%S',
    )

    logger = logging.getLogger('LOGGER_NAME')
    asyncio_logger = logging.getLogger('asyncio').setLevel(logging.WARNING)


def get_time_string(raw_time_stamp, format ='%b %d %H:%M:%S'):
    ''' Return a string with the current time '''
    time_string = ''
    try:
        unix_time = int(float(raw_time_stamp) / 1000)
        delta = datetime.timedelta(hours = 1)
        t = datetime.datetime.fromtimestamp(unix_time)
        t += delta
        time_string = ' (' + t.strftime(format) + ')'
    except Exception :
        logging.exception('exception trying to get datetime from timestamp')
    return time_string


def track_layer_number(client, msg):
    ''' Update the current layer class attribute '''
    if 'topic' in msg and msg['topic'] == 'cmds' and 'data' in msg:
        for data in msg['data']:
            if 'name' in data and 'value' in data and data['name'] == 'report':
                value = json.loads(data['value'])
                if 'counts' in value and 'AddLayerCommand' in value['counts']:
                    client.current_layer = value['counts']['AddLayerCommand']
                client.value = value
                print('track_layer_number:', value)

        client.current_layer = 5

'''
class Decorators:
    #execute, stop_job, resume_job, start_job
    @classmethod
    @decorator.decorator
    async def _wait_until_channel_done(client, coro, *args, **kwargs):
        print('creating waiting task')
        waiter = asyncio.create_task(client._channel_done(*args, **kwargs))
        res = await coro(*args, **kwargs)
        print('awaited coro (execution')
        await waiter
        print('done awaiting the waiter')
        return res
'''
