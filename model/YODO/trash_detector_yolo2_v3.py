import time
import cv2
# import os
import serial
# from serial import Serial
import argparse
import threading
import socketserver
import pygame
import yolo2_model as yo
from keras import backend as K

cap = cv2.VideoCapture(0)
# cap.set(cv2.CAP_PROP_AUTOFOCUS, 0) # 沒什麼做用
# cap.set(cv2.CAP_PROP_EXPOSURE, -13.0) # 沒什麼做用
# cap.set(cv2.CAP_PROP_FPS, 100) # 沒什麼做用

result = [] # predict result [[0, val], [1, val], [2, val], [3, val]]
open_flag = [False, False, False, False] # class 0/1/2/3

parser = argparse.ArgumentParser(description="Capture Image from Cam dev.0")
parser.add_argument('--listen_ip', default="127.0.0.1", type=str, help='連線位址 | Default: 127.0.0.1')
parser.add_argument('--listen_port', default=7890, type=int, help='連線埠號 | Default: 7890')
parser.add_argument('--class_id', default=1, type=int, help='負責的類別（0/1/2/3） | Default: 1')
parser.add_argument('--threshold', default=0.5, type=float, help='物件認許值 (0-1) | Default: 0.9')
parser.add_argument('--open_time', default=3, type=float, help='回收桶開啟時間 (sec) | Default: 3')
parser.add_argument('--detect_times', default=3, type=int, help=' 物件被連續辨識到次數 | Default: 3')
parser.add_argument('--human_flag', default=True, type=bool, help='是否必須有人出現 (True/False) | Default: True')
parser.add_argument('--flag_duration', default=5, type=float, help='人出現後偵測物件時間 (sec) | Default: 5')
parser.add_argument('--cap_width', default=416, type=float, help='拍攝圖相寬度 (pixel) | Default: 300')
parser.add_argument('--cap_height', default=416, type=float, help='拍攝圖相高度 (pixel | Default: 300')
parser.add_argument('--class_file', default='./config/class_list.txt', type=str, help='物件類別檔 | Default: yolov3.txt')
parser.add_argument('--weight_file', default='./model/trained_stage_1_0116a.h5', type=str, help='模組參數檔 | Default: yolov3.weights')
parser.add_argument('--config_file', default='./config/yolo_anchors.txt', type=str, help='模組設定檔 | Default: yolov3.cfg')

args = parser.parse_args()

listen_ip = args.listen_ip
listen_port = args.listen_port
class_id = args.class_id
threshold = args.threshold
open_time = args.open_time
cap_width = args.cap_width
cap_height = args.cap_height
class_file = args.class_file
weight_file = args.weight_file
config_file = args.config_file
detected_times = args.detect_times
human_flag = args.human_flag
flag_duration = args.flag_duration

print('ARGs: threshold={}, detected_times={}, open_time={}, human_flag={}, duration={}'.format(
    threshold, detected_times, open_time, human_flag, flag_duration))
# print('This machine will handling classid:{} only!'.format(class_id))

cap.set(cv2.CAP_PROP_FRAME_WIDTH, cap_width)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cap_height)

voice_string = None
voice_record = None
if class_id == 1:
    voice_string = 'say 請投入保特瓶回收桶 -r 100'
    voice_record = './voice/voice_Bottle.mp3'
elif class_id == 2:
    voice_string = 'say 請投入鐵鋁罐回收桶 -r 100'
    voice_record = './voice/voice_Metal.mp3'
elif class_id == 3:
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

### Need Put into Real Model
# import random
# def predModel(image):
#     result = []
#     for classid in range(4):
#         pred = random.random()
#         result.append([classid, pred])
#     return(result)

### Predict Object from Captured Image, and Preparing Pred. Result
def trashPredictor(image):
    global sess
    global model
    global ts_parm
    global classes
    global detected_flag
    global detected_cnt
    global detected_times
    global human_flag
    global flag_duration
    global time_start
    global time_stop

    try:
        image.shape
    except:
        return(None)

    # imgHeight, imgWidth, depth = image.shape
    # print("(H W D)=", imgHeight, imgWidth, depth)
    # result = predModel(image)
    time_begin = time.time()
    result = yo.detect_object(sess, model, ts_parm, classes, image)
    time_end = time.time()
    print("Elapse:", time_end-time_begin)
    print(result)

    time_stop = time.time()
    for classid, pred in result:
        if classid == 0:
            if human_flag and pred > threshold:
                time_start = time.time()
                # print('Setting Human been detected time: {}'.format(time_start))
            continue

        if human_flag:
            # print('time_start={}, time_stop={}'.format(time_start, time_stop))
            if time_start == None:
                print('..... No human! Detected object ignoring!')
                break
            if (time_stop-time_start) > flag_duration:
                time_start = None
                print('..... After human been detected over {} seconds! Detected object ignoring!'.format(flag_duration))
                break

        if pred > threshold:
            if not detected_flag[classid]:
                detected_flag[classid] = True
                detected_cnt[classid] = 0

            detected_cnt[classid] += 1
            if detected_cnt[classid] >= detected_times:
                try:
                    detected_flag[classid] = False
                    detected_cnt[classid] = 0
                    open_flag[classid] = True
                    print('........................................ Gate of class: {} was setted'.format(classid))
                except:
                    pass

        else:
            if detected_flag[classid]:
                detected_flag[classid] = False

    return(result)

### Child Process
### mission: Voice and Open Cover
def openCover(arg):
    # global result
    global class_id
    global open_flag
    global mcu
    gate_str = {0:'1', 1:'2', 2:'4'}
    gate_open_flag = None

    t = threading.currentThread()
    while getattr(t, "do_run", True):
        try:
            gate_open_flag = False
            for idx in range(3):
                if open_flag[idx+1]:
                    gate_open_flag = True
                    mcu.write(gate_str[idx].encode("ascii"))
                    print('... Open Gate: {}\n'.format(gate_str[idx]))
                    open_flag[idx+1] = False

            if gate_open_flag:
                time.sleep(open_time)

            # if not open_flag[class_id]:
            #     continue
            #
            # if open_flag[class_id]:
            #     print("Thread: %s" %arg, open_flag[class_id])
            #     print()
            #
            #     ### for MAC play sound
            #     os.system(voice_string)
            #
            #     ### for noneMAC play sound
            #     # try:
            #     #     voice.play(voice_record)
            #     # except KeyboardInterrupt:
            #     #     voice.stop()
            #
            #     time.sleep(open_time)
            #     open_flag[class_id] = False

        except Exception as e:
            pass

    print("Child Process Stopped!")

### Create Child Process
t = threading.Thread(target = openCover, args=("openCover",))
t.start()
print("Child Process Running...")

### Load Light Images
red_light_img = cv2.imread("./image/red.png")
green_light_img = cv2.imread("./image/green.png")

### Define Light Window
window_light = "light"
cv2.namedWindow(window_light, cv2.WND_PROP_FULLSCREEN)
cv2.setWindowProperty(window_light,
                      cv2.WND_PROP_FULLSCREEN,
                      cv2.WINDOW_FULLSCREEN)

### Define Capture Window
window_capture = "Capture"
cv2.namedWindow(window_capture, 0)
cv2.resizeWindow(window_capture, 200, 200)
cv2.moveWindow(window_capture, 0, 0)

### TCP Server
class ThreadedTCPRequestHandler(socketserver.BaseRequestHandler):
    global open_time
    global open_flag

    def handle(self):
        self.cnt = 0
        cur_thread = threading.current_thread()

        print("{}: Client({}) 端連線請求".format(cur_thread,
                                            self.client_address))
        # print("open time:", open_time)
        try:
            self.data = self.request.recv(1024).decode('utf-8')
            if not self.data:
                print("\t 資料收取異常！！連接斷開！！")
            elif self.data[:5] != "Trash":
                response = "DECLINE!!".encode('utf-8')
                self.request.sendall(response)
            else:
                print("{}: Client({}) 端連線成功".format(cur_thread,
                                                    self.client_address))
                response = "CONNECT!!".encode('utf-8')
                self.request.sendall(response)

                self.classid = int(self.data[-1])
                print("This Client will to handle ClassID:", self.classid)
                while True:
                    try:
                        if open_flag[self.classid]:
                            print("Send request to Client(ClassID:{})".format(self.classid))
                            message = "OPEN"
                            self.request.sendall(message.encode('utf-8'))
                            open_flag[self.classid] = False
                            time.sleep(open_time - 1)
                    except Exception as e:
                        open_flag[self.classid] = False
                        print("Send Msg Fail:", e)
                        self.cnt += 1
                        if self.cnt >= 3:
                            break

        except Exception as e:
            print(e)

        finally:
            print("{}: Client({}) 連接斷開".format(cur_thread,
                                               self.client_address))
            self.request.close()

        exit(0)

    def setup(self):
        pass

    def finish(self):
        pass

class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass

### Socket Server
# server = ThreadedTCPServer((listen_ip, listen_port), ThreadedTCPRequestHandler)
# ip, port = server.server_address
# server_thread = threading.Thread(target=server.serve_forever)
# server_thread.daemon = True
# server_thread.start()
#
# print("Ready to accept Client's connect...")
# print("Server (IP:PORT)=({}:{})".format(listen_ip,str(listen_port)))

### Initial Audio Player (PyGame)
# voice = audio_player()
# voice.initMixer()

### Initial COM port
mcu = serial.Serial('COM3', 9600, timeout=0.1)
mcu.write('0'.encode("ascii")) # Say Hello

### yolo model
sess = K.get_session()
classes = yo.load_classes(class_file)
model, ts_parm = yo.build_model(weight_file, config_file, classes)
detected_flag = [False, False, False, False]
detected_cnt = [0, 0, 0, 0]
time_start = None

### Wait a monent
time.sleep(2) # warm-up

### Main Process
print("Start Capture...")
while(True):
    if open_flag[class_id]:
        cv2.imshow(window_light, green_light_img)
    else:
        cv2.imshow(window_light, red_light_img)

    ret, frame = cap.read()
    cv2.imshow(window_capture, frame)

    # print('frame original shape={}'.format(frame.shape))
    image = cv2.resize(frame, (cap_width, cap_height), interpolation=cv2.INTER_CUBIC)
    result = trashPredictor(image)

    # time.sleep(0.2) # Take shuttle interval by second

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

### Shutdown Socket Server
# server.shutdown()

### Release CAP
cap.release()
cv2.destroyAllWindows()

### Stop Child Process
t.do_run = False
t.join()

### Main Process Stop
print("Process Stopped!!")