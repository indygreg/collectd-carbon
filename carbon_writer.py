#  Copyright 2010 Gregory Szorc
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#
import collectd
import socket
from time import time

host = None
port = None
types = {}

def carbon_parse_types_file(path):
    global types

    f = open(path, 'r')

    for line in f:
        fields = line.split()
        if len(fields) < 2:
            continue

        type_name = fields[0]
        v = []
        for ds in fields[1:]:
            ds = ds.rstrip(',')
            ds_fields = ds.split(':')

            if len(ds_fields) != 4:
                collectd.warning('invalid types.db data source type: %s' % ds)
                continue

            v.append(ds_fields)

        types[type_name] = v

    f.close()

def carbon_config(c):
    global host, port

    for child in c.children:
        if child.key == 'LineReceiverHost':
            host = child.values[0]
        elif child.key == 'LineReceiverPort':
            port = int(child.values[0])
        elif child.key == 'TypesDB':
            for v in child.values:
                carbon_parse_types_file(v)

    if not host:
        raise Exception('LineReceiverHost not defined')

    if not port:
        raise Exception('LineReceiverPort not defined')

def carbon_init():
    global host, port
    import threading

    d = { 'host': host, 'port': port, 'sock': None, 'lock': threading.Lock() }

    carbon_connect(d)

    collectd.register_write(carbon_write, data=d)

def carbon_connect(data):
    result = False

    data['lock'].acquire()
    if not data['sock']:
        collectd.info('connecting to %s:%s' % ( data['host'], data['port'] ) )
        try:
            data['sock'] = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            data['sock'].connect((host, port))
            result = True
        except:
            result = False
            collectd.warning('error connecting socket')
    else:
        result = True

    data['lock'].release()

    return result

def carbon_write_data(data, s):
    result = False
    data['lock'].acquire()
    try:
        data['sock'].sendall(s)
        result = True
    except:
        collectd.warning('error sending data')

    data['lock'].release()
    return result

def carbon_write(v, data=None):
    if not carbon_connect(data):
        collectd.warning('no connection to carbon server')
        return

    if v.type not in types:
        collectd.warning('carbon module does not know how to handle type %s. do you have all your types.db files configured?' % v.type)
        return

    type = types[v.type]

    if len(type) != len(v.values):
        collectd.warning('differing number of values for type %s' % v.type)
        return

    metric_fields = [ v.host.replace('.', '_') ]

    metric_fields.append(v.plugin)
    if v.plugin_instance:
        metric_fields.append(v.plugin_instance)

    metric_fields.append(v.type)
    if v.type_instance:
        metric_fields.append(v.type_instance)

    time = v.time

    lines = []
    i = 0
    for value in v.values:
        ds_name = type[i][0]
        ds_type = type[i][1]
        i += 1

        path_fields = metric_fields[:]
        path_fields.append(ds_name)

        # TODO handle different data types here
        line = '%s %f %d' % ( '.'.join(path_fields), value, time )
        lines.append(line)

    lines.append('')
    carbon_write_data(data, '\n'.join(lines))

collectd.register_config(carbon_config)
collectd.register_init(carbon_init)
