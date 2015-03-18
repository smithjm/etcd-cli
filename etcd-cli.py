#!/usr/bin/env python

import yaml
import argparse
import ConfigParser
import logging
import os
from os.path import isfile, expanduser
import etcd
import etcd.client
import glob
import jinja2

def create_dir(path):
    try:
        c.directory.create(path)
    except etcd.exceptions.EtcdAlreadyExistsException:
        pass

# Get arguments
parser = argparse.ArgumentParser(add_help=False)
parser.add_argument('-c', '--config', help='Configuration file')
parser.add_argument('-d', '--debug', action='store_true', help='Print debug info')
parser.add_argument('-y', '--yes', action='store_true', help='Answer yes to all queries')
init_args, unknown = parser.parse_known_args()

# Create formatter
try:
    import colorlog
    formatter = colorlog.ColoredFormatter("[%(log_color)s%(levelname)-8s%(reset)s] %(log_color)s%(message)s%(reset)s")
except ImportError:
    formatter = logging.Formatter("[%(levelname)-8s] %(message)s")

# Create console handle
console = logging.StreamHandler()
console.setFormatter(formatter)

loglvl = logging.WARN
if init_args.debug:
    loglvl = logging.DEBUG

# Create logger
logger = logging.getLogger(__name__)
logger.setLevel(loglvl)
logger.addHandler(console)

# Get configuration
config = ConfigParser.ConfigParser()

# Set defaults
config.add_section('main')
config.set('main', 'node', 'etcd')
config.set('main', 'port', '4001')
config.set('main', 'schemas', 'schemas')
config.set('main', 'templates', 'templates')

# Load config
cfile = None
if init_args.config:
    if isfile(init_args.config):
        cfile = init_args.config
    else:
        logger.error('Config file doesn''t exist: {0}'.format(init_args.config))
        exit(1)
elif isfile(expanduser('~/.etcd-cli.conf')):
    cfile = expanduser('~/.etcd-cli.conf')
elif isfile('/etc/etcd-cli/etcd-cli.conf'):
    cfile = '/etc/etcd-cli/etcd-cli.conf'

logger.info("Using config file: {0}".format(cfile))
config.read(cfile)

# Load schema
schemas = {}
for fn in glob.glob(config.get('main', 'schemas') + '/*.yaml'):
    content = open(fn).read()
    try:
        schemas.update(yaml.load(content))
    except Exception, e:
        logger.critical('Failed to parse YAML in schema file: {0}'.format(e))
        exit(1)

resources = schemas.keys()

# Add Parser
parser = argparse.ArgumentParser()
parser.add_argument('-c', '--config', help='Configuration file')
parser.add_argument('-d', '--debug', action='store_true', help='Print debug info')
parser.add_argument('-y', '--yes', action='store_true', help='Answer yes to all queries')

subparser = parser.add_subparsers(dest = 'action')

parsers = {}
for action in  [ 'get', 'add', 'modify', 'delete', 'list' ]:

    parsers[action, 'first'] = subparser.add_parser(action)
    parsers[action, 'second'] = parsers[action, 'first'].add_subparsers(dest = 'resource')
    for resource in resources:
        parsers[action, resource] = parsers[action, 'second'].add_parser(resource)

        if not 'primary' in schemas[resource]:
            logger.error("Schema: %s needs to declare a primary key" % resource)
            exit(1)
        key = schemas[resource]['primary']

        required_fields = [ key ]
        if 'required' in schemas[resource]:
            required_fields = schemas[resource]['required']

        if action == 'list':
            parsers[action, resource].add_argument('--format', choices = ['text', 'table', 'csv', 'json', 'yaml'], default = 'text', help = 'Print format')
            parsers[action, resource].add_argument('--fields', help = 'Fields to print, ignored by JSON or YAML')

        elif action == 'get':
            descr = schemas[resource][key]['description']
            parsers[action, resource].add_argument(key, help = descr)
            parsers[action, resource].add_argument('--format', choices = ['text', 'table', 'csv', 'json', 'yaml'], default = 'text', help = 'Print format')
            parsers[action, resource].add_argument('--fields', help = 'Fields to print, ignored by JSON or YAML')

        elif action == 'delete':
            descr = schemas[resource][key]['description']
            parsers[action, resource].add_argument(key, help = descr)

        else:
            for entry in schemas[resource].keys():
                if entry == 'primary':
                    continue

                ftype = None
                if not 'type' in schemas[resource][entry]:
                    logger.error("Schema: %s entry: %s needs to declare a type" % (resource, entry))
                    exit(1)
                ftype = schemas[resource][entry]['type']

                if ftype != 'array' and ftype != 'string' and ftype != 'boolean':
                    logger.error("Schema: %s entry: %s has an unsupported type: %s for this CLI" % (resource, entry, ftype))
                    exit(1)

                descr = None
                if 'description' in schemas[resource][entry]:
                    descr = schemas[resource][entry]['description']

                if entry == key:
                    parsers[action, resource].add_argument(key, help = descr)
                    continue

                arguments = [ '--%s' % entry ]
                if 'short' in schemas[resource][entry]:
                    arguments = [ '-{0}'.format(schemas[resource][entry]['short']), '--{0}'.format(entry) ]

                choices = None
#                if action != 'modify' and 'enum' in schemas[resource]['schema'][entry]:
#                    choices = schemas[resource]['schema'][entry]['enum']

                required = False
                if action != 'modify' and entry in required_fields:
                    required = True

                default = None
                if action != 'modify' and 'default' in schemas[resource][entry]:
                    default = schemas[resource][entry]['default']

                if len(arguments) > 1:
                    parsers[action, resource].add_argument(arguments[0], arguments[1], choices = choices, required = required, default = default, help = descr)
                else:
                    parsers[action, resource].add_argument(arguments[0], choices = choices, required = required, default = default, help = descr)

args = parser.parse_args()
arglist = vars(args)

# Load template
fn = config.get('main', 'templates') + '/{0}.jinja'.format(args.resource)
template = None
if isfile(fn):
    logger.info("Loading template: {0}".format(fn))
    template = open(fn).read()
else:
    logger.error('Missing template file: {0}'.format(fn))
    exit(1)

c = etcd.client.Client(host=config.get('main', 'node'), port=config.get('main', 'port'), is_ssl=False)

if args.action == 'add':
    template = jinja2.Template(open(fn).read())
    try:
        result = template.render(arglist)
    except Exception, e:
        logger.error('Failed to parse JINJA in template: {0}\n{1}'.format(fn, e))

    # Accept input
    if not args.yes:
        print 'Adding:\n{0}\n'.format(result)
        answer = raw_input('Do you want to proceed: [y/n]? ')
        if answer and answer[0].lower() != 'y':
            exit(1)

    for line in result.splitlines():
        path, val = line.rsplit(':', 1)
        dir, key = path.rsplit('/', 1)
        logger.info('Set: {0}/{1}: {2}'.format(dir.strip(), key.strip(), val.strip()))
        create_dir(dir.strip())
        c.node.set(path.strip(), val)
