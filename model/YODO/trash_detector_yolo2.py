import time
import cv2
import os
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
parser.add_argument('--threshold', default=0.5, type=float, help='物件認許值 | Default: 0.9')
parser.add_argument('--open_time', default=3, type=float, help='回收桶開啟時間 | Default: 3')
parser.add_argument('--cap_width', default=416, type=float, help='拍攝圖相寬度 | Default: 300')
parser.add_argument('--cap_height', default=416, type=float, help='拍攝圖相高度 | Default: 300')
parser.add_argument('--class_file', default='./config/class_list.txt', type=str, help='物件類別檔 | Default: yolov3.txt')
parser.add_argument('--weight_file', default='./model/trained_stage_1_0110_6997.h5', type=str, help='模組參數檔 | Default: yolov3.weights')
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
detected_times = 3

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

    for classid, pred in result:
        if classid == 0: continue

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
                    # print('Open Gate fro class:', classid)
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

    t = threading.currentThread()
    while getattr(t, "do_run", True):
        try:
            if not open_flag[class_id]:
                continue

            if open_flag[class_id]:
                print("%s" % arg, open_flag[class_id])
                os.system(voice_string)
                # try:
                #     voice.play(voice_record)
                # except KeyboardInterrupt:
                #     voice.stop()

                time.sleep(open_time)
                open_flag[class_id] = False

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
# HOST = "localhost"
server = ThreadedTCPServer((listen_ip, listen_port), ThreadedTCPRequestHandler)
ip, port = server.server_address
server_thread = threading.Thread(target=server.serve_forever)
server_thread.daemon = True
server_thread.start()

print("Ready to accept Client's connect...")
print("Server (IP:PORT)=({}:{})".format(listen_ip,str(listen_port)))

### Initial Audio Player (PyGame)
voice = audio_player()
voice.initMixer()

### yolo model
sess = K.get_session()
classes = yo.load_classes(class_file)
model, ts_parm = yo.build_model(weight_file, config_file, classes)
detected_flag = [False, False, False, False]
detected_cnt = [0, 0, 0, 0]

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

    image = cv2.resize(frame, (cap_width, cap_height), interpolation=cv2.INTER_CUBIC)
    result = trashPredictor(image)

    # time.sleep(0.2) # Take shuttle interval by second

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

### Shutdown Socket Server
server.shutdown()

### Release CAP
cap.release()
cv2.destroyAllWindows()

### Stop Child Process
t.do_run = False
t.join()

### Main Process Stop
print("Process Stopped!!")