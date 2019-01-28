import socket
import time
import argparse
import os
import cv2
import pygame

parser = argparse.ArgumentParser(description="Capture Image from Cam dev.0")
parser.add_argument('--connect_ip', default="127.0.0.1", type=str, help='連線位址 | Default: 127.0.0.1')
parser.add_argument('--connect_port', default=7890, type=int, help='連線埠號 | Default: 7890')
parser.add_argument('--class_id', default=2, type=int, help='負責的類別（0/1/2） | Default: 2')
parser.add_argument('--open_time', default=3, type=float, help='回收桶開啟時間 | Default: 3')

args = parser.parse_args()

connect_ip = args.connect_ip
connect_port = args.connect_port
class_id = args.class_id
open_time = args.open_time

print("Connect to", connect_ip, connect_port)

voice_string = None
voice_record = None
if class_id == 0:
    voice_string = 'say 請投入保特瓶回收桶 -r 100'
    voice_record = './voice/voice_Bottle.mp3'
elif class_id == 1:
    voice_string = 'say 請投入鐵鋁罐回收桶 -r 100'
    voice_record = './voice/voice_Metal.mp3'
elif class_id == 2:
    voice_string = 'say 請投入紙類回收桶 -r 100'
    voice_record = './voice/voice_Paper_Cup.mp3'

### play audio
class audio_player():
    def __init__(self):
        pass

    def play(self, file):
        pygame.init()
        pygame.mixer.init()

        clock = pygame.time.Clock()
        pygame.mixer.music.load(file)
        pygame.mixer.music.play()

        while pygame.mixer.music.get_busy():
            clock.tick(1000)

    def stop(self):
        pygame.mixer.music.stop()

    def getmixerargs(self):
        pygame.mixer.init()
        freq, size, chan = pygame.mixer.get_init()

        return freq, size, chan

    def initMixer(self):
        BUFFER = 4096

        FREQ, SIZE, CHAN = self.getmixerargs()
        pygame.mixer.init(FREQ, SIZE, CHAN, BUFFER)

# open_flag = False
red_light_img = cv2.imread("./image/red.png")
green_light_img = cv2.imread("./image/green.png")

### Define Light Window
window_light = "light"
cv2.namedWindow(window_light, cv2.WND_PROP_FULLSCREEN)
cv2.setWindowProperty(window_light,
                      cv2.WND_PROP_FULLSCREEN,
                      cv2.WINDOW_FULLSCREEN)

### Socket connect
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((connect_ip, connect_port))

def light_shower(open_flag):
    if open_flag:
        cv2.imshow(window_light, green_light_img)
    else:
        cv2.imshow(window_light, red_light_img)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        cv2.destroyAllWindows()

### Main process
try:
    ### Initial Audio Player (PyGame)
    voice = audio_player()
    voice.initMixer()

    message = "Trash: {}".format(class_id)
    print('Message [{}] send to Server!'.format(message))
    s.send(message.encode('utf-8'))

    data = s.recv(1024).decode('utf-8')
    print(data)

    if data == "CONNECT!!":
        print("This Client will deal with ClassID:", class_id)
        try:
            while True:
                data = s.recv(1024).decode('utf-8')
                if data == "OPEN":
                    print("Received 'OPEN' instruction！")
                    light_shower(True)

                    ### for MAC play sound
                    os.system(voice_string)

                    ### for noneMAC play sound
                    # try:
                    #     voice.play(voice_record)
                    # except KeyboardInterrupt:
                    #     voice.stop()

                    print('..... Gate will open {} seconds'.format(open_time))
                    time.sleep(open_time)
                    light_shower(False)

        except Exception as e:
            print(e)

except Exception as e:
    print(e)

s.close()
cv2.destroyAllWindows()

print("Process Stop!")