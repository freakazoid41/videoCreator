
# Importing Required Modules 
import yaml
import sys
from PIL import Image
from PIL import GifImagePlugin
import os
import os.path
import smtplib
from email.mime.text import MIMEText

import glob
import shutil
import cv2
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import base64
from io import BytesIO
import json
from natsort import natsorted
from moviepy import *
from pydub import AudioSegment
import datetime
from elevenlabs import stream
from elevenlabs.client import ElevenLabs
from elevenlabs import play

## sometimes chrome is stays open on server after script teminated for some reason run : pkill -9 chrome : for session clean
## also run rm /var/www/html/dogumgunu.aydemenerji.com.tr/public/birth.json.lock after teminate

script_dir = os.path.dirname(os.path.realpath(__file__))
output_dir = script_dir+'/alphavideos/'
audio_output_dir = script_dir+'/audios/'

with open(script_dir+'/settings.yaml') as f:
    my_dict = yaml.safe_load(f)

def processImage(infile):
    try:
        im = Image.open(infile)

        files = glob.glob(script_dir+'/images/*')
        for f in files:
            os.remove(f)


    except IOError:
        print ("Cant load", infile)
        sys.exit(1)
    i = 0
    mypalette = im.getpalette()

    try:
        while 1:

            path = script_dir+'/images/foo'+str(i)+'.png'
            #im.putpalette(mypalette)
            new_im = Image.new("RGBA", im.size)
            new_im.paste(im)
            #remove bg 
            datas = new_im.getdata()
 
            newData = []

            for item in datas:
                if item[0] == 255 and item[1] == 255 and item[2] == 255:
                    newData.append((255, 255, 255, 0))
                else:
                    newData.append(item)
            new_im.putdata(newData)


            
            new_im.save(path)
            
            print ('Created : '+path)

            i += 1
            im.seek(im.tell() + 1)

    except EOFError:
        pass # end of sequence

def svg_to_gif(svg_file, gif_file, width, height, duration=3000, frames=60):
    
    # Set up a headless Chrome browser
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument('--profile-directory=Default')

   
    chrome_options.add_argument("--user-data-dir=/tmp/chrome-user-data2")

    driver = webdriver.Chrome(options=chrome_options)

    # Create a simple HTML file to display the SVG
    html_content = f"""
    <html>
    <body style="margin:0;padding:0;overflow:hidden;">
        <object data="{my_dict['svg_location'] + svg_file}" width="1920" height="1080"></object>
    </body>
    </html>
    """
    with open('temp.html', 'w') as f:
        f.write(html_content)
    # we are sending html to public address because of permission problems (normally we can use from local folder but it didn't work)
    shutil.copyfile('temp.html', my_dict['main_output'] + 'temp.html')
    # Open the HTML file in the browser
    driver.get(my_dict['svg_location']+"temp.html")
    driver.set_window_size(width, height)

    # Capture frames
    frame_duration = duration / frames
    frame_images = []
    
    #time.sleep(1)
    for _ in range(frames):
        # Capture the current state of the page
        screenshot = driver.get_screenshot_as_base64()
        im = Image.open(BytesIO(base64.b64decode(screenshot)))

        im = im.resize((width, height), Image.LANCZOS)

        frame_images.append(im)
        time.sleep(frame_duration / 1000)  # Wait for next frame

    # Save as GIF
    frame_images[0].save(
        output_dir + gif_file,
        save_all=True,
        append_images=frame_images[1:],
        duration=frame_duration,
        loop=0
    )
    print(gif_file+' Created..')
    
    # Clean up
    driver.quit()
    
    os.remove('temp.html')

def images_to_mp4(output_file,fps,last_duration):
    base_dir = script_dir+'/images'
    
    filenames = next(os.walk(base_dir), (None, None, []))[2]  # [] if no file
    
    file_list_sorted = natsorted(filenames,reverse=False)  # Sort the images
    
    clips = [ImageClip(base_dir+'/'+m).with_duration(0.05)
            for m in file_list_sorted]

    clips.append(ImageClip(base_dir+'/'+file_list_sorted[-1]).with_duration(last_duration))

    concat_clip = concatenate_videoclips(clips, method="compose")
   
    concat_clip.write_videofile(output_file, fps=fps,threads=1, codec="libvpx",bitrate="50000k")

#set alpha videos to main videos
def vdo_with_alpha(lowerThird = None, videoFile=None, outputFile= None):
    tmpVid = cv2.VideoCapture(script_dir+'/'+videoFile)
    framespersecond = float(tmpVid.get(cv2.CAP_PROP_FPS))
    
    video_clip = VideoFileClip(script_dir+'/'+videoFile, target_resolution=(1920,1080))
    
    overlay_clip = VideoFileClip(lowerThird, has_mask=True, target_resolution=(1920,1080))
    overlay_clip = overlay_clip.with_end(video_clip.duration)
    

    final_video = CompositeVideoClip([video_clip, overlay_clip])
    
    final_video.write_videofile(
        script_dir+'/'+outputFile,
        fps=framespersecond,
        remove_temp=True,
        codec="libx264",
        audio_codec="aac",
        threads=6
    )
#for all dynamic areas set the parameters and make them mp4

#this method will create silence sound file for breaks
def createSilencePart(duration):
  silence_seg = AudioSegment.silent(duration=2500) # 1000 for 1 sec, 2000 for 2 secs
  silence_seg.export(audio_output_dir+'silence.wav', format='wav')
  return AudioFileClip(audio_output_dir+'silence.wav')
#this method will create text to speech voice file
def createVoice(text,output):
    #try:

        client = ElevenLabs(
            api_key=my_dict['remote_key'],
        )
        audio_stream = client.text_to_speech.convert_as_stream(
            text=text,
            voice_id="mBUB5zYuPwfVE6DTcEjf",
            model_id="eleven_multilingual_v2"
        )

        # option 1: play the streamed audio locally
        #stream(audio_stream)

        # option 2: process the audio bytes manually
        with open(output, "wb") as binary_file:
            for chunk in audio_stream:
                if isinstance(chunk, bytes):
                    binary_file.write(chunk)
    #except Exception as e:
        #bypass request limit until its accept
     #   print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno), type(e).__name__, e)
     #   createVoice(text,output)

#this method is combile all of them to one mp4 file
def createMovie(output = "output.mp4" , title = 'EXP',date = 'EXP'):

  # video combine
  L = []

  files = [script_dir+"/dogumgunu-video1-edited.mp4",script_dir+"/dogumgunu-video2-edited.mp4",script_dir+"/videos/dogumgunu-video3.mp4"]
  for file in files:
      if os.path.splitext(file)[1] == '.mp4':
          filePath = file
          video = VideoFileClip(filePath)
          L.append(video)

  #create prompts
  createVoice(title,audio_output_dir+'talk1.wav')
  createVoice(date,audio_output_dir+'talk2.wav')


  if not (os.path.isfile(audio_output_dir+'talk3.wav') and os.access(audio_output_dir+'talk3.wav', os.R_OK)):
    createVoice(my_dict['script1'],audio_output_dir+'talk3.wav')
    createVoice(my_dict['script2'],audio_output_dir+'talk4.wav')
    createVoice(my_dict['script3'],audio_output_dir+'talk5.wav')

  #dynamic prompts
  audioclip = AudioFileClip(audio_output_dir+'talk1.wav')
  audioclip = audioclip.with_effects([afx.MultiplyVolume(3)])
  audioclip = concatenate_audioclips([createSilencePart('500'),audioclip])
  new_audioclip = CompositeAudioClip([audioclip])
  L[0].audio   = new_audioclip

  audioclip = AudioFileClip(audio_output_dir+'talk2.wav')
  audioclip = audioclip.with_effects([afx.MultiplyVolume(3)])
  audioclip = concatenate_audioclips([audioclip])
  new_audioclip = CompositeAudioClip([audioclip])
  L[1].audio   = new_audioclip

  #last long prompt with some  slience areas
  audioclip1 = AudioFileClip(audio_output_dir+'talk3.wav')
  audioclip1 = audioclip1.with_effects([afx.MultiplyVolume(3)])
  audioclip2 = AudioFileClip(audio_output_dir+'talk4.wav')
  audioclip2 = audioclip2.with_effects([afx.MultiplyVolume(3)])
  audioclip3 = AudioFileClip(audio_output_dir+'talk5.wav')
  audioclip3 = audioclip3.with_effects([afx.MultiplyVolume(3)])

  audiolast   = concatenate_audioclips([createSilencePart('500'),audioclip1,audioclip2,createSilencePart('1000'),audioclip3])

  new_audioclip = CompositeAudioClip([audiolast])
  L[2].audio   = new_audioclip

  final_clip = concatenate_videoclips(L, method='compose')

  #put music to video
  audioclip = AudioFileClip(audio_output_dir+"dogumgunu-ses.mp3")
  #audioclip = audioclip.subclip(final_clip.start,final_clip.end)
  new_audioclip = CompositeAudioClip([audioclip,final_clip.audio])
  final_clip.audio   = new_audioclip
  final_clip.audio   = new_audioclip.with_duration(final_clip.duration)
  final_clip.write_videofile(output, fps=24, remove_temp=True, audio_codec="aac")

def editSvg(location,key,text):
    #location = os.path.dirname(__file__)+'/'+location
    #read input file
    fin = open(location, "rt")

    #read file contents to string
    data = fin.read()

    #replace all occurrences of the required string
    data = data.replace(key, text)

    #close the input file
    fin.close()

    #open the input file in write mode
    fin = open(location, "wt")

    #overrite the input file with the resulting data
    fin.write(data)

    #close the file
    fin.close()

def updateStatus(d):
    with open(my_dict['json_path'], 'w', encoding='utf8') as f:
        json.dump(d, f, ensure_ascii=False)

def setLockFile(lock = True):
    if lock :
        with open(my_dict['json_path']+'.lock', 'w', encoding='utf8') as f:
            json.dump('{"locked" : "true"}', f, ensure_ascii=False)
    else : 
        os.remove(my_dict['json_path']+'.lock')

def sendErrorMail(detail): 
    port = 587
    smtp_server = "smtp.gmail.com"
    login = "kbhiteam@gmail.com"  
    password = "hrlkynudtcmfhreb"  
                
    sender_email = "kbhiteam@gmail.com"
    receiver_email = "kadir.bozat@talk.com.tr"

    # Plain text content
    text = detail

    # Create MIMEText object
    message = MIMEText(text, "plain")
    message["Subject"] = "Doğum Günü Video Oluşturucusu"
    message["From"] = sender_email
    message["To"] = receiver_email

    # Send the email
    with smtplib.SMTP(smtp_server, port) as server:
        server.starttls()  # Secure the connection
        server.login(login, password)
        server.sendmail(sender_email, receiver_email, message.as_string())
    
     
    message["To"] = 'bilge.bilir@talk.com.tr'

    # Send the email
    with smtplib.SMTP(smtp_server, port) as server:
        server.starttls()  # Secure the connection
        server.login(login, password)
        server.sendmail(sender_email, receiver_email, message.as_string())

#get json file from api folder
with open(my_dict['json_path'],'r') as f:
    d = json.load(f)
    f.close()
    #if new list ready start to creating for persons
    if (d['status'] == 'waiting' or d['status'] == 'preparing') and not os.path.exists(my_dict['json_path']+'.lock'):
        #set lock file 
        print('Cron Started..')
        setLockFile(True)
        
        d['status'] = 'ended' ## if all videos are ended left as it is 
        
        for p in d['personList']:

            if 'status' not in p or p['status'] == 'error':
                #set status as working
                p['status'] = 'preparing'
                d['status'] = 'preparing' # update script list status
                updateStatus(d)
                try:

                    start_time = datetime.datetime.now()
                   
                    

                    p['title'] = p['title'] if 'title' in p else 'Not Setted'
                    p['day']   = p['day'] if 'day'in p else datetime.datetime.today().day # on aydem side of the project check this value for mail sending..
                    p['month'] = p['month'] if 'month'in p else str(datetime.datetime.today().month)

                    if(str(p['day']).startswith("0")): p['day'] = p['day'][1:]

                    print('transactions is started for => '+p['title'])
                    #copy svgs to public location first
                    # we are sending svg files to public address because of permission problems (normally we can use from local folder but it didn't work)
                    titleCopy = my_dict['main_output'] + my_dict['title_svg']
                    dateCopy  = my_dict['main_output'] + my_dict['date_svg']

                    shutil.copyfile(script_dir+'/'+my_dict['title_svg'], titleCopy)
                    shutil.copyfile(script_dir+'/'+my_dict['date_svg'], dateCopy) 
                    
                    #we sended them to public folder so no need to update mail files
                    editSvg(titleCopy,'{title}',p['title'])
                    editSvg(dateCopy,'{day}',p['day'])
                    editSvg(dateCopy,'{month}',p['month'])

                    
                    '''svg_to_gif(my_dict['title_svg'],my_dict['title_svg']+".gif",1920,1080,80)
                    processImage(output_dir+my_dict['title_svg']+".gif")
                    images_to_mp4(output_dir+my_dict['title_svg']+'alpha.webm',60,10)'''

                    
                    '''svg_to_gif(my_dict['date_svg'],my_dict['date_svg']+".gif",1920,1080,80)
                    processImage(output_dir+'/'+my_dict['date_svg']+".gif")
                    images_to_mp4(output_dir+'/'+my_dict['date_svg']+'alpha.webm',60,10)'''

                    #turn svg's to gif then make them alpha video
                    for sv in [my_dict['title_svg'],my_dict['date_svg']]:
                        svg_to_gif(sv,sv+".gif",1920,1080,80)
                        print(output_dir+sv+".gif")
                        processImage(output_dir+sv+".gif")
                        images_to_mp4(output_dir+sv+'alpha.webm',60,10)
                    
                    #merge alpha videos with video parts
                    vdo_with_alpha(output_dir+my_dict['title_svg']+'alpha.webm', "videos/dogumgunu-video1.mp4", "dogumgunu-video1-edited.mp4")
                    vdo_with_alpha(output_dir+my_dict['date_svg']+'alpha.webm', "videos/dogumgunu-video2.mp4", "dogumgunu-video2-edited.mp4")
                    
                    filename =  "output-"+(p['outputCode'] if 'outputCode' in p else str(datetime.datetime.now().strftime('%Y%m%d%H%M%S')))+".mp4"

                    p['filename'] = filename


                    createMovie(
                        my_dict['main_output']+filename ,
                        my_dict['script_title'].replace("{title}",p['title']) , 
                        my_dict['script_date'].replace("{date}",p['day']+' '+p['month']))
                    
                    #update status of json for info
                    end_time = datetime.datetime.now()
                    p['duration'] = str(end_time - start_time)
                    p['status'] = 'ready'
                    #updateStatus(d)
                    
                except Exception as e:
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno), type(e).__name__, e)

                    p['status'] = 'error'
                    updateStatus(d)

                    sendErrorMail(str(e))
                    setLockFile(False)

                break ## always work for only one row and exit  
                
            

        #last 
        #end_time = datetime.datetime.now()
        #d['Duration'] = str(end_time - start_time)
        #write last status to file
        
        updateStatus(d) # change last status as  ended if all list is finished

        #unset lock file
        setLockFile(False)
    else :
        print('Cron Still Locked ....')    

   



