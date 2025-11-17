#!/home/arnaud/venv/bin/python3

import argparse
import tomllib
from budget_report import read_from_config

WRITE_REFERENCE_FILES = True

parser = argparse.ArgumentParser(
    prog='br',
    description='Extract tables from budget report')
parser.add_argument('-c', '--config', type=str, default='config.toml', help='configuration file')
parser.add_argument('-o', '--output-dir', type=str, default='.', help='output directory')
parser.add_argument('-r', '--only-read', help='just read the table, no processing', action='store_true')

args = parser.parse_args()
config_filename = args.config
output_dir = args.output_dir
only_read = args.only_read

with open(config_filename, 'rb') as f:
    conf = tomllib.load(f)
filename = conf['general']['filename']

for table in conf['general']['tables']:
    ct = conf[table]
    c = read_from_config(filename, ct, only_read)
    if WRITE_REFERENCE_FILES:
        c.to_csv('/'.join([output_dir, table + '.csv']), float_format='%.2f')

print('-'*50, 'Done')

