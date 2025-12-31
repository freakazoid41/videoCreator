
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
import subprocess
import imageio_ffmpeg
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException
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
import atexit

## sometimes chrome is stays open on server after script teminated for some reason run : pkill -9 chrome : for session clean
## also run rm /var/www/html/dogumgunu.aydemenerji.com.tr/public/birth.json.lock after teminate

script_dir = os.path.dirname(os.path.realpath(__file__))
output_dir = script_dir+'/alphavideos/'
audio_output_dir = script_dir+'/audios/'

with open(script_dir+'/settings.yaml') as f:
    my_dict = yaml.safe_load(f)

# Shared ChromeDriver instance to avoid repeated browser startup costs
_shared_chrome_driver = None

def get_chrome_driver(width=1920, height=1080):
    """Return a shared Chrome WebDriver. Creates it on first use and reuses.
    Caller should not quit the driver; `close_chrome_driver()` will be called at exit.
    """
    global _shared_chrome_driver
    # Try to reuse existing driver
    if _shared_chrome_driver is not None:
        try:
            _shared_chrome_driver.set_window_size(width, height)
            return _shared_chrome_driver
        except Exception:
            try:
                _shared_chrome_driver.quit()
            except Exception:
                pass
            _shared_chrome_driver = None

    # Attempt to create a new driver with retries
    last_exc = None
    attempts = 3
    for attempt in range(1, attempts + 1):
        try:
            chrome_options = Options()
            # modern headless flag; fallback to legacy if needed
            try:
                chrome_options.add_argument('--headless=new')
            except Exception:
                chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--profile-directory=Default')
            chrome_options.add_argument('--user-data-dir=/tmp/chrome-user-data2')
            chrome_options.add_argument(f'--window-size={width},{height}')
            # ensure consistent DPR
            chrome_options.add_argument('--force-device-scale-factor=1')
            chrome_options.add_argument('--high-dpi-support=1')

            _shared_chrome_driver = webdriver.Chrome(options=chrome_options)
            # quick sanity check
            try:
                _shared_chrome_driver.execute_script('return 1')
            except Exception:
                # if execute fails, quit and raise to retry
                try:
                    _shared_chrome_driver.quit()
                except Exception:
                    pass
                _shared_chrome_driver = None
                raise

            _shared_chrome_driver.set_window_size(width, height)
            return _shared_chrome_driver
        except WebDriverException as e:
            last_exc = e
            try:
                writeLog(f'get_chrome_driver attempt {attempt} failed: {str(e)}')
            except Exception:
                pass
            time.sleep(1 * attempt)
            continue
        except Exception as e:
            last_exc = e
            try:
                writeLog(f'get_chrome_driver unexpected error on attempt {attempt}: {str(e)}')
            except Exception:
                pass
            time.sleep(1 * attempt)
            continue

    # If we reach here, all attempts failed
    if last_exc:
        raise last_exc
    raise RuntimeError('Failed to start Chrome WebDriver')

def close_chrome_driver():
    global _shared_chrome_driver
    try:
        if _shared_chrome_driver is not None:
            _shared_chrome_driver.quit()
    except Exception:
        pass
    _shared_chrome_driver = None

# Ensure the shared driver is cleaned up on process exit
atexit.register(close_chrome_driver)

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
            # Convert frame to RGBA and vectorize transparent-white conversion with NumPy
            try:
                import numpy as np
                frame = im.convert('RGBA')
                arr = np.array(frame)
                # mask where RGB == 255 (white)
                mask = (arr[:, :, 0] == 255) & (arr[:, :, 1] == 255) & (arr[:, :, 2] == 255)
                # set alpha to 0 where mask
                arr[mask, 3] = 0
                new_im = Image.fromarray(arr, mode='RGBA')
                new_im.save(path)
            except Exception:
                # Fallback to pure-Pillow per-pixel method if NumPy not available or conversion fails
                new_im = Image.new("RGBA", im.size)
                new_im.paste(im)
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
    try:
        # Set up a headless Chrome browser
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument('--profile-directory=Default')
        chrome_options.add_argument("--user-data-dir=/tmp/chrome-user-data3")
        
        driver = get_chrome_driver(width, height)

        # Create a simple HTML file to display the SVG. Use an absolute file:// URL
        # pointing at the copy we placed in `main_output` so Chrome can load it reliably.
        if my_dict.get('svg_location', '').startswith('http'):
            svg_data = my_dict['svg_location'] + svg_file
        else:
            svg_abs_path = os.path.abspath(os.path.join(my_dict['main_output'], svg_file))
            svg_data = 'file://' + svg_abs_path

        html_content = f"""
        <html>
        <body style="margin:0;padding:0;overflow:hidden;">
            <object data="{svg_data}" width="{width}" height="{height}"></object>
        </body>
        </html>
        """
        with open('temp.html', 'w') as f:
            f.write(html_content)
        # we are sending html to public address because of permission problems (normally we can use from local folder but it didn't work)
        shutil.copyfile('temp.html', my_dict['main_output'] + 'temp.html')
        # Open the HTML file in the browser using a valid URL (file:// for local files)
        # prefer main_output copy if available
        temp_path = os.path.abspath(my_dict['main_output'] + 'temp.html')
        if my_dict.get('svg_location', '').startswith('http'):
            url = my_dict['svg_location'] + "temp.html"
        else:
            url = 'file://' + temp_path
        driver.get(url)
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
        writeLog(gif_file+' Created..')
        
        # Clean up
        # don't quit shared driver here; it will be reused. cleanup registered on exit
        try:
            os.remove('temp.html')
        except Exception:
            pass
    except Exception as e:
        writeLog(f'Error in svg_to_gif for {svg_file}: {str(e)} at line {sys.exc_info()[-1].tb_lineno}')
        raise

def images_to_mp4(output_file, fps, last_duration):
    """Create a video from images using ffmpeg (concat demuxer).

    This avoids MoviePy frame-level loops by writing a temporary concat list
    with per-image durations (default 0.05s per frame) and calling ffmpeg.
    """
    base_dir = os.path.join(script_dir, 'images')

    filenames = next(os.walk(base_dir), (None, None, []))[2]  # [] if no file
    file_list_sorted = natsorted(filenames, reverse=False)

    if not file_list_sorted:
        writeLog('images_to_mp4: no images found in ' + base_dir)
        return

    list_path = os.path.join(base_dir, 'ffmpeg_list.txt')
    image_duration = 0.05

    # Write concat demuxer file
    with open(list_path, 'w', encoding='utf8') as f:
        for name in file_list_sorted[:-1]:
            f.write("file '%s'\n" % os.path.join(base_dir, name))
            f.write("duration %s\n" % (image_duration,))

        last = file_list_sorted[-1]
        f.write("file '%s'\n" % os.path.join(base_dir, last))
        f.write("duration %s\n" % (last_duration,))
        # Per ffmpeg concat demuxer docs, repeat the last file
        f.write("file '%s'\n" % os.path.join(base_dir, last))

    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [
        ffmpeg_exe,
        '-y',
        '-f', 'concat',
        '-safe', '0',
        '-i', list_path,
        '-vsync', 'vfr',
        '-pix_fmt', 'yuva420p',
        '-c:v', 'libvpx',
        '-auto-alt-ref', '0',
        '-b:v', '50000k',
        output_file,
    ]

    try:
        subprocess.run(cmd, check=True)
        writeLog(output_file + ' Created..')
    except subprocess.CalledProcessError as e:
        writeLog('ffmpeg failed: ' + str(e))
        raise
    finally:
        try:
            os.remove(list_path)
        except Exception:
            pass

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
     #   writeLog('Error on line {}'.format(sys.exc_info()[-1].tb_lineno), type(e).__name__, e)
     #   createVoice(text,output)

#this method is combile all of them to one mp4 file
def createMovie(output="output.mp4", title='EXP', date='EXP'):
    files = [
        os.path.join(script_dir, "dogumgunu-video1-edited.mp4"),
        os.path.join(script_dir, "dogumgunu-video2-edited.mp4"),
        os.path.join(script_dir, "videos/dogumgunu-video3.mp4"),
    ]

    # Ensure TTS audio exists
    createVoice(title, os.path.join(audio_output_dir, 'talk1.wav'))
    createVoice(date, os.path.join(audio_output_dir, 'talk2.wav'))

    if not (os.path.isfile(os.path.join(audio_output_dir, 'talk3.wav')) and os.access(os.path.join(audio_output_dir, 'talk3.wav'), os.R_OK)):
        createVoice(my_dict['script1'], os.path.join(audio_output_dir, 'talk3.wav'))
        createVoice(my_dict['script2'], os.path.join(audio_output_dir, 'talk4.wav'))
        createVoice(my_dict['script3'], os.path.join(audio_output_dir, 'talk5.wav'))

    from pydub import AudioSegment

    def _ensure_audio(path):
        if not os.path.isfile(path):
            raise FileNotFoundError(path)
        return AudioSegment.from_file(path)

    s1 = AudioSegment.silent(duration=500) + _ensure_audio(os.path.join(audio_output_dir, 'talk1.wav'))
    s2 = _ensure_audio(os.path.join(audio_output_dir, 'talk2.wav'))
    s3 = (
        AudioSegment.silent(duration=500)
        + _ensure_audio(os.path.join(audio_output_dir, 'talk3.wav'))
        + _ensure_audio(os.path.join(audio_output_dir, 'talk4.wav'))
        + AudioSegment.silent(duration=1000)
        + _ensure_audio(os.path.join(audio_output_dir, 'talk5.wav'))
    )

    # ffmpeg executable
    try:
        import imageio_ffmpeg

        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        ffmpeg_exe = 'ffmpeg'

    def _get_video_duration_seconds(path):
        try:
            out = subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=nw=1:nk=1', path], stderr=subprocess.STDOUT)
            return float(out.strip())
        except Exception:
            return None

    seg_paths = [
        os.path.join(audio_output_dir, 'seg1.wav'),
        os.path.join(audio_output_dir, 'seg2.wav'),
        os.path.join(audio_output_dir, 'seg3.wav'),
    ]

    video_durations = [_get_video_duration_seconds(v) for v in files]

    audios = [s1, s2, s3]
    for idx, aud in enumerate(audios):
        vd = video_durations[idx] if idx < len(video_durations) else None
        if vd is not None:
            target_ms = int(vd * 1000)
            if len(aud) < target_ms:
                aud = aud + AudioSegment.silent(duration=(target_ms - len(aud)))
            elif len(aud) > target_ms:
                aud = aud[:target_ms]
        aud.export(seg_paths[idx], format='wav')

    temp_videos = []
    for idx, (video_in, seg_audio) in enumerate(zip(files, seg_paths)):
        if not os.path.isfile(video_in):
            writeLog('Missing video: ' + video_in)
            continue
        tmp_out = os.path.join(script_dir, f'tmp_segment_{idx+1}.mp4')
        cmd = [
            ffmpeg_exe,
            '-y',
            '-i', video_in,
            '-i', seg_audio,
            '-map', '0:v',
            '-map', '1:a',
            '-c:v', 'copy',
            '-c:a', 'aac',
            '-b:a', '192k',
            tmp_out,
        ]
        subprocess.run(cmd, check=True)
        temp_videos.append(tmp_out)

    # Concatenate segments using MPEG-TS intermediates to avoid timestamp/timebase issues
    ts_files = []
    for tv in temp_videos:
        ts_path = tv + '.ts'
        cmd_ts = [
            ffmpeg_exe,
            '-y',
            '-i', tv,
            '-c', 'copy',
            '-bsf:v', 'h264_mp4toannexb',
            '-f', 'mpegts',
            ts_path,
        ]
        subprocess.run(cmd_ts, check=True)
        ts_files.append(ts_path)

    concat_tmp = os.path.join(script_dir, 'concat_tmp.mp4')
    concat_input = 'concat:' + '|'.join(ts_files)
    cmd_concat = [
        ffmpeg_exe,
        '-y',
        '-i', concat_input,
        '-c', 'copy',
        '-bsf:a', 'aac_adtstoasc',
        concat_tmp,
    ]
    subprocess.run(cmd_concat, check=True)

    # cleanup ts intermediates
    for t in ts_files:
        try:
            os.remove(t)
        except Exception:
            pass

    # Mix with background music if available
    music_path = os.path.join(audio_output_dir, 'dogumgunu-ses.mp3')
    final_out = output
    if os.path.isfile(music_path):
        cmd = [
            ffmpeg_exe,
            '-y',
            '-i', concat_tmp,
            '-i', music_path,
            '-filter_complex', '[0:a]volume=3[a0];[1:a]volume=1[a1];[a0][a1]amix=inputs=2:duration=first:dropout_transition=3[aout]',
            '-map', '0:v',
            '-map', '[aout]',
            '-c:v', 'copy',
            '-c:a', 'aac',
            '-b:a', '192k',
            final_out,
        ]
        subprocess.run(cmd, check=True)
    else:
        shutil.move(concat_tmp, final_out)

    # Cleanup temp files
    for tv in temp_videos:
        try:
            os.remove(tv)
        except Exception:
            pass
    try:
        os.remove(concat_list)
    except Exception:
        pass
    try:
        for p in seg_paths:
            os.remove(p)
    except Exception:
        pass

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
    return True ## temp bypass
    with open(my_dict['json_path'], 'w', encoding='utf8') as f:
        json.dump(d, f, ensure_ascii=False)

def setLockFile(lock = True):
    return True ## temp bypass
    if lock :
        with open(my_dict['json_path']+'.lock', 'w', encoding='utf8') as f:
            json.dump('{"locked" : "true"}', f, ensure_ascii=False)
    else : 
        try:
            os.remove(my_dict['json_path']+'.lock')
        except FileNotFoundError:
            pass

def sendErrorMail(detail): 
    port = 587
    smtp_server = "smtp.gmail.com"
   
    login = "kadir@kontent.com.tr"  # Your login generated by Mailtrap
    password = "tvdgktjybrhmwgjs"  # Your password generated by Mailtrap

    sender_email = "dgunuerror@kontent.com.tr"
    receiver_email = "kadir@kontent.com.tr"

    # Plain text content
    text = detail

    # Create MIMEText object
    message = MIMEText(text, "plain")
    message["Subject"] = "Doğum Günü Video Oluşturucusu"
    message["From"] = sender_email
    message["To"] = receiver_email

    # Send the email to the first recipient
    with smtplib.SMTP(smtp_server, port) as server:
        server.starttls()  # Secure the connection
        server.login(login, password)
        server.sendmail(sender_email, receiver_email, message.as_string())

    # Send to the alternative recipient using a fresh message object
    alt_receiver = 'bilge.bilir@talk.com.tr'
    message2 = MIMEText(text, "plain")
    message2["Subject"] = message["Subject"]
    message2["From"] = sender_email
    message2["To"] = alt_receiver
    with smtplib.SMTP(smtp_server, port) as server:
        server.starttls()
        server.login(login, password)
        server.sendmail(sender_email, alt_receiver, message2.as_string())

def writeLog(message):
    print(str(datetime.datetime.now()) + ' - ' + message + '\n')

#get json file from api folder
with open(my_dict['json_path'],'r') as f:
    d = json.load(f)
    f.close()
    #if new list ready start to creating for persons
    if (d['status'] == 'waiting' or d['status'] == 'preparing') and not os.path.exists(my_dict['json_path']+'.lock'):
        #set lock file 
        writeLog('Cron Started..')
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

                    writeLog('transactions is started for => '+p['title'])
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
                        writeLog(output_dir+sv+".gif")
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
                   

                    p['status'] = 'error'
                    updateStatus(d)

                    sendErrorMail(str(e))
                    setLockFile(False)
                    writeLog(str('Error on line {}'.format(sys.exc_info()[-1].tb_lineno)))

                break ## always work for only one row and exit  
                
            

        #last 
        #end_time = datetime.datetime.now()
        #d['Duration'] = str(end_time - start_time)
        #write last status to file
        
        updateStatus(d) # change last status as  ended if all list is finished

        #unset lock file
        setLockFile(False)
    else :
        writeLog('Cron Still Locked ....')    

   



