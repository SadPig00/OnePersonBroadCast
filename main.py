import time
import numpy as np
import cv2
import tkinter
import sys, os
import Config
import threading

from Dialog import rtsp_dialog
from Dialog import set_Channel
from datetime import datetime
from PyQt5 import uic
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import requests

#global ch_frame
global main1_frame
global main2_frame
global main3_frame
main1_frame = None
main2_frame = None
main3_frame = None
#global opencv_key
#global isClose
#ch_frame = [None,None,None]
#opencv_key = None
#isClose = False
global pitchInfo
global config_width
global config_height
global video_fps
global monit_fps

config_width = int(Config.config['PROGRAM']['width'])
config_height  = int(Config.config['PROGRAM']['height'])
video_fps = int(Config.config['PROGRAM']['video_fps'])
monit_fps = int(Config.config['PROGRAM']['monit_fps'])

pitchInfo = None
global isExe
isExe = Config.config['PROGRAM']['isExe'] == 'true'

# TODO : ABS 서버에서 스트라이크 좌표 가져오는 쓰레드 함수
class GetPitchInfo(QThread):
    def __init__(self,parent):
        super().__init__()
        self.working = True
        self.parent = parent
    def run(self):
        global pitchInfo
        pitch_temp = None
        abs_start_time = 0
        while self.working:
            try:
                for i in self.parent.isABS.keys():
                    if self.parent.isABS[i]:
                        response = requests.get(url=Config.config['REQUEST']['uri'], timeout=1)
                        data = response.json()
                        if 'box_bottom' in data.keys():
                            # TODO : 공 좌표 받은 이후 4초간 데이터 변동 없으면 좌표 표출 X
                            if data != pitch_temp:
                                QThread.msleep(int(Config.config['ABS']['mtime_delay'])) # RTSP 서버와의 딜레이 조정
                                pitchInfo = data
                                pitch_temp = data
                                abs_start_time = time.time()
                            elif time.time() - abs_start_time > float(Config.config['ABS']['ball_reset_time']):
                                abs_start_time = 0
                                pitchInfo = None

                        if 'error' in data.keys():
                            pitchInfo = None
                        break
                QThread.msleep(100)
            except Exception as e:
                pitchInfo = None
                print(f"request fail :: {e}")

    def stop(self):
        self.working = False
        self.quit()
        self.wait(2000)
"""
def getPitchInfo():
    global pitchInfo
    while True:
        try:
            response = requests.get(url=Config.config['REQUEST']['uri'],timeout=2)
            data = response.json()

            if 'box_bottom' in data.keys():
                pitchInfo = data
            if 'error' in data.keys():
                pitchInfo = None
            time.sleep(0.1)
        except Exception as e:
            print(f"request fail :: {e}")
"""

# TODO : 좌표 알아내는 핸들러 (현재 미사용)
def mouse_handler(event, x, y, flags, param):  # 마우스로 좌표 알아내기
    if flags == cv2.EVENT_FLAG_LBUTTON:
        clicked = [x, y]

        global crop_x
        global crop_y

        heigt, width, _ = param.shape

        if x - int(width / 8) > 0 and x + int(width / 8) <= 1280 and y - int(heigt / 8) > 0 and y + int(heigt / 8) <= 720:
            crop_x = x
            crop_y = y


# TODO : RTSP 서버 연결 스레드
class rtsp_worker(QThread):
    update_frame = pyqtSignal(np.ndarray, str,int)  # 프레임 업데이트 시그널

    def __init__(self, parent, url, name):
        super().__init__(parent)
        self.parent = parent
        self.url = url
        self.name = name
        self.working = True

    def run(self):
        global video_fps
        try:
            cap = cv2.VideoCapture(self.url)
            frame_count = 0
            crop_frame_count = 1

            while cap.isOpened() and self.working:

                ret, frame = cap.read()

                if not ret:
                    # TODO : 인터넷 속도 문제로 RTSP 서버 끊겼을시 재접속
                    frame_count += 1
                    if frame_count == 1000:
                        cap = cv2.VideoCapture(self.url)
                        frame_count = 0
                        crop_frame_count = 1

                    continue

                crop_frame_count += 1
                if crop_frame_count == video_fps+1:
                    crop_frame_count = 1

                self.update_frame.emit(frame, self.name,crop_frame_count)

                #QThread.msleep(1)


            cap.release()
        except Exception as e:
            print(f"RTSP Server Run Error :: {e}")
            if self.name == 'first':
                QMessageBox.about(self, "RTSP Connect Error", "First RTSP Server Not Connect")
            if self.name == 'second':
                QMessageBox.about(self, "RTSP Connect Error", "Second RTSP Server Not Connect")
            if self.name == 'third':
                QMessageBox.about(self, "RTSP Connect Error", "Third RTSP Server Not Connect")
            self.stop()

    def stop(self):
        self.working = False
        self.quit()
        self.wait(2000)

# TODO : crop 이미지 스레드 ( 현재 미사용 )
"""
class CropUpdateThread(QThread):
    update_pixmap_signal = pyqtSignal(QImage,str)

    def __init__(self, parent, rtsp_name, rect_point,ch):
        super().__init__()
        self.rtsp_name = rtsp_name
        self.rect_point = rect_point
        self.working = True
        self.ch = ch
        self.parent = parent


    def run(self):

        global ch_frame
        crop_x, crop_y, crop_width, crop_height = self.rect_point

        while self.working:
            try:
                # TODO : 갱신되는 main1, main2 이미지를 받아 crop 이미지로 변환 (원본 비율에 맞춤 )
                #if self.rtsp_name == 'First RTSP' and ch_frame[0] != None and ch_frame[12] != None:
                if self.rtsp_name == 'First RTSP' and ch_frame[0] != None:

                    # TODO : 해당 채널의 원본비율 넓이 높이 저장
                    width_rate = self.parent.ch_rect['RTSP_1'][2] / self.parent.main_screen_width
                    height_rate = self.parent.ch_rect['RTSP_1'][3] / self.parent.main_screen_height

                    # TODO : 원본 비율을 계산한 x,y,width,height
                    self.parent.ch_rect[self.ch] = [round(crop_x * width_rate), round(crop_y * height_rate), round(crop_width * width_rate), round(crop_height * height_rate),'ch1']
                    #frame = self.parent.main1.pixmap().copy(crop_x, crop_y,crop_width , crop_height )
                    frame = ch_frame[0].scaled(self.parent.main_screen_width,self.parent.main_screen_height).copy(crop_x, crop_y, crop_width, crop_height)

                #elif self.rtsp_name == 'Second RTSP' and ch_frame[1] != None and ch_frame[13] != None:
                elif self.rtsp_name == 'Second RTSP' and ch_frame[1] != None:

                    # TODO : 해당 채널의 원본비율 넓이 높이 저장
                    width_rate = self.parent.ch_rect['RTSP_2'][2] / self.parent.main_screen_width
                    height_rate = self.parent.ch_rect['RTSP_2'][3] / self.parent.main_screen_height

                    # TODO : 원본 비율을 계산한 x,y,width,height
                    self.parent.ch_rect[self.ch] = [round(crop_x * width_rate), round(crop_y * height_rate),round(crop_width * width_rate), round(crop_height * height_rate),'ch2']
                    #frame = self.parent.main2.pixmap().copy(crop_x, crop_y,crop_width , crop_height )
                    frame = ch_frame[1].scaled(self.parent.main_screen_width, self.parent.main_screen_height).copy(crop_x, crop_y, crop_width, crop_height)

                elif self.rtsp_name == 'Third RTSP' and ch_frame[2] != None:

                    # TODO : 해당 채널의 원본비율 넓이 높이 저장
                    width_rate = self.parent.ch_rect['RTSP_3'][2] / self.parent.main_screen_width
                    height_rate = self.parent.ch_rect['RTSP_3'][3] / self.parent.main_screen_height

                    # TODO : 원본 비율을 계산한 x,y,width,height
                    self.parent.ch_rect[self.ch] = [round(crop_x * width_rate), round(crop_y * height_rate),round(crop_width * width_rate), round(crop_height * height_rate),'ch2']
                    #frame = self.parent.main2.pixmap().copy(crop_x, crop_y,crop_width , crop_height )
                    frame = ch_frame[2].scaled(self.parent.main_screen_width, self.parent.main_screen_height).copy(crop_x, crop_y, crop_width, crop_height)

                else:
                    continue


                frame = frame.toImage()

                self.update_pixmap_signal.emit(frame,self.ch)

                # TODO : 쓰레드 자원관리를 위해 ms 타임 걸어둠 ( 약 3프레임 )
                QThread.msleep(333)
                #QThread.msleep(1)


            except Exception as e :
                print(f"crop 스레드 오류 :: {e}")
                break

    def stop(self):
        self.working = False
        self.quit()
        self.wait(2000)
"""
# TODO : OBS( 방송화면 ) 출력용 모니터 스레드
class MonitThread(QThread):
    update_monit_frame = pyqtSignal(QImage,bool)

    def __init__(self,channel_rect,ch, isABS):
        super().__init__()
        self.working = True
        self.channel_rect = channel_rect
        self.ch = ch
        self.isABS = isABS
    def run(self):
        #global ch_frame
        global main1_frame
        global main2_frame
        global main3_frame

        global config_width
        global config_height

        while self.working:

            if self.ch == 'RTSP_1':
                frame = main1_frame.copy(self.channel_rect[0], self.channel_rect[1], self.channel_rect[2], self.channel_rect[3]).scaled(config_width,config_height)
            if self.ch == 'RTSP_2':
                frame = main2_frame.copy(self.channel_rect[0], self.channel_rect[1], self.channel_rect[2],self.channel_rect[3]).scaled(config_width,config_height)
            if self.ch == 'RTSP_3':
                frame = main3_frame.copy(self.channel_rect[0], self.channel_rect[1], self.channel_rect[2],self.channel_rect[3]).scaled(config_width,config_height)

            frame = frame.toImage()

            self.update_monit_frame.emit(frame,self.isABS)

            QThread.msleep(1)
    def change_channel_rect(self,channel_rect,ch, isABS):
        self.channel_rect = channel_rect
        self.ch = ch
        self.isABS = isABS

    def stop(self):
        self.working = False
        self.quit()
        self.wait(2000)

if isExe:
    form_class = uic.loadUiType(f"{os.path.dirname(__file__)}\\UI\\BroadCast.ui")[0]
    monit_class = uic.loadUiType(f"{os.path.dirname(__file__)}\\UI\\monit_widget.ui")[0]

if not isExe:
    form_class = uic.loadUiType('./UI/BroadCast.ui')[0]
    monit_class = uic.loadUiType('./UI/monit_widget.ui')[0]


# TODO : OBS ( 방송출력 ) 화면 Class
class MonitClass(QWidget,monit_class):
    def __init__(self):
        global isExe
        global config_width
        global config_height

        super().__init__()
        self.setupUi(self)
        #self.monit_label.setGeometry(0,0,1280,720)
        self.resize(config_width, config_height)
        self.setFixedSize(self.width(),self.height())
        self.monit_label.setGeometry(0, 0, config_width, config_height)
        if isExe:
            self.monit_label.setPixmap(QPixmap(f"{os.path.dirname(__file__)}\\Assets\\no-signal-icon-black.jpg"))
        if not isExe:
            self.monit_label.setPixmap(QPixmap('./Assets/no-signal-icon-black.jpg'))
        #self.setGeometry(-1281,-721,1280,720)
        self.setGeometry(-(config_width+1), -(config_height-1), config_width, config_height)
        self.setWindowFlags(Qt.FramelessWindowHint)
        #self.setCursor(QCursor(Qt.BlankCursor))
        self.setWindowOpacity(0)
        self.show()

# TODO : main 화면 Class
class WindowClass(QMainWindow, form_class):
    def __init__(self):
        global isExe
        global config_width
        global config_height

        super().__init__()
        self.window_width = tkinter.Tk().winfo_screenwidth()
        self.window_height = tkinter.Tk().winfo_screenheight()
        self.setupUi(self)

        self.resize(round(self.window_width*0.8), round(self.window_height*0.8))
        self.rtsp_num = int(Config.config['RTSP']['rtsp_num'])
        # TODO : selected color :: rgb(253, 8, 8) // no selected color :: rgb(190, 190, 190);
        self.selected_color="border : 2px solid rgb(253,8,8)"
        self.no_selected_color="border : 2px solid rgb(190, 190, 190)"

        #self.main1.resize(100, 10)
        # TODO : 영상 화면 비율 16:9
        self.rate = 16 / 9

        # TODO : 초기 RTSP 서버 초기값 None
        self.first_rtsp = Config.config['RTSP']['first_rtsp']
        self.second_rtsp = Config.config['RTSP']['second_rtsp']
        self.third_rtsp = Config.config['RTSP']['third_rtsp']

        # TODO : rtsp 스레드 초기 선언
        self.rtsp_worker1 = None
        self.rtsp_worker2 = None
        self.rtsp_worker3 = None

        # TODO : frame 없을때 기본 이미지 설정
        if isExe:
            self.noSignalImage = QPixmap(f"{os.path.dirname(__file__)}\\Assets\\no-signal-icon-black.jpg")
            self.setWindowIcon(QIcon(f"{os.path.dirname(__file__)}\\icon.ico"))
        if not isExe:
            self.noSignalImage = QPixmap('./Assets/no-signal-icon-black.jpg')
            self.setWindowIcon(QIcon(f"{os.path.dirname(__file__)}\\Assets\\icon.ico"))



        # TODO : 이미지 사이즈 사용자의 모니터 사이즈에 맞춰 16:9 비율로 설정
        if self.rtsp_num == 2 :

            self.main_screen_width = round(self.window_width / 2.15)
            self.main_screen_height = round(self.main_screen_width / self.rate)
            """
            self.main_screen_height = round(self.window_height/2.5)
            self.main_screen_width = round(self.main_screen_height * self.rate)
            """
            # TODO : main rtsp 채널 초기 이미지 셋팅
            self.main3.deleteLater()
            self.main3_label.deleteLater()
            self.main3_layout.deleteLater()
            self.actionSet_Third_RTSP.deleteLater()
            self.actionSelect_Third_RTSP.deleteLater()
            self.actionRun_Third_RTSP_Server.deleteLater()
            self.actionRun_ABS_RTSP_3.deleteLater()
            self.actionStop_Third_RTSP_Server.deleteLater()
            self.actionStop_ABS_RTSP_3.deleteLater()

            self.main_noSignalImage = self.noSignalImage.scaled(self.main_screen_width, self.main_screen_height)
            self.main1.setPixmap(self.main_noSignalImage)
            self.main2.setPixmap(self.main_noSignalImage)

        if self.rtsp_num == 3:
            self.main_screen_width = round(self.window_width / 3)
            self.main_screen_height = round(self.main_screen_width / self.rate)

            # TODO : main rtsp 채널 초기 이미지 셋팅
            self.main_noSignalImage = self.noSignalImage.scaled(self.main_screen_width, self.main_screen_height)
            self.main1.setPixmap(self.main_noSignalImage)
            self.main2.setPixmap(self.main_noSignalImage)
            self.main3.setPixmap(self.main_noSignalImage)
        #self.main_screen_width = round(self.width() / 2)

        # TODO : PIP 모니터 화면 크기 설정 및 초기 이미지 선언
        #self.sub_screen_width = round(self.main_screen_width / 2)
        self.sub_screen_width = round(self.window_width / 5.1)
        self.sub_screen_height = round(self.sub_screen_width / self.rate)
        self.sub_noSignalImage = self.noSignalImage.scaled(self.sub_screen_width, self.sub_screen_height)

        # TODO : CH list 선언
        if self.rtsp_num == 2:
            self.channel_list = [self.main1, self.main2, self.ch1, self.ch2, self.ch3, self.ch4, self.ch5,
                                 self.ch6, self.ch7, self.ch8, self.ch9, self.ch10]
        if self.rtsp_num == 3:
            self.channel_list = [self.main1, self.main2, self.main3, self.ch1, self.ch2, self.ch3, self.ch4, self.ch5, self.ch6, self.ch7, self.ch8, self.ch9, self.ch10]

        # TODO : crop 스레드 관리를 위한 dict, 화면 표출을 위한 dict
        #self.crop_update_thread = {'ch1':None,'ch2':None,'ch3':None,'ch4':None,'ch5':None,'ch6':None,'ch7':None,'ch8':None,'ch9':None,'ch10':None}
        if self.rtsp_num == 2:
            self.ch_rect = {'RTSP_1':None,'RTSP_2':None,'ch1': None, 'ch2': None, 'ch3': None, 'ch4': None, 'ch5': None, 'ch6': None,'ch7': None, 'ch8': None, 'ch9': None, 'ch10': None}
        elif self.rtsp_num == 3:
            self.ch_rect = {'RTSP_1': None, 'RTSP_2': None, 'RTSP_3': None, 'ch1': None, 'ch2': None, 'ch3': None, 'ch4': None,
                            'ch5': None, 'ch6': None, 'ch7': None, 'ch8': None, 'ch9': None, 'ch10':None}

        # TODO : RTSP에서 들어오는 이미지의 비율은 16:9 비율로 특정, 이미지 크기가 커지면 PIP 화면 크롭시 화면에 가득찰수가 있어서 1280x720으로 변환 해주기 위한 resize 필요
        # TODO : 해당 resize시 원본과 resize된 비율을 가지고 있어야됨.
        self.crop_ch_rect = {"RTSP_1":[None,None],"RTSP_2":[None,None],"RTSP_3":[None,None]}

        # TODO : 하위 (crop) 채널 초기 이미지 셋팅
        self.ch1.setPixmap(self.sub_noSignalImage)
        self.ch2.setPixmap(self.sub_noSignalImage)
        self.ch3.setPixmap(self.sub_noSignalImage)
        self.ch4.setPixmap(self.sub_noSignalImage)
        self.ch5.setPixmap(self.sub_noSignalImage)
        self.ch6.setPixmap(self.sub_noSignalImage)
        self.ch7.setPixmap(self.sub_noSignalImage)
        self.ch8.setPixmap(self.sub_noSignalImage)
        self.ch9.setPixmap(self.sub_noSignalImage)
        self.ch10.setPixmap(self.sub_noSignalImage)

        # TODO : Menu 버튼의 RTSP 설정 버튼 slot 설정
        self.actionSet_first_RTSP.triggered.connect(lambda : self.getRtsp('First RTSP'))
        self.actionSet_Second_RTSP.triggered.connect(lambda: self.getRtsp('Second RTSP'))
        self.actionSet_Third_RTSP.triggered.connect(lambda: self.getRtsp('Third RTSP'))

        # TODO : Menu 버튼의 RTSP 실행 버튼 slot 설정
        self.actionRun_First_RTSP_Server.triggered.connect(self.run_first_rtsp)
        self.actionRun_Second_RTSP_Server.triggered.connect(self.run_second_rtsp)
        self.actionRun_Third_RTSP_Server.triggered.connect(self.run_third_rtsp)

        # TODO : Menu 버튼의 Screen 설정
        self.actionFull_Screen.triggered.connect(self.showFullScreen)
        self.actionMax_size_Screen.triggered.connect(self.showMaximized)
        self.actionQuit_q.triggered.connect(self.close)


        # TODO : Menu 버튼의 channel 설정
        self.actionSelect_first_RTSP.triggered.connect(lambda :self.getChannelSetting(rtsp_name="First RTSP"))
        self.actionSelect_Second_RTSP.triggered.connect(lambda: self.getChannelSetting(rtsp_name="Second RTSP"))
        self.actionSelect_Third_RTSP.triggered.connect(lambda: self.getChannelSetting(rtsp_name="Third RTSP"))

        # TODO : Menu 버튼의 RTSP 갯수 설정
        self.Set2RTSP.triggered.connect(lambda :self.setRTSP_Number(rtsp_number=2))
        self.Set3RTSP.triggered.connect(lambda: self.setRTSP_Number(rtsp_number=3))

        # TODO : Menu 버튼의 ShortCut Key 뷰
        shortCut_Key_box = QMessageBox()
        #shortCut_Key_box.setMinimumWidth(20031)
        self.actionView_ShortCut_Key.triggered.connect(lambda :
                                                       shortCut_Key_box.about(self,"ShortCut Key",f"RTSP_1 : Ins                                        ."
                                                                                  f"\nRTSP_2 : Home\nRTSP_3 : PgUp\n"
                                                                                  f"CH1 : 1\nCH2 : 2\nCH3 : 3\nCH4 : 4\n"
                                                                                  f"CH5 : 5\nCH6 : 6\nCH7 : 7\nCH8 : 8\n"
                                                                                  f"CH9 : 9\nCH10 : 0"))

        # TODO : Menu 버튼의 stop RTSP 클릭 이벤트
        self.actionStop_First_RTSP_Server.triggered.connect(lambda :self.stop_rtsp(name='first'))
        self.actionStop_Second_RTSP_Server.triggered.connect(lambda: self.stop_rtsp(name='second'))
        self.actionStop_Third_RTSP_Server.triggered.connect(lambda: self.stop_rtsp(name='third'))


        # TODO : Menu 버튼의 stop CH 클릭 이벤트
        self.actionStop_CH_1.triggered.connect(lambda : self.stop_ch(ch='ch1'))
        self.actionStop_CH_2.triggered.connect(lambda: self.stop_ch(ch='ch2'))
        self.actionStop_CH_3.triggered.connect(lambda: self.stop_ch(ch='ch3'))
        self.actionStop_CH_4.triggered.connect(lambda: self.stop_ch(ch='ch4'))
        self.actionStop_CH_5.triggered.connect(lambda: self.stop_ch(ch='ch5'))
        self.actionStop_CH_6.triggered.connect(lambda: self.stop_ch(ch='ch6'))
        self.actionStop_CH_7.triggered.connect(lambda: self.stop_ch(ch='ch7'))
        self.actionStop_CH_8.triggered.connect(lambda: self.stop_ch(ch='ch8'))
        self.actionStop_CH_9.triggered.connect(lambda : self.stop_ch(ch='ch9'))
        self.actionStop_CH_10.triggered.connect(lambda: self.stop_ch(ch='ch10'))


        # TODO : ABS 송출을 위한 스트라이크존 ( 방송 출력 모니터 비율에 맞춰 scaled )
        self.strike_zone = QPixmap(f"{os.path.dirname(__file__)}\\Assets\\strikeZone.png")
        strike_zone_width = self.strike_zone.width()
        strike_zone_height = self.strike_zone.height()
        # 출력 영상의 (100 /3.2)% 비율로 사이즈 조정
        resize_rate = config_height / 3.2 / strike_zone_height
        self.strike_zone = self.strike_zone.scaled(round(strike_zone_width * resize_rate),round(strike_zone_height * resize_rate))

        strike_zone_width = self.strike_zone.width()
        strike_zone_height = self.strike_zone.height()

        # 스트라이크 존 이미지 우측과 하단을 영상에서 띄어놓음
        self.strike_zone_image_x = config_width - round(strike_zone_width + (config_width * 0.02)) # 스트라이크존 전체 이미지 좌상단 x
        self.strike_zone_image_y = config_height - round(strike_zone_height + (config_height * 0.03)) # 스트라이크존 전체 이미지 좌상단 y

        # start x,y (40,40) // end x,y (100, 130)   :: rate start x,y ( (width * 40/140), (height*40/240) ) end x,y ( (width * 100/140), (height*130/240) )
        # TODO : ABS config 설정
        self.ball_size = round(int(Config.config['ABS']['ball_size'])*(config_width/1920))
        self.zone_width = int(Config.config['ABS']['zone_width'])

        self.strike_zone_start_x = self.strike_zone_image_x + round(strike_zone_width * 40 / 140) - int(self.ball_size/2) # 실질적인 스트라이크존 좌상단 x
        self.strike_zone_start_y = self.strike_zone_image_y + round(strike_zone_height * 40 / 240) - int(self.ball_size/2) # 실질적인 스트라이크존 좌상단 y
        self.strike_zone_end_x = self.strike_zone_image_x +round(strike_zone_width * 100 / 140) - int(self.ball_size/2) # 실질적인 스트라이크존 우하단 x
        self.strike_zone_end_y = self.strike_zone_image_y + round(strike_zone_height * 130 / 240) - int(self.ball_size/2) # 실질적인 스트라이크존 우하단 y

        self.km_start_x = self.strike_zone_image_x
        self.km_start_y = self.strike_zone_image_y + round(strike_zone_height * (21/24))

        # TODO : ABS 송출을 위한 isABS 값 초기 설정
        if self.rtsp_num == 2:
            self.isABS = {'RTSP_1': False, 'RTSP_2': False, 'ch1': False, 'ch2': False, 'ch3': False, 'ch4': False,
                            'ch5': False, 'ch6': False, 'ch7': False, 'ch8': False, 'ch9': False, 'ch10': False}

        elif self.rtsp_num == 3:
            self.isABS = {'RTSP_1': False, 'RTSP_2': False, 'RTSP_3': False, 'ch1': False, 'ch2': False, 'ch3': False,
                            'ch4': False,'ch5': False, 'ch6': False, 'ch7': False, 'ch8': False, 'ch9': False, 'ch10': False}

        # TODO : Menu ABS run 버튼 클릭
        if self.rtsp_num == 2:
            self.actionRun_ABS_RTSP_1.triggered.connect(lambda : self.setIsABS(name='RTSP_1',onABS=True))
            self.actionRun_ABS_RTSP_2.triggered.connect(lambda: self.setIsABS(name='RTSP_2', onABS=True))
            self.actionRun_ABS_CH_1.triggered.connect(lambda: self.setIsABS(name='ch1', onABS=True))
            self.actionRun_ABS_CH_2.triggered.connect(lambda: self.setIsABS(name='ch2', onABS=True))
            self.actionRun_ABS_CH_3.triggered.connect(lambda: self.setIsABS(name='ch3', onABS=True))
            self.actionRun_ABS_CH_4.triggered.connect(lambda: self.setIsABS(name='ch4', onABS=True))
            self.actionRun_ABS_CH_5.triggered.connect(lambda: self.setIsABS(name='ch5', onABS=True))
            self.actionRun_ABS_CH_6.triggered.connect(lambda: self.setIsABS(name='ch6', onABS=True))
            self.actionRun_ABS_CH_7.triggered.connect(lambda: self.setIsABS(name='ch7', onABS=True))
            self.actionRun_ABS_CH_8.triggered.connect(lambda: self.setIsABS(name='ch8', onABS=True))
            self.actionRun_ABS_CH_9.triggered.connect(lambda: self.setIsABS(name='ch9', onABS=True))
            self.actionRun_ABS_CH_10.triggered.connect(lambda: self.setIsABS(name='ch10', onABS=True))
        elif self.rtsp_num == 3:
            self.actionRun_ABS_RTSP_1.triggered.connect(lambda: self.setIsABS(name='RTSP_1', onABS=True))
            self.actionRun_ABS_RTSP_2.triggered.connect(lambda: self.setIsABS(name='RTSP_2', onABS=True))
            self.actionRun_ABS_RTSP_3.triggered.connect(lambda: self.setIsABS(name='RTSP_3', onABS=True))
            self.actionRun_ABS_CH_1.triggered.connect(lambda: self.setIsABS(name='ch1', onABS=True))
            self.actionRun_ABS_CH_2.triggered.connect(lambda: self.setIsABS(name='ch2', onABS=True))
            self.actionRun_ABS_CH_3.triggered.connect(lambda: self.setIsABS(name='ch3', onABS=True))
            self.actionRun_ABS_CH_4.triggered.connect(lambda: self.setIsABS(name='ch4', onABS=True))
            self.actionRun_ABS_CH_5.triggered.connect(lambda: self.setIsABS(name='ch5', onABS=True))
            self.actionRun_ABS_CH_6.triggered.connect(lambda: self.setIsABS(name='ch6', onABS=True))
            self.actionRun_ABS_CH_7.triggered.connect(lambda: self.setIsABS(name='ch7', onABS=True))
            self.actionRun_ABS_CH_8.triggered.connect(lambda: self.setIsABS(name='ch8', onABS=True))
            self.actionRun_ABS_CH_9.triggered.connect(lambda: self.setIsABS(name='ch9', onABS=True))
            self.actionRun_ABS_CH_10.triggered.connect(lambda: self.setIsABS(name='ch10', onABS=True))

        # TODO : Menu ABS stop 버튼 클릭
        if self.rtsp_num == 2:
            self.actionStop_ABS_RTSP_1.triggered.connect(lambda : self.setIsABS(name='RTSP_1',onABS=False))
            self.actionStop_ABS_RTSP_2.triggered.connect(lambda: self.setIsABS(name='RTSP_2', onABS=False))
            self.actionStop_ABS_CH_1.triggered.connect(lambda: self.setIsABS(name='ch1', onABS=False))
            self.actionStop_ABS_CH_2.triggered.connect(lambda: self.setIsABS(name='ch2', onABS=False))
            self.actionStop_ABS_CH_3.triggered.connect(lambda: self.setIsABS(name='ch3', onABS=False))
            self.actionStop_ABS_CH_4.triggered.connect(lambda: self.setIsABS(name='ch4', onABS=False))
            self.actionStop_ABS_CH_5.triggered.connect(lambda: self.setIsABS(name='ch5', onABS=False))
            self.actionStop_ABS_CH_6.triggered.connect(lambda: self.setIsABS(name='ch6', onABS=False))
            self.actionStop_ABS_CH_7.triggered.connect(lambda: self.setIsABS(name='ch7', onABS=False))
            self.actionStop_ABS_CH_8.triggered.connect(lambda: self.setIsABS(name='ch8', onABS=False))
            self.actionStop_ABS_CH_9.triggered.connect(lambda: self.setIsABS(name='ch9', onABS=False))
            self.actionStop_ABS_CH_10.triggered.connect(lambda: self.setIsABS(name='ch10', onABS=False))
        elif self.rtsp_num == 3:
            self.actionStop_ABS_RTSP_1.triggered.connect(lambda: self.setIsABS(name='RTSP_1', onABS=False))
            self.actionStop_ABS_RTSP_2.triggered.connect(lambda: self.setIsABS(name='RTSP_2', onABS=False))
            self.actionStop_ABS_RTSP_3.triggered.connect(lambda: self.setIsABS(name='RTSP_3', onABS=False))
            self.actionStop_ABS_CH_1.triggered.connect(lambda: self.setIsABS(name='ch1', onABS=False))
            self.actionStop_ABS_CH_2.triggered.connect(lambda: self.setIsABS(name='ch2', onABS=False))
            self.actionStop_ABS_CH_3.triggered.connect(lambda: self.setIsABS(name='ch3', onABS=False))
            self.actionStop_ABS_CH_4.triggered.connect(lambda: self.setIsABS(name='ch4', onABS=False))
            self.actionStop_ABS_CH_5.triggered.connect(lambda: self.setIsABS(name='ch5', onABS=False))
            self.actionStop_ABS_CH_6.triggered.connect(lambda: self.setIsABS(name='ch6', onABS=False))
            self.actionStop_ABS_CH_7.triggered.connect(lambda: self.setIsABS(name='ch7', onABS=False))
            self.actionStop_ABS_CH_8.triggered.connect(lambda: self.setIsABS(name='ch8', onABS=False))
            self.actionStop_ABS_CH_9.triggered.connect(lambda: self.setIsABS(name='ch9', onABS=False))
            self.actionStop_ABS_CH_10.triggered.connect(lambda: self.setIsABS(name='ch10', onABS=False))

        # TODO : OBS (방송) 화면 송출한 서브 화면 표시 (widget)
        self.monit_class = MonitClass()
        self.monit_thread = None

        # TODO : ABS 서버 통신 쓰레드
        #self.abs_request_thread = threading.Thread(target=getPitchInfo)
        #self.abs_request_thread.start()
        self.abs_request_thread = GetPitchInfo(parent=self)
        self.abs_request_thread.start()



    # TODO : ABS Setting
    def setIsABS(self,name,onABS):
        self.isABS[name] = onABS

    # TODO : RTSP 서버 갯수 정하기
    def setRTSP_Number(self,rtsp_number):
        if rtsp_number == self.rtsp_num:
            QMessageBox.about(self, "Set RTSP Number", "The set value is the same")
        else:
            try:
                Config.config['RTSP']['rtsp_num'] = str(rtsp_number)
                with open(Config.config_path, 'w', encoding='utf-8') as configfile:
                    Config.config.write(configfile)
                QMessageBox.about(self, "Set RTSP Number", "Please restart the program")
            except Exception as e:
                print(e)

    # TODO : RTSP 주소 받기
    def getRtsp(self,server_num):
        dialog = rtsp_dialog.RTSP_dialog(server_num)
        if server_num == 'First RTSP':
            self.server_num = server_num
            dialog.rtsp_address_signal.connect(self.setRtsp)
        if server_num == 'Second RTSP':
            self.server_num = server_num
            dialog.rtsp_address_signal.connect(self.setRtsp)
        if server_num == 'Third RTSP':
            self.server_num = server_num
            dialog.rtsp_address_signal.connect(self.setRtsp)
        dialog.exec_()

    # TODO : RTSP 주소 설정 완료
    def setRtsp(self,address):
        if self.server_num == 'First RTSP':
            self.first_rtsp = address
            #print(f"{self.server_num} :: {self.rtsp_server1}")
        if self.server_num == 'Second RTSP':
            self.second_rtsp = address
            #print(f"{self.server_num} :: {self.rtsp_server2}")
        if self.server_num == 'Third RTSP':
            self.third_rtsp = address

    # TODO : crop 이미지 채널 설정 및 rect 설정
    def getChannelSetting(self,rtsp_name):
        #global ch_frame
        global main1_frame
        global main2_frame
        global main3_frame

        if rtsp_name == "First RTSP":
            if main1_frame != None:
                #dialog = set_Channel.Set_Channel_Dialog(frame=ch_frame[0].scaled(self.main_screen_width,self.main_screen_height),rtsp_name=rtsp_name)
                if self.ch_rect['RTSP_1'][2] <= 1280:
                    w = self.ch_rect['RTSP_1'][2]
                    h = self.ch_rect['RTSP_1'][3]
                    self.crop_ch_rect['RTSP_1'][0] = w
                    self.crop_ch_rect['RTSP_1'][1] = h
                if self.ch_rect['RTSP_1'][2] > 1280:
                    w = 1280
                    h = 720
                    self.crop_ch_rect['RTSP_1'][0] = w
                    self.crop_ch_rect['RTSP_1'][1] = h
                dialog = set_Channel.Set_Channel_Dialog(frame=self.main1.pixmap().scaled(self.crop_ch_rect['RTSP_1'][0],self.crop_ch_rect['RTSP_1'][1]), rtsp_name=rtsp_name,origin_width=self.ch_rect['RTSP_1'][2])
                dialog.get_rectangle_signal.connect(self.setChannelRect)
                dialog.exec_()
            if main1_frame == None:
                QMessageBox.about(self, "RTSP Connect Error", "First RTSP Server Not Connect")

        if rtsp_name == "Second RTSP":
            if main2_frame != None:
                if self.ch_rect['RTSP_2'][2] <= 1280:
                    w = self.ch_rect['RTSP_2'][2]
                    h = self.ch_rect['RTSP_2'][3]
                    self.crop_ch_rect['RTSP_2'][0] = w
                    self.crop_ch_rect['RTSP_2'][1] = h
                if self.ch_rect['RTSP_2'][2] > 1280:
                    w = 1280
                    h = 720
                    self.crop_ch_rect['RTSP_2'][0] = w
                    self.crop_ch_rect['RTSP_2'][1] = h
                #dialog = set_Channel.Set_Channel_Dialog(frame=ch_frame[1].scaled(self.main_screen_width,self.main_screen_height),rtsp_name=rtsp_name)
                dialog = set_Channel.Set_Channel_Dialog(frame=self.main2.pixmap().scaled(self.crop_ch_rect['RTSP_2'][0],self.crop_ch_rect['RTSP_2'][1]), rtsp_name=rtsp_name,origin_width=self.ch_rect['RTSP_2'][2])
                dialog.get_rectangle_signal.connect(self.setChannelRect)
                dialog.exec_()
            if main2_frame == None:
                QMessageBox.about(self, "RTSP Connect Error", "Second RTSP Server Not Connect")

        if rtsp_name == "Third RTSP":
            if main3_frame != None:
                #dialog = set_Channel.Set_Channel_Dialog(frame=ch_frame[1].scaled(self.main_screen_width,self.main_screen_height),rtsp_name=rtsp_name)
                if self.ch_rect['RTSP_3'][2] <= 1280:
                    w = self.ch_rect['RTSP_3'][2]
                    h = self.ch_rect['RTSP_3'][3]
                    self.crop_ch_rect['RTSP_3'][0] = w
                    self.crop_ch_rect['RTSP_3'][1] = h
                if self.ch_rect['RTSP_3'][2] > 1280:
                    w = 1280
                    h = 720
                    self.crop_ch_rect['RTSP_3'][0] = w
                    self.crop_ch_rect['RTSP_3'][1] = h
                dialog = set_Channel.Set_Channel_Dialog(frame=self.main3.pixmap().scaled(self.crop_ch_rect['RTSP_3'][0],self.crop_ch_rect['RTSP_3'][1]), rtsp_name=rtsp_name,origin_width=self.ch_rect['RTSP_3'][2])
                dialog.get_rectangle_signal.connect(self.setChannelRect)
                dialog.exec_()
            if main3_frame == None:
                QMessageBox.about(self, "RTSP Connect Error", "Third RTSP Server Not Connect")

    # TODO : CH 셋팅에서 전달받은 값.. ch1, ch2 ... // First RTSP, Second RTSP // [left_top_x,left_top_y,width,height]
    def setChannelRect(self, ch, rtsp_name, rect_point):
        #global ch_frame
        global main1_frame
        global main2_frame
        global main3_frame
        ##########################################

        crop_x, crop_y, crop_width, crop_height = rect_point
        #width_rate = self.ch_rect['ch1'][2] / self.main_screen_width
        #height_rate = self.ch_rect['ch1'][3] / self.main_screen_height

        if rtsp_name == 'First RTSP' and main1_frame != None:
            width_rate = self.ch_rect['RTSP_1'][2] / self.crop_ch_rect['RTSP_1'][0]
            height_rate = self.ch_rect['RTSP_1'][3] / self.crop_ch_rect['RTSP_1'][1]
            self.ch_rect[ch] = [round(crop_x * width_rate), round(crop_y * height_rate),round(crop_width * width_rate), round(crop_height * height_rate),'RTSP_1',False]
        if rtsp_name == 'Second RTSP' and main2_frame != None:
            width_rate = self.ch_rect['RTSP_2'][2] / self.crop_ch_rect['RTSP_2'][0]
            height_rate = self.ch_rect['RTSP_2'][3] / self.crop_ch_rect['RTSP_2'][1]
            self.ch_rect[ch] = [round(crop_x * width_rate), round(crop_y * height_rate),round(crop_width * width_rate), round(crop_height * height_rate), 'RTSP_2',False]
        if rtsp_name == 'Third RTSP' and main3_frame != None:
            width_rate = self.ch_rect['RTSP_3'][2] / self.crop_ch_rect['RTSP_3'][0]
            height_rate = self.ch_rect['RTSP_3'][3] / self.crop_ch_rect['RTSP_3'][1]
            self.ch_rect[ch] = [round(crop_x * width_rate), round(crop_y * height_rate),round(crop_width * width_rate), round(crop_height * height_rate), 'RTSP_3',False]

        ##########################################
        """
        for i in self.crop_update_thread.keys():
            if i == ch and self.crop_update_thread[i] != None:
                self.crop_update_thread[i].stop()
                self.crop_update_thread[i].wait()

        self.crop_update_thread[ch] = CropUpdateThread(rtsp_name=rtsp_name, rect_point=rect_point, ch=ch, parent=self)
        self.crop_update_thread[ch].update_pixmap_signal.connect(self.update_channel_pixmap)

        self.crop_update_thread[ch].start()
        """

    # TODO : crop 이미지 출력을 위한 slot
    @pyqtSlot(QImage, str)
    def update_channel_pixmap(self, pixmap,ch):
        pixmap = pixmap.scaled(self.sub_screen_width, self.sub_screen_height)
        pixmap = QPixmap.fromImage(pixmap)

        try:
            if ch == 'ch1':
                self.ch1.setPixmap(pixmap)
            elif ch == 'ch2':
                self.ch2.setPixmap(pixmap)
            elif ch == 'ch3':
                self.ch3.setPixmap(pixmap)
            elif ch == 'ch4':
                self.ch4.setPixmap(pixmap)
            elif ch == 'ch5':
                self.ch5.setPixmap(pixmap)
            elif ch == 'ch6':
                self.ch6.setPixmap(pixmap)
            elif ch == 'ch7':
                self.ch7.setPixmap(pixmap)
            elif ch == 'ch8':
                self.ch8.setPixmap(pixmap)
            elif ch == 'ch9':
                self.ch9.setPixmap(pixmap)
            elif ch == 'ch10':
                self.ch10.setPixmap(pixmap)

        except Exception as e:
            print(f"update_channel_pixmap function error :: {e}")

    # TODO : 모니터 화면 업데이트 스레드 signal 받는 slot 함수
    @pyqtSlot(QImage,bool)
    def update_monit_frame(self,qimage,isABS):
        global pitchInfo
        pixmap = QPixmap.fromImage(qimage)

        # TODO : 스트라이크존 isABS 판별
        if isABS:
            painter = QPainter(pixmap)
            painter.setOpacity(0.6)
            painter.drawPixmap(self.strike_zone_image_x,self.strike_zone_image_y,self.strike_zone)
            if pitchInfo is not None:
                try:
                    if Config.config['ABS']['reverse'] == 'true':
                        x_rate = ((self.zone_width / 2) + (pitchInfo['pitch_x'] / 10000)) / self.zone_width
                        x_point = round(self.strike_zone_start_x + ((self.strike_zone_end_x - self.strike_zone_start_x) * x_rate))
                        x_point = round(2*(self.strike_zone_start_x + (self.strike_zone_end_x - self.strike_zone_start_x)/2) - x_point)

                    if Config.config['ABS']['reverse'] == 'false':
                        x_rate = ((self.zone_width/2) + (pitchInfo['pitch_x']/10000)) / self.zone_width
                        x_point = round(self.strike_zone_start_x + ((self.strike_zone_end_x - self.strike_zone_start_x ) * x_rate))
                    y_rate = ((pitchInfo['pitch_y'] - pitchInfo['box_bottom']) / (pitchInfo['box_top']-pitchInfo['box_bottom']))
                    y_point = round(self.strike_zone_end_y - ((self.strike_zone_end_y - self.strike_zone_start_y) * y_rate))

                    if x_point <= self.strike_zone_image_x:
                        x_point = self.strike_zone_image_x  + self.ball_size
                    if x_point >= self.strike_zone_image_x + self.strike_zone.width():
                        x_point = self.strike_zone_image_x + self.strike_zone.width() - 2*self.ball_size
                    if y_point <= self.strike_zone_image_y:
                        y_point = self.strike_zone_image_y  + self.ball_size
                    if y_point >= self.strike_zone_image_y + self.km_start_y:
                        y_point = self.strike_zone_image_y + self.km_start_y  - 2*self.ball_size

                    painter.setPen(QPen(Qt.gray, self.ball_size))
                    painter.drawEllipse(x_point,y_point,self.ball_size,self.ball_size)
                    global config_width
                    painter.setPen(QPen(Qt.red))
                    painter.setFont(QFont('Times',round(25*(config_width/1920)),QFont.Bold))
                    painter.drawText(QRect(self.km_start_x, self.km_start_y, self.strike_zone.width(), self.strike_zone_image_y+self.strike_zone.height()-self.km_start_y),Qt.AlignCenter, f"{pitchInfo['speed']}KM")
                except Exception as e:
                    print(f"ABS ball point error :: {e}")
            painter.end()

        self.monit_class.monit_label.setPixmap(pixmap)
    def setStrikeZone(self,qimage):
        painter = QPainter(qimage)
        painter.setOpacity(0.6)
        painter.drawPixmap(self.strike_zone_image_x,self.strike_zone_image_y,self.strike_zone)
        painter.end()

    def closeEvent(self, event):
        message = QMessageBox.question(self, "OnePersonBroadcast", "Are you sure you want to quit?")
        if message == QMessageBox.Yes:

            if self.rtsp_worker1 != None:
                self.rtsp_worker1.stop()
                self.rtsp_worker1.wait()
            if self.rtsp_worker2 != None:
                self.rtsp_worker2.stop()
                self.rtsp_worker2.wait()
            if self.rtsp_worker3 != None:
                self.rtsp_worker3.stop()
                self.rtsp_worker3.wait()
            """
            for ch in self.crop_update_thread.keys():
                if self.crop_update_thread[ch] != None:
                    self.crop_update_thread[ch].stop()
                    self.crop_update_thread[ch].wait()
            """
            self.monit_class.close()
            if self.monit_thread != None:
                self.monit_thread.stop()

            self.abs_request_thread.stop()
            time.sleep(0.5)
            #global ch_frame
            global main1_frame
            global main2_frame
            global main3_frame
            #global isClose
            #for index in range(0, len(ch_frame)):
            #    ch_frame[index] = None
            main1_frame = None
            main2_frame = None
            main3_frame = None
            #isClose = True
            #cv2.destroyAllWindows()
            event.accept()

        else:
            event.ignore()


    def keyPressEvent(self, event):
        #global ch_frame
        global main1_frame
        global main2_frame
        global main3_frame
        #global opencv_key

        if event.key() == Qt.Key_Q:
            self.close()

        if event.key() == Qt.Key_F11:
            if self.height() != self.window_height:
                self.showFullScreen()
            else:
                self.showMaximized()

        if event.key() == Qt.Key_F1:
            self.getChannelSetting(rtsp_name="First RTSP")

        if event.key() == Qt.Key_F2:
            self.getChannelSetting(rtsp_name="Second RTSP")

        if self.rtsp_num == 3:
            if event.key() == Qt.Key_F3:
                self.getChannelSetting(rtsp_name="Third RTSP")

        if event.key() == Qt.Key_F5:
            self.run_first_rtsp()

        if event.key() == Qt.Key_F6:
            self.run_second_rtsp()

        if self.rtsp_num == 3:
            if event.key() == Qt.Key_F7:
                self.run_third_rtsp()

        # TODO : OBS ( 화면출력 ) 변경시 Monit Thread에 데이터 전달
        def handle_channel_key(channel, channel_rect, isABS):
            #global isClose
            #while channel_rect != None:
            if channel_rect != None:
                try:
                    for i in self.channel_list:
                        if i == channel:
                            i.setStyleSheet(self.selected_color)
                        else:
                            i.setStyleSheet(self.no_selected_color)

                    #if isClose:
                    #    break
                    if channel_rect[4] == 'RTSP_1':
                        if self.monit_thread == None:
                            self.monit_thread = MonitThread(channel_rect=channel_rect,ch='RTSP_1',isABS=isABS)
                            self.monit_thread.update_monit_frame.connect(self.update_monit_frame)
                            self.monit_thread.start()
                        if self.monit_thread != None:
                            self.monit_thread.change_channel_rect(channel_rect=channel_rect,ch='RTSP_1',isABS=isABS)

                        #self.monit_class.monit_label.setPixmap(ch_frame[0].copy(channel_rect[0],channel_rect[1],channel_rect[2],channel_rect[3]).scaled(1280,720))

                    if channel_rect[4] == 'RTSP_2':
                        if self.monit_thread == None:
                            self.monit_thread = MonitThread(channel_rect=channel_rect, ch='RTSP_2',isABS=isABS)
                            self.monit_thread.update_monit_frame.connect(self.update_monit_frame)
                            self.monit_thread.start()
                        if self.monit_thread != None:
                            self.monit_thread.change_channel_rect(channel_rect=channel_rect,ch='RTSP_2',isABS=isABS)
                        #self.monit_class.monit_label.setPixmap(ch_frame[1].copy(channel_rect[0], channel_rect[1], channel_rect[2], channel_rect[3]).scaled(1280,720))

                    if channel_rect[4] == 'RTSP_3':
                        if self.monit_thread == None:
                            self.monit_thread = MonitThread(channel_rect=channel_rect, ch='RTSP_3',isABS=isABS)
                            self.monit_thread.update_monit_frame.connect(self.update_monit_frame)
                            self.monit_thread.start()
                        if self.monit_thread != None:
                            self.monit_thread.change_channel_rect(channel_rect=channel_rect,ch='RTSP_3',isABS=isABS)
                        #self.monit_class.monit_label.setPixmap(ch_frame[1].copy(channel_rect[0], channel_rect[1], channel_rect[2], channel_rect[3]).scaled(1280,720))
                    #opencv_key = cv2.waitKey(1)
                    for j in self.ch_rect.keys():
                        if self.ch_rect[j] == None:
                            continue
                        if channel_rect == self.ch_rect[j]:
                            self.ch_rect[j][5] = True
                        else:
                            self.ch_rect[j][5] = False
                except Exception as e:
                    print(f"key handle event error :: {e}")

        if self.rtsp_num == 2:
            key_map = {
                Qt.Key.Key_Insert: (self.main1, self.ch_rect['RTSP_1'],self.isABS['RTSP_1']),
                Qt.Key.Key_Home: (self.main2, self.ch_rect['RTSP_2'],self.isABS['RTSP_2']),
                Qt.Key.Key_1: (self.ch1, self.ch_rect['ch1'],self.isABS['ch1']),
                Qt.Key.Key_2: (self.ch2, self.ch_rect['ch2'],self.isABS['ch2']),
                Qt.Key.Key_3: (self.ch3, self.ch_rect['ch3'],self.isABS['ch3']),
                Qt.Key.Key_4: (self.ch4, self.ch_rect['ch4'],self.isABS['ch4']),
                Qt.Key.Key_5: (self.ch5, self.ch_rect['ch5'],self.isABS['ch5']),
                Qt.Key.Key_6: (self.ch6, self.ch_rect['ch6'],self.isABS['ch6']),
                Qt.Key.Key_7: (self.ch7, self.ch_rect['ch7'],self.isABS['ch7']),
                Qt.Key.Key_8: (self.ch8, self.ch_rect['ch8'],self.isABS['ch8']),
                Qt.Key.Key_9: (self.ch9, self.ch_rect['ch9'],self.isABS['ch9']),
                Qt.Key.Key_0: (self.ch10, self.ch_rect['ch10'],self.isABS['ch10']),
            }
        if self.rtsp_num == 3:
            key_map = {
                Qt.Key.Key_Insert: (self.main1, self.ch_rect['RTSP_1'],self.isABS['RTSP_1']),
                Qt.Key.Key_Home: (self.main2, self.ch_rect['RTSP_2'],self.isABS['RTSP_2']),
                Qt.Key.Key_PageUp: (self.main3, self.ch_rect['RTSP_3'],self.isABS['RTSP_3']),
                Qt.Key.Key_1: (self.ch1, self.ch_rect['ch1'],self.isABS['ch1']),
                Qt.Key.Key_2: (self.ch2, self.ch_rect['ch2'],self.isABS['ch2']),
                Qt.Key.Key_3: (self.ch3, self.ch_rect['ch3'],self.isABS['ch3']),
                Qt.Key.Key_4: (self.ch4, self.ch_rect['ch4'],self.isABS['ch4']),
                Qt.Key.Key_5: (self.ch5, self.ch_rect['ch5'],self.isABS['ch5']),
                Qt.Key.Key_6: (self.ch6, self.ch_rect['ch6'],self.isABS['ch6']),
                Qt.Key.Key_7: (self.ch7, self.ch_rect['ch7'],self.isABS['ch7']),
                Qt.Key.Key_8: (self.ch8, self.ch_rect['ch8'],self.isABS['ch8']),
                Qt.Key.Key_9: (self.ch9, self.ch_rect['ch9'],self.isABS['ch9']),
                Qt.Key.Key_0: (self.ch10, self.ch_rect['ch10'],self.isABS['ch10']),
            }


        if event.key() in key_map:
            channel, channel_rect, isABS = key_map[event.key()]
            handle_channel_key(channel, channel_rect, isABS)

    # TODO : 첫번째 rtsp 서버 실행 함수
    def run_first_rtsp(self):
        try:
            if self.first_rtsp != None:
                if self.rtsp_worker1 != None:
                    self.rtsp_worker1.stop()
                self.rtsp_worker1 = rtsp_worker(self, url=self.first_rtsp,name="first")
                self.rtsp_worker1.update_frame.connect(self.update_frame)

                self.rtsp_worker1.start()
        except Exception as e:
            print(f"run_rtsp_first Error :: {e}")
            if self.rtsp_worker1 != None:
                self.rtsp_worker1.stop()
                self.rtsp_worker1 = None


    # TODO : 두번째 rtsp 서버 실행 함수
    def run_second_rtsp(self):
        try:
            if self.second_rtsp != None:
                if self.rtsp_worker2 != None:
                    self.rtsp_worker2.stop()

                self.rtsp_worker2 = rtsp_worker(self, url=self.second_rtsp,name="second")
                self.rtsp_worker2.update_frame.connect(self.update_frame)

                self.rtsp_worker2.start()
        except Exception as e:
            print(f"run_rtsp_second Error :: {e}")
            if self.rtsp_worker2 != None:
                self.rtsp_worker2.stop()
                self.rtsp_worker2 = None

    # TODO : 세번째 rtsp 서버 실행 함수
    def run_third_rtsp(self):
        try:
            if self.third_rtsp != None:
                if self.rtsp_worker3 != None:
                    self.rtsp_worker3.stop()
                self.rtsp_worker3 = rtsp_worker(self, url=self.third_rtsp, name="third")
                self.rtsp_worker3.update_frame.connect(self.update_frame)

                self.rtsp_worker3.start()
        except Exception as e:
            print(f"run_rtsp_second Error :: {e}")
            if self.rtsp_worker3 != None:
                self.rtsp_worker3.stop()
                self.rtsp_worker3 = None

    # TODO : RTSP 서버 종료 함수
    def stop_rtsp(self,name):
        if name == 'first':
            if self.rtsp_worker1 != None:
                self.rtsp_worker1.stop()
                self.rtsp_worker1.wait()
                self.rtsp_worker1 = None

        if name == 'second':
            if self.rtsp_worker2 != None:
                self.rtsp_worker2.stop()
                self.rtsp_worker2.wait()
                self.rtsp_worker2 = None

        if name == 'third':
            if self.rtsp_worker3 != None:
                self.rtsp_worker3.stop()
                self.rtsp_worker3.wait()
                self.rtsp_worker3 = None

    #TODO : PIP 채널 영상 종료
    def stop_ch(self,ch):
        self.ch_rect[ch] = None
        if ch == 'ch1':
            self.ch1.setPixmap(self.sub_noSignalImage)
        elif ch == 'ch2':
            self.ch2.setPixmap(self.sub_noSignalImage)
        elif ch == 'ch3':
            self.ch3.setPixmap(self.sub_noSignalImage)
        elif ch == 'ch4':
            self.ch4.setPixmap(self.sub_noSignalImage)
        elif ch == 'ch5':
            self.ch5.setPixmap(self.sub_noSignalImage)
        elif ch == 'ch6':
            self.ch6.setPixmap(self.sub_noSignalImage)
        elif ch == 'ch7':
            self.ch7.setPixmap(self.sub_noSignalImage)
        elif ch == 'ch8':
            self.ch8.setPixmap(self.sub_noSignalImage)
        elif ch == 'ch9':
            self.ch9.setPixmap(self.sub_noSignalImage)
        elif ch == 'ch10':
            self.ch10.setPixmap(self.sub_noSignalImage)


    def draw_crop_rect(self,frame,geometry,text,ch,selected):

        # TODO: 해당 rect는 원본 비율의 x, y, w, h
        pixmap_with_rects = frame
        painter = QPainter(pixmap_with_rects)
        painter.setRenderHint(QPainter.Antialiasing)
        if not selected:
            pen = QPen(Qt.green)
        if selected:
            pen = QPen(Qt.red)
        pen.setWidth(2)
        painter.setPen(pen)

        font = QFont()
        font.setFamily('Times')
        font.setBold(True)
        font.setPointSize(round(10))
        painter.setFont(font)

        x, y, w, h = geometry
        if ch != 'RTSP_1' and ch != 'RTSP_2' and ch != 'RTSP_3':
            rect = QRect(x, y, w, h)
            painter.drawRect(rect)

        if self.isABS[ch]: # onABS
            painter.drawText(QRect(x+10,y+10,w,h),Qt.TextWordWrap, text+'\nABS')  # rect 위에 key 값을 글자로 씀
        if not self.isABS[ch]: # offABS
            painter.drawText(QRect(x + 10, y + 10, w, h), Qt.TextWordWrap, text)  # rect 위에 key 값을 글자로 씀

        painter.end()

        return pixmap_with_rects

    # TODO : main1, main2 화면에 출력 ( Rect ) signal 받는 slot 함수
    @pyqtSlot(np.ndarray, str, int)
    def update_frame(self, frame, name, crop_frame_count):
        #global ch_frame
        global main1_frame
        global main2_frame
        global main3_frame
        global video_fps
        global monit_fps

        # TODO : 전달받은 opencv 영상을 pixmap으로 변환 ( 원본 )
        h, w, c = frame.shape
        qImg = QImage(frame.data, w, h, w * c, QImage.Format.Format_BGR888)
        pixmap = QPixmap.fromImage(qImg)
        crop_frame = None
        if name == 'first':
            main1_frame = pixmap
            main_frame = pixmap.scaled(self.main_screen_width,self.main_screen_height)

            if crop_frame_count % round(video_fps/monit_fps) == 0:
                crop_frame = main_frame.copy()

            self.ch_rect['RTSP_1'] = [0, 0, w, h,'RTSP_1',False]

            for i in self.ch_rect.keys():
                try:
                    if i == 'RTSP_2' or i == 'RTSP_3':
                        continue

                    if self.ch_rect[i] != None and self.ch_rect[i][4] == 'RTSP_1':
                        x,y,w,h = self.ch_rect[i][:4]
                        witdh_rate = self.main_screen_width/self.ch_rect['RTSP_1'][2]
                        height_rate = self.main_screen_height/self.ch_rect['RTSP_1'][3]
                        x = round(x*witdh_rate)
                        y = round(y*height_rate)
                        w = round(w*witdh_rate)
                        h = round(h*height_rate)
                        main_frame = self.draw_crop_rect(frame=main_frame, geometry=(x, y, w, h),text=f'{i}\n{self.ch_rect[i][2]}x{self.ch_rect[i][3]}',ch=i,selected=self.ch_rect[i][5]).copy()
                        if crop_frame_count % round(video_fps/monit_fps) != 0 or crop_frame == None:
                            continue
                        elif i == 'ch1':
                            self.ch1.setPixmap(crop_frame.copy(round(self.ch_rect[i][0]*witdh_rate),round(self.ch_rect[i][1]*height_rate),round(self.ch_rect[i][2]*witdh_rate),round(self.ch_rect[i][3]*height_rate)).scaled(self.sub_screen_width,self.sub_screen_height))
                        elif i == 'ch2':
                            self.ch2.setPixmap(crop_frame.copy(round(self.ch_rect[i][0]*witdh_rate),round(self.ch_rect[i][1]*height_rate),round(self.ch_rect[i][2]*witdh_rate),round(self.ch_rect[i][3]*height_rate)).scaled(self.sub_screen_width,self.sub_screen_height))
                        elif i == 'ch3':
                            self.ch3.setPixmap(crop_frame.copy(round(self.ch_rect[i][0]*witdh_rate),round(self.ch_rect[i][1]*height_rate),round(self.ch_rect[i][2]*witdh_rate),round(self.ch_rect[i][3]*height_rate)).scaled(self.sub_screen_width,self.sub_screen_height))
                        elif i == 'ch4':
                            self.ch4.setPixmap(crop_frame.copy(round(self.ch_rect[i][0]*witdh_rate),round(self.ch_rect[i][1]*height_rate),round(self.ch_rect[i][2]*witdh_rate),round(self.ch_rect[i][3]*height_rate)).scaled(self.sub_screen_width,self.sub_screen_height))
                        elif i == 'ch5':
                            self.ch5.setPixmap(crop_frame.copy(round(self.ch_rect[i][0]*witdh_rate),round(self.ch_rect[i][1]*height_rate),round(self.ch_rect[i][2]*witdh_rate),round(self.ch_rect[i][3]*height_rate)).scaled(self.sub_screen_width,self.sub_screen_height))
                        elif i == 'ch6':
                            self.ch6.setPixmap(crop_frame.copy(round(self.ch_rect[i][0]*witdh_rate),round(self.ch_rect[i][1]*height_rate),round(self.ch_rect[i][2]*witdh_rate),round(self.ch_rect[i][3]*height_rate)).scaled(self.sub_screen_width,self.sub_screen_height))
                        elif i == 'ch7':
                            self.ch7.setPixmap(crop_frame.copy(round(self.ch_rect[i][0]*witdh_rate),round(self.ch_rect[i][1]*height_rate),round(self.ch_rect[i][2]*witdh_rate),round(self.ch_rect[i][3]*height_rate)).scaled(self.sub_screen_width,self.sub_screen_height))
                        elif i == 'ch8':
                            self.ch8.setPixmap(crop_frame.copy(round(self.ch_rect[i][0]*witdh_rate),round(self.ch_rect[i][1]*height_rate),round(self.ch_rect[i][2]*witdh_rate),round(self.ch_rect[i][3]*height_rate)).scaled(self.sub_screen_width,self.sub_screen_height))
                        elif i == 'ch9':
                            self.ch9.setPixmap(crop_frame.copy(round(self.ch_rect[i][0]*witdh_rate),round(self.ch_rect[i][1]*height_rate),round(self.ch_rect[i][2]*witdh_rate),round(self.ch_rect[i][3]*height_rate)).scaled(self.sub_screen_width,self.sub_screen_height))
                        elif i == 'ch10':
                            self.ch10.setPixmap(crop_frame.copy(round(self.ch_rect[i][0]*witdh_rate),round(self.ch_rect[i][1]*height_rate),round(self.ch_rect[i][2]*witdh_rate),round(self.ch_rect[i][3]*height_rate)).scaled(self.sub_screen_width,self.sub_screen_height))

                except Exception as e:
                    print(f"draw_rect_errorr :: {e}")
                    continue

            self.main1.setPixmap(main_frame)
            #self.main1.setPixmap(main_frame.scaled(self.main_screen_width, self.main_screen_height))



        if name == 'second':
            main2_frame = pixmap
            main_frame = pixmap.scaled(self.main_screen_width,self.main_screen_height)
            if crop_frame_count % round(video_fps/monit_fps) == 0:
                crop_frame = main_frame.copy()
            self.ch_rect['RTSP_2'] = [0, 0, w, h,'RTSP_2',False]

            for i in self.ch_rect.keys():
                try:
                    if i == 'RTSP_1' or i == 'RTSP_3':
                        continue
                    if self.ch_rect[i] != None and self.ch_rect[i][4] == 'RTSP_2':
                        x, y, w, h = self.ch_rect[i][:4]
                        witdh_rate = self.main_screen_width / self.ch_rect['RTSP_2'][2]
                        height_rate = self.main_screen_height / self.ch_rect['RTSP_2'][3]
                        x = round(x * witdh_rate)
                        y = round(y * height_rate)
                        w = round(w * witdh_rate)
                        h = round(h * height_rate)
                        main_frame = self.draw_crop_rect(frame=main_frame, geometry=(x, y, w, h), text=f'{i}\n{self.ch_rect[i][2]}x{self.ch_rect[i][3]}',ch=i,selected=self.ch_rect[i][5]).copy()
                        if crop_frame_count % round(video_fps/monit_fps) != 0 or crop_frame == None:
                            continue
                        if i == 'ch1':
                            self.ch1.setPixmap(crop_frame.copy(round(self.ch_rect[i][0]*witdh_rate),round(self.ch_rect[i][1]*height_rate),round(self.ch_rect[i][2]*witdh_rate),round(self.ch_rect[i][3]*height_rate)).scaled(self.sub_screen_width,self.sub_screen_height))
                        elif i == 'ch2':
                            self.ch2.setPixmap(crop_frame.copy(round(self.ch_rect[i][0]*witdh_rate),round(self.ch_rect[i][1]*height_rate),round(self.ch_rect[i][2]*witdh_rate),round(self.ch_rect[i][3]*height_rate)).scaled(self.sub_screen_width,self.sub_screen_height))
                        elif i == 'ch3':
                            self.ch3.setPixmap(crop_frame.copy(round(self.ch_rect[i][0]*witdh_rate),round(self.ch_rect[i][1]*height_rate),round(self.ch_rect[i][2]*witdh_rate),round(self.ch_rect[i][3]*height_rate)).scaled(self.sub_screen_width,self.sub_screen_height))
                        elif i == 'ch4':
                            self.ch4.setPixmap(crop_frame.copy(round(self.ch_rect[i][0]*witdh_rate),round(self.ch_rect[i][1]*height_rate),round(self.ch_rect[i][2]*witdh_rate),round(self.ch_rect[i][3]*height_rate)).scaled(self.sub_screen_width,self.sub_screen_height))
                        elif i == 'ch5':
                            self.ch5.setPixmap(crop_frame.copy(round(self.ch_rect[i][0] * witdh_rate),round(self.ch_rect[i][1]*height_rate),round(self.ch_rect[i][2] * witdh_rate),round(self.ch_rect[i][3] * height_rate)).scaled(self.sub_screen_width,self.sub_screen_height))
                        elif i == 'ch6':
                            self.ch6.setPixmap(crop_frame.copy(round(self.ch_rect[i][0]*witdh_rate),round(self.ch_rect[i][1]*height_rate),round(self.ch_rect[i][2]*witdh_rate),round(self.ch_rect[i][3]*height_rate)).scaled(self.sub_screen_width,self.sub_screen_height))
                        elif i == 'ch7':
                            self.ch7.setPixmap(crop_frame.copy(round(self.ch_rect[i][0]*witdh_rate),round(self.ch_rect[i][1]*height_rate),round(self.ch_rect[i][2]*witdh_rate),round(self.ch_rect[i][3]*height_rate)).scaled(self.sub_screen_width,self.sub_screen_height))
                        elif i == 'ch8':
                            self.ch8.setPixmap(crop_frame.copy(round(self.ch_rect[i][0]*witdh_rate),round(self.ch_rect[i][1]*height_rate),round(self.ch_rect[i][2]*witdh_rate),round(self.ch_rect[i][3]*height_rate)).scaled(self.sub_screen_width,self.sub_screen_height))
                        elif i == 'ch9':
                            self.ch9.setPixmap(crop_frame.copy(round(self.ch_rect[i][0]*witdh_rate),round(self.ch_rect[i][1]*height_rate),round(self.ch_rect[i][2]*witdh_rate),round(self.ch_rect[i][3]*height_rate)).scaled(self.sub_screen_width,self.sub_screen_height))
                        elif i == 'ch10':
                            self.ch10.setPixmap(crop_frame.copy(round(self.ch_rect[i][0]*witdh_rate),round(self.ch_rect[i][1]*height_rate),round(self.ch_rect[i][2]*witdh_rate),round(self.ch_rect[i][3]*height_rate)).scaled(self.sub_screen_width,self.sub_screen_height))

                except Exception as e:
                    print(f"draw_rect_errorr :: {e}")
                    continue
            self.main2.setPixmap(main_frame)
            #self.main2.setPixmap(main_frame.scaled(self.main_screen_width, self.main_screen_height))

        if name == 'third':
            main3_frame = pixmap
            main_frame = pixmap.scaled(self.main_screen_width,self.main_screen_height)
            if crop_frame_count % round(video_fps/monit_fps) == 0:
                crop_frame = main_frame.copy()
            self.ch_rect['RTSP_3'] = [0, 0, w, h,'RTSP_3',False]

            for i in self.ch_rect.keys():
                try:
                    if i == 'RTSP_1' or i == 'RTSP_2':
                        continue
                    if self.ch_rect[i] != None and self.ch_rect[i][4] == 'RTSP_3':
                        x, y, w, h = self.ch_rect[i][:4]
                        witdh_rate = self.main_screen_width / self.ch_rect['RTSP_3'][2]
                        height_rate = self.main_screen_height / self.ch_rect['RTSP_3'][3]
                        x = round(x * witdh_rate)
                        y = round(y * height_rate)
                        w = round(w * witdh_rate)
                        h = round(h * height_rate)
                        main_frame = self.draw_crop_rect(frame=main_frame, geometry=(x, y, w, h), text=f'{i}\n{self.ch_rect[i][2]}x{self.ch_rect[i][3]}',ch=i,selected=self.ch_rect[i][5]).copy()

                        if crop_frame_count % round(video_fps/monit_fps) != 0 or crop_frame == None:
                            continue
                        if i == 'ch1':
                            self.ch1.setPixmap(crop_frame.copy(round(self.ch_rect[i][0]*witdh_rate),round(self.ch_rect[i][1]*height_rate),round(self.ch_rect[i][2]*witdh_rate),round(self.ch_rect[i][3]*height_rate)).scaled(self.sub_screen_width,self.sub_screen_height))
                        elif i == 'ch2':
                            self.ch2.setPixmap(crop_frame.copy(round(self.ch_rect[i][0]*witdh_rate),round(self.ch_rect[i][1]*height_rate),round(self.ch_rect[i][2]*witdh_rate),round(self.ch_rect[i][3]*height_rate)).scaled(self.sub_screen_width,self.sub_screen_height))
                        elif i == 'ch3':
                            self.ch3.setPixmap(crop_frame.copy(round(self.ch_rect[i][0]*witdh_rate),round(self.ch_rect[i][1]*height_rate),round(self.ch_rect[i][2]*witdh_rate),round(self.ch_rect[i][3]*height_rate)).scaled(self.sub_screen_width,self.sub_screen_height))
                        elif i == 'ch4':
                            self.ch4.setPixmap(crop_frame.copy(round(self.ch_rect[i][0]*witdh_rate),round(self.ch_rect[i][1]*height_rate),round(self.ch_rect[i][2]*witdh_rate),round(self.ch_rect[i][3]*height_rate)).scaled(self.sub_screen_width,self.sub_screen_height))
                        elif i == 'ch5':
                            self.ch5.setPixmap(crop_frame.copy(round(self.ch_rect[i][0] * witdh_rate),round(self.ch_rect[i][1]*height_rate),round(self.ch_rect[i][2] * witdh_rate),round(self.ch_rect[i][3] * height_rate)).scaled(self.sub_screen_width,self.sub_screen_height))
                        elif i == 'ch6':
                            self.ch6.setPixmap(crop_frame.copy(round(self.ch_rect[i][0]*witdh_rate),round(self.ch_rect[i][1]*height_rate),round(self.ch_rect[i][2]*witdh_rate),round(self.ch_rect[i][3]*height_rate)).scaled(self.sub_screen_width,self.sub_screen_height))
                        elif i == 'ch7':
                            self.ch7.setPixmap(crop_frame.copy(round(self.ch_rect[i][0]*witdh_rate),round(self.ch_rect[i][1]*height_rate),round(self.ch_rect[i][2]*witdh_rate),round(self.ch_rect[i][3]*height_rate)).scaled(self.sub_screen_width,self.sub_screen_height))
                        elif i == 'ch8':
                            self.ch8.setPixmap(crop_frame.copy(round(self.ch_rect[i][0]*witdh_rate),round(self.ch_rect[i][1]*height_rate),round(self.ch_rect[i][2]*witdh_rate),round(self.ch_rect[i][3]*height_rate)).scaled(self.sub_screen_width,self.sub_screen_height))
                        elif i == 'ch9':
                            self.ch9.setPixmap(crop_frame.copy(round(self.ch_rect[i][0]*witdh_rate),round(self.ch_rect[i][1]*height_rate),round(self.ch_rect[i][2]*witdh_rate),round(self.ch_rect[i][3]*height_rate)).scaled(self.sub_screen_width,self.sub_screen_height))
                        elif i == 'ch10':
                            self.ch10.setPixmap(crop_frame.copy(round(self.ch_rect[i][0]*witdh_rate),round(self.ch_rect[i][1]*height_rate),round(self.ch_rect[i][2]*witdh_rate),round(self.ch_rect[i][3]*height_rate)).scaled(self.sub_screen_width,self.sub_screen_height))

                except Exception as e:
                    print(f"draw_rect_errorr :: {e}")
                    continue
            self.main3.setPixmap(main_frame)
            #self.main2.setPixmap(main_frame.scaled(self.main_screen_width, self.main_screen_height))



if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)
        myWindow = WindowClass()
        myWindow.showMaximized()
        sys.exit(app.exec_())
    except Exception as e:
        print(e)
