import yaml
from os import walk


with open(script_dir+'/settings.yaml') as f:
    my_dict = yaml.safe_load(f)


filenames = next(walk(my_dict['main_output']), (None, None, []))[2]  # [] if no file

print(filename)