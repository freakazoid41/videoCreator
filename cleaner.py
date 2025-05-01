import yaml
import os
from os import walk

script_dir = os.path.dirname(os.path.realpath(__file__))

with open(script_dir+'/settings.yaml') as f:
    my_dict = yaml.safe_load(f)


filenames = next(walk(my_dict['main_output']), (None, None, []))[2]  # [] if no file

print(filename)