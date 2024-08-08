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

global ch_frame
#global opencv_key
#global isClose
ch_frame = [None,None,None]
#opencv_key = None
#isClose = False
global pitchInfo
pitchInfo = None
global isExe
isExe = Config.config['PROGRAM']['isExe'] == 'true'

# TODO : ABS 서버에서 스트라이크 좌표 가져오는 쓰레드 함수
def getPitchInfo():
    global pitchInfo
    while True:
        try:
            response = requests.get(url=Config.config['REQUEST']['uri'],timeout=2)
            data = response.json()

            if 'box_bottom' in data.keys():
                pitchInfo = data
            else :
                pitchInfo = None
            print(response)
            print(pitchInfo)
            time.sleep(0.5)
        except Exception as e:
            print(f"request fail :: {e}")


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
        try:
            cap = cv2.VideoCapture(self.url)
            frame_count = 0
            crop_frame_count = 1

            fps = 0
            while cap.isOpened() and self.working:
                ret, frame = cap.read()

                if not ret:
                    # TODO : 인터넷 속도 문제로 RTSP 서버 끊겼을시 재접속
                    frame_count += 1
                    if frame_count == 1000:
                        cap = cv2.VideoCapture(self.url)
                        frame_count = 0
                        crop_frame_count = 1
                    print('ret false')
                    continue

                crop_frame_count += 1
                if crop_frame_count == 31:
                    crop_frame_count = 1

                self.update_frame.emit(frame, self.name,crop_frame_count)
                QThread.msleep(1)


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
    update_monit_frame = pyqtSignal(QImage)

    def __init__(self,channel_rect,ch):
        super().__init__()
        self.working = True
        self.channel_rect = channel_rect
        self.ch = ch
    def run(self):
        global ch_frame

        while self.working:

            if self.ch == 'RTSP_1':
                frame = ch_frame[0].copy(self.channel_rect[0], self.channel_rect[1], self.channel_rect[2], self.channel_rect[3]).scaled(1280, 720)
            if self.ch == 'RTSP_2':
                frame = ch_frame[1].copy(self.channel_rect[0], self.channel_rect[1], self.channel_rect[2],self.channel_rect[3]).scaled(1280, 720)
            if self.ch == 'RTSP_3':
                frame = ch_frame[2].copy(self.channel_rect[0], self.channel_rect[1], self.channel_rect[2],self.channel_rect[3]).scaled(1280, 720)

            frame = frame.toImage()

            self.update_monit_frame.emit(frame)

            QThread.msleep(1)
    def change_channel_rect(self,channel_rect,ch):
        self.channel_rect = channel_rect
        self.ch = ch

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
        super().__init__()
        self.setupUi(self)
        self.monit_label.setGeometry(0,0,1280,720)
        if isExe:
            self.monit_label.setPixmap(QPixmap(f"{os.path.dirname(__file__)}\\Assets\\no-signal-icon-black.jpg"))
        if not isExe:
            self.monit_label.setPixmap(QPixmap('./Assets/no-signal-icon-black.jpg'))
        self.setGeometry(-1281,-721,1280,720)
        self.setFixedSize(self.width(),self.height())
        self.setWindowFlags(Qt.FramelessWindowHint)
        #self.setCursor(QCursor(Qt.BlankCursor))
        self.setWindowOpacity(0)
        self.show()

# TODO : main 화면 Class
class WindowClass(QMainWindow, form_class):
    def __init__(self):
        global isExe
        super().__init__()
        self.window_width = tkinter.Tk().winfo_screenwidth()
        self.window_height = tkinter.Tk().winfo_screenheight()
        self.setupUi(self)

        self.resize(round(self.window_width*0.9), round(self.window_height*0.9))
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
        shortCut_Key_box.setMinimumWidth(20031)
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




        # TODO : OBS (방송) 화면 송출한 서브 화면 표시 (widget)
        self.monit_class = MonitClass()
        self.monit_thread = None

        # TODO : ABS 서버 통신 쓰레드
        self.abs_request_thread = threading.Thread(target=getPitchInfo)



    # TODO : RTSP 서버 갯수 정하기
    def setRTSP_Number(self,rtsp_number):
        if rtsp_number == self.rtsp_num:
            QMessageBox.about(self, "Set RTSP Number", "The set value is the same")
        else:
            try:
                Config.config['RTSP']['rtsp_num'] = str(rtsp_number)
                with open(Config.config_path, 'w', encoding='utf-8') as configfile:
                    Config.config.write(configfile)
                QMessageBox.about(self, "Set RTSP Number", "Please rerun the program")
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
        global ch_frame
        if rtsp_name == "First RTSP":
            if ch_frame[0] != None:
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
            if ch_frame[0] == None:
                QMessageBox.about(self, "RTSP Connect Error", "First RTSP Server Not Connect")

        if rtsp_name == "Second RTSP":
            if ch_frame[1] != None:
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
            if ch_frame[1] == None:
                QMessageBox.about(self, "RTSP Connect Error", "Second RTSP Server Not Connect")

        if rtsp_name == "Third RTSP":
            if ch_frame[2] != None:
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
            if ch_frame[2] == None:
                QMessageBox.about(self, "RTSP Connect Error", "Third RTSP Server Not Connect")

    # TODO : CH 셋팅에서 전달받은 값.. ch1, ch2 ... // First RTSP, Second RTSP // [left_top_x,left_top_y,width,height]
    def setChannelRect(self, ch, rtsp_name, rect_point):
        global ch_frame
        ##########################################

        crop_x, crop_y, crop_width, crop_height = rect_point
        #width_rate = self.ch_rect['ch1'][2] / self.main_screen_width
        #height_rate = self.ch_rect['ch1'][3] / self.main_screen_height

        if rtsp_name == 'First RTSP' and ch_frame[0] != None:
            width_rate = self.ch_rect['RTSP_1'][2] / self.crop_ch_rect['RTSP_1'][0]
            height_rate = self.ch_rect['RTSP_1'][3] / self.crop_ch_rect['RTSP_1'][1]
            self.ch_rect[ch] = [round(crop_x * width_rate), round(crop_y * height_rate),round(crop_width * width_rate), round(crop_height * height_rate),'RTSP_1']
        if rtsp_name == 'Second RTSP' and ch_frame[1] != None:
            width_rate = self.ch_rect['RTSP_2'][2] / self.crop_ch_rect['RTSP_2'][0]
            height_rate = self.ch_rect['RTSP_2'][3] / self.crop_ch_rect['RTSP_2'][1]
            self.ch_rect[ch] = [round(crop_x * width_rate), round(crop_y * height_rate),round(crop_width * width_rate), round(crop_height * height_rate), 'RTSP_2']
        if rtsp_name == 'Third RTSP' and ch_frame[2] != None:
            width_rate = self.ch_rect['RTSP_3'][2] / self.crop_ch_rect['RTSP_3'][0]
            height_rate = self.ch_rect['RTSP_3'][3] / self.crop_ch_rect['RTSP_3'][1]
            self.ch_rect[ch] = [round(crop_x * width_rate), round(crop_y * height_rate),round(crop_width * width_rate), round(crop_height * height_rate), 'RTSP_3']

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
    @pyqtSlot(QImage)
    def update_monit_frame(self,qimage):
        pixmap = QPixmap.fromImage(qimage)
        self.monit_class.monit_label.setPixmap(pixmap)

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
            time.sleep(0.5)
            global ch_frame
            #global isClose
            for index in range(0, len(ch_frame)):
                ch_frame[index] = None
            #isClose = True
            cv2.destroyAllWindows()
            event.accept()

        else:
            event.ignore()


    def keyPressEvent(self, event):
        global ch_frame
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
        def handle_channel_key(channel, channel_rect):
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
                            self.monit_thread = MonitThread(channel_rect=channel_rect,ch='RTSP_1')
                            self.monit_thread.update_monit_frame.connect(self.update_monit_frame)
                            self.monit_thread.start()
                        if self.monit_thread != None:
                            self.monit_thread.change_channel_rect(channel_rect=channel_rect,ch='RTSP_1')
                        #self.monit_class.monit_label.setPixmap(ch_frame[0].copy(channel_rect[0],channel_rect[1],channel_rect[2],channel_rect[3]).scaled(1280,720))

                    if channel_rect[4] == 'RTSP_2':
                        if self.monit_thread == None:
                            self.monit_thread = MonitThread(channel_rect=channel_rect, ch='RTSP_2')
                            self.monit_thread.update_monit_frame.connect(self.update_monit_frame)
                            self.monit_thread.start()
                        if self.monit_thread != None:
                            self.monit_thread.change_channel_rect(channel_rect=channel_rect,ch='RTSP_2')
                        #self.monit_class.monit_label.setPixmap(ch_frame[1].copy(channel_rect[0], channel_rect[1], channel_rect[2], channel_rect[3]).scaled(1280,720))

                    if channel_rect[4] == 'RTSP_3':
                        if self.monit_thread == None:
                            self.monit_thread = MonitThread(channel_rect=channel_rect, ch='RTSP_3')
                            self.monit_thread.update_monit_frame.connect(self.update_monit_frame)
                            self.monit_thread.start()
                        if self.monit_thread != None:
                            self.monit_thread.change_channel_rect(channel_rect=channel_rect,ch='RTSP_3')
                        #self.monit_class.monit_label.setPixmap(ch_frame[1].copy(channel_rect[0], channel_rect[1], channel_rect[2], channel_rect[3]).scaled(1280,720))
                    #opencv_key = cv2.waitKey(1)
                except Exception as e:
                    print(f"key handle event error :: {e}")

        if self.rtsp_num == 2:
            key_map = {
                Qt.Key.Key_Insert: (self.main1, self.ch_rect['RTSP_1']),
                Qt.Key.Key_Home: (self.main2, self.ch_rect['RTSP_2']),
                Qt.Key.Key_1: (self.ch1, self.ch_rect['ch1']),
                Qt.Key.Key_2: (self.ch2, self.ch_rect['ch2']),
                Qt.Key.Key_3: (self.ch3, self.ch_rect['ch3']),
                Qt.Key.Key_4: (self.ch4, self.ch_rect['ch4']),
                Qt.Key.Key_5: (self.ch5, self.ch_rect['ch5']),
                Qt.Key.Key_6: (self.ch6, self.ch_rect['ch6']),
                Qt.Key.Key_7: (self.ch7, self.ch_rect['ch7']),
                Qt.Key.Key_8: (self.ch8, self.ch_rect['ch8']),
                Qt.Key.Key_9: (self.ch9, self.ch_rect['ch9']),
                Qt.Key.Key_0: (self.ch10, self.ch_rect['ch10']),
            }
        if self.rtsp_num == 3:
            key_map = {
                Qt.Key.Key_Insert: (self.main1, self.ch_rect['RTSP_1']),
                Qt.Key.Key_Home: (self.main2, self.ch_rect['RTSP_2']),
                Qt.Key.Key_PageUp: (self.main3, self.ch_rect['RTSP_3']),
                Qt.Key.Key_1: (self.ch1, self.ch_rect['ch1']),
                Qt.Key.Key_2: (self.ch2, self.ch_rect['ch2']),
                Qt.Key.Key_3: (self.ch3, self.ch_rect['ch3']),
                Qt.Key.Key_4: (self.ch4, self.ch_rect['ch4']),
                Qt.Key.Key_5: (self.ch5, self.ch_rect['ch5']),
                Qt.Key.Key_6: (self.ch6, self.ch_rect['ch6']),
                Qt.Key.Key_7: (self.ch7, self.ch_rect['ch7']),
                Qt.Key.Key_8: (self.ch8, self.ch_rect['ch8']),
                Qt.Key.Key_9: (self.ch9, self.ch_rect['ch9']),
                Qt.Key.Key_0: (self.ch10, self.ch_rect['ch10']),
            }


        if event.key() in key_map:
            channel, channel_rect = key_map[event.key()]
            handle_channel_key(channel, channel_rect)

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


    def draw_crop_rect(self,frame,geometry,text,ch):

        # TODO: 해당 rect는 원본 비율의 x, y, w, h
        pixmap_with_rects = frame
        painter = QPainter(pixmap_with_rects)
        pen = QPen(Qt.green)
        pen.setWidth(2)
        painter.setPen(pen)

        font = QFont()
        font.setFamily('Times')
        font.setBold(True)
        font.setPointSize(10)
        painter.setFont(font)

        x, y, w, h = geometry
        if ch != 'RTSP_1' and ch != 'RTSP_2' and ch != 'RTSP_3':
            rect = QRect(x, y, w, h)
            painter.drawRect(rect)
        #painter.drawText(QRect(round((w)/2+x-17), round((h/2)+y+5),80,80),Qt.AlignCenter|Qt.TextWordWrap ,text+"\n이야야야야야")  # rect 위에 key 값을 글자로 씀
        painter.drawText(QRect(x+10,y+10,w,h),Qt.TextWordWrap, text)  # rect 위에 key 값을 글자로 씀
        painter.end()

        return pixmap_with_rects

    # TODO : main1, main2 화면에 출력 ( Rect ) signal 받는 slot 함수
    @pyqtSlot(np.ndarray, str, int)
    def update_frame(self, frame, name, crop_frame_count):
        global ch_frame

        # TODO : 전달받은 opencv 영상을 pixmap으로 변환 ( 원본 )
        h, w, c = frame.shape
        qImg = QImage(frame.data, w, h, w * c, QImage.Format.Format_BGR888)
        pixmap = QPixmap.fromImage(qImg)

        if name == 'first':
            ch_frame[0] = pixmap
            main_frame = pixmap.scaled(self.main_screen_width,self.main_screen_height)
            crop_frame = main_frame.copy()
            self.ch_rect['RTSP_1'] = [0, 0, w, h,'RTSP_1']

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

                        main_frame = self.draw_crop_rect(frame=main_frame, geometry=(x, y, w, h),text=f'{i}\n{self.ch_rect[i][2]}x{self.ch_rect[i][3]}',ch=i).copy()
                        if crop_frame_count % 15 != 0:
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
            ch_frame[1] = pixmap
            main_frame = pixmap.scaled(self.main_screen_width,self.main_screen_height)
            crop_frame = main_frame.copy()
            self.ch_rect['RTSP_2'] = [0, 0, w, h,'RTSP_2']

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
                        main_frame = self.draw_crop_rect(frame=main_frame, geometry=(x, y, w, h), text=f'{i}\n{self.ch_rect[i][2]}x{self.ch_rect[i][3]}',ch=i).copy()
                        if crop_frame_count % 15 != 0:
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
            ch_frame[2] = pixmap
            main_frame = pixmap.scaled(self.main_screen_width,self.main_screen_height)
            crop_frame = main_frame.copy()
            self.ch_rect['RTSP_3'] = [0, 0, w, h,'RTSP_3']

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
                        main_frame = self.draw_crop_rect(frame=main_frame, geometry=(x, y, w, h), text=f'{i}\n{self.ch_rect[i][2]}x{self.ch_rect[i][3]}',ch=i).copy()

                        if crop_frame_count % 15 != 0:
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
