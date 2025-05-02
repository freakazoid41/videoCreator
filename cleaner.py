import yaml
import os
import time
from datetime import date,datetime
from os import walk

script_dir = os.path.dirname(os.path.realpath(__file__))

with open(script_dir+'/settings.yaml') as f:
    my_dict = yaml.safe_load(f)


def numOfDays(date1, date2):
  #check which date is greater to avoid days output in -ve number
    if date2 > date1:   
        return (date2-date1).days
    else:
        return (date1-date2).days



filenames = next(walk(my_dict['main_output']), (None, None, []))[2]  # [] if no file
print(str(len(filenames)) + ' => Total File Founded..')

oldCount  = 0
for f in filenames:
    fileDate = os.path.getctime(my_dict['main_output']+'/'+f)
    dayDiff  = numOfDays(datetime.fromtimestamp(fileDate) , datetime.now())

    if dayDiff > 14 : 
        oldCount += 1
        print(f+' => is too old .. removing.. ('+time.ctime(fileDate)+')')
        #os.unlink(my_dict['main_output']+'/'+f)

print(str(oldCount) + ' => Old File Founded and Removed..')


    
