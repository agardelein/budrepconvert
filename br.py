#!/home/arnaud/venv/bin/python3

import argparse
import tomllib
from budget_report import read_from_config

WRITE_REFERENCE_FILES = True

parser = argparse.ArgumentParser(
    prog='br',
    description='Extract tables from budget report')
parser.add_argument('-c', '--config', type=str, default='config.toml', help='configuration file')

args = parser.parse_args()
config_filename = args.config

with open(config_filename, 'rb') as f:
    conf = tomllib.load(f)
filename = conf['general']['filename']

for table in conf['general']['tables']:
    ct = conf[table]
    c = read_from_config(filename, ct)
    if WRITE_REFERENCE_FILES:
        c.to_csv(table + '.csv', float_format='%.2f')

print('-'*50, 'Done')

