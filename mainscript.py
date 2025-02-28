
# Importing Required Modules 
import yaml
import sys
from PIL import Image
from PIL import GifImagePlugin
import os
import glob
import cv2
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import base64
from io import BytesIO

from natsort import natsorted
from moviepy import *
from pydub import AudioSegment

from elevenlabs import stream
from elevenlabs.client import ElevenLabs
from elevenlabs import play


output_dir = 'alphavideos/'
audio_output_dir = 'audios/'

with open('settings.yaml') as f:
    my_dict = yaml.safe_load(f)

def processImage(infile):
    try:
        im = Image.open(infile)

        files = glob.glob('images/*')
        for f in files:
            os.remove(f)


    except IOError:
        print ("Cant load", infile)
        sys.exit(1)
    i = 0
    mypalette = im.getpalette()

    try:
        while 1:

            path = 'images/foo'+str(i)+'.png'
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
            


            i += 1
            im.seek(im.tell() + 1)

    except EOFError:
        pass # end of sequence

def svg_to_gif(svg_file, gif_file, width, height, duration=3000, frames=60):
    print(os.path.abspath(svg_file))
    # Set up a headless Chrome browser
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    driver = webdriver.Chrome(options=chrome_options)

    # Create a simple HTML file to display the SVG
    html_content = f"""
    <html>
    <body style="margin:0;padding:0;overflow:hidden;">
        <object data="file:///{os.path.abspath(svg_file)}" width="1920" height="1080"></object>
    </body>
    </html>
    """
    with open('temp.html', 'w') as f:
        f.write(html_content)

    # Open the HTML file in the browser
    driver.get(f"file:///{os.path.abspath('temp.html')}")
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
        gif_file,
        save_all=True,
        append_images=frame_images[1:],
        duration=frame_duration,
        loop=0
    )

    # Clean up
    driver.quit()
    os.remove('temp.html')

def images_to_mp4(output_file,fps,last_duration):
    base_dir = os.path.realpath("images")
    
    filenames = next(os.walk('images'), (None, None, []))[2]  # [] if no file
    
    file_list_sorted = natsorted(filenames,reverse=False)  # Sort the images
    
    clips = [ImageClip('images/'+m).with_duration(0.05)
            for m in file_list_sorted]

    clips.append(ImageClip('images/'+file_list_sorted[-1]).with_duration(last_duration))

    concat_clip = concatenate_videoclips(clips, method="compose")
   
    concat_clip.write_videofile(output_file, fps=fps,threads=1, codec="libvpx",bitrate="50000k")


#set alpha videos to main videos
def vdo_with_alpha(lowerThird = None, videoFile=None, outputFile= None):
    tmpVid = cv2.VideoCapture(videoFile)
    framespersecond = float(tmpVid.get(cv2.CAP_PROP_FPS))
    
    video_clip = VideoFileClip(videoFile, target_resolution=(1920,1080))
    
    overlay_clip = VideoFileClip(lowerThird, has_mask=True, target_resolution=(1920,1080))
    overlay_clip = overlay_clip.with_end(video_clip.duration)
    

    final_video = CompositeVideoClip([video_clip, overlay_clip])
    
    final_video.write_videofile(
        outputFile,
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
  client = ElevenLabs(
    api_key='sk_58e3e1da548bbe910f47743b21a9f0949cdf7e787a943938',
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
#this method is combile all of them to one mp4 file
def createMovie(output = "output.mp4" , title = 'EXP',date = 'EXP'):

  # video combine
  L = []

  files = ["dogumgunu-video1-edited.mp4","dogumgunu-video2-edited.mp4","videos/dogumgunu-video3.mp4"]
  for file in files:
      if os.path.splitext(file)[1] == '.mp4':
          filePath = file
          video = VideoFileClip(filePath)
          L.append(video)

  #create prompts
  createVoice(title,audio_output_dir+'talk1.wav')
  createVoice(date,audio_output_dir+'talk2.wav')
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


for p in [{
            "title" : "Ahmet",
            "month" : "Ocak",
            "day"   : '12'
        },{
            "title" : "Kadir",
            "month" : "Aralık",
            "day"   : '22'
        }]:

    editSvg(my_dict['title_svg'],'{title}',p['title'])
    editSvg(my_dict['date_svg'],'{day}',p['day'])
    editSvg(my_dict['date_svg'],'{month}',p['month'])

    for sv in [my_dict['title_svg']]:
        svg_to_gif(sv, output_dir+'/'+my_dict['title_svg']+".gif",1920,1080,80)
        processImage(output_dir+'/'+my_dict['title_svg']+".gif")
        images_to_mp4(output_dir+'/'+my_dict['title_svg']+'alpha.webm',60,10)

    for sv in [my_dict['date_svg']]:
        svg_to_gif(sv, output_dir+'/'+my_dict['date_svg']+".gif",1920,1080,80)
        processImage(output_dir+'/'+my_dict['date_svg']+".gif")
        images_to_mp4(output_dir+'/'+my_dict['date_svg']+'alpha.webm',60,10)

    editSvg(my_dict['title_svg'],p['title']+'</tspan>','{title}'+'</tspan>')
    editSvg(my_dict['date_svg'],p['day']+'</tspan>','{day}'+'</tspan>')
    editSvg(my_dict['date_svg'],p['month']+'</tspan>','{month}'+'</tspan>')




    vdo_with_alpha(output_dir+'/'+my_dict['title_svg']+'alpha.webm', "videos/dogumgunu-video1.mp4", "dogumgunu-video1-edited.mp4")
    vdo_with_alpha(output_dir+'/'+my_dict['date_svg']+'alpha.webm', "videos/dogumgunu-video2.mp4", "dogumgunu-video2-edited.mp4")

    createMovie("output-"+p['title']+".mp4" , my_dict['script_title'].replace("{title}",p['title']) , my_dict['script_date'].replace("{date}",p['day']+' '+p['month']))

   



