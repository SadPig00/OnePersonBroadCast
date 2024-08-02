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


global ch_frame
#global opencv_key
#global isClose
ch_frame = [None,None]
#opencv_key = None
#isClose = False


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
    update_frame = pyqtSignal(np.ndarray, str)  # 프레임 업데이트 시그널

    def __init__(self, parent, url, name):
        super().__init__(parent)
        self.parent = parent
        self.url = url
        self.name = name
        self.working = True

    def run(self):
        try:
            cap = cv2.VideoCapture(self.url)
            while cap.isOpened() and self.working:
                ret, frame = cap.read()

                if not ret:
                    print(f"buffer error :: {e}")
                    continue

                self.update_frame.emit(frame, self.name)
                QThread.msleep(1)


            cap.release()
        except Exception as e:
            print(f"RSTP Server Run Error :: {e}")
            if self.name == 'first':
                QMessageBox.about(self, "RTSP Connect Error", "First RTSP Server Not Connect")
            if self.name == 'second':
                QMessageBox.about(self, "RTSP Connect Error", "Second RTSP Server Not Connect")
            self.stop()

    def stop(self):
        self.working = False
        self.quit()
        self.wait(2000)

# TODO : crop 이미지 스레드
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
                    width_rate = self.parent.ch_rect['ch1'][2] / self.parent.main_screen_width
                    height_rate = self.parent.ch_rect['ch1'][3] / self.parent.main_screen_height

                    # TODO : 원본 비율을 계산한 x,y,width,height
                    self.parent.ch_rect[self.ch] = [round(crop_x * width_rate), round(crop_y * height_rate), round(crop_width * width_rate), round(crop_height * height_rate),'ch1']
                    #frame = self.parent.main1.pixmap().copy(crop_x, crop_y,crop_width , crop_height )
                    frame = ch_frame[0].scaled(self.parent.main_screen_width,self.parent.main_screen_height).copy(crop_x, crop_y, crop_width, crop_height)

                #elif self.rtsp_name == 'Second RTSP' and ch_frame[1] != None and ch_frame[13] != None:
                elif self.rtsp_name == 'Second RTSP' and ch_frame[1] != None:

                    # TODO : 해당 채널의 원본비율 넓이 높이 저장
                    width_rate = self.parent.ch_rect['ch2'][2] / self.parent.main_screen_width
                    height_rate = self.parent.ch_rect['ch2'][3] / self.parent.main_screen_height

                    # TODO : 원본 비율을 계산한 x,y,width,height
                    self.parent.ch_rect[self.ch] = [round(crop_x * width_rate), round(crop_y * height_rate),round(crop_width * width_rate), round(crop_height * height_rate),'ch2']
                    #frame = self.parent.main2.pixmap().copy(crop_x, crop_y,crop_width , crop_height )
                    frame = ch_frame[1].scaled(self.parent.main_screen_width, self.parent.main_screen_height).copy(crop_x, crop_y, crop_width, crop_height)

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

            if self.ch == 'ch1':
                frame = ch_frame[0].copy(self.channel_rect[0], self.channel_rect[1], self.channel_rect[2], self.channel_rect[3]).scaled(1280, 720)
            if self.ch == 'ch2':
                frame = ch_frame[1].copy(self.channel_rect[0], self.channel_rect[1], self.channel_rect[2],self.channel_rect[3]).scaled(1280, 720)

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
form_class = uic.loadUiType('./UI/BroadCast.ui')[0]
monit_class = uic.loadUiType('./UI/monit_widget.ui')[0]

# TODO : OBS ( 방송출력 ) 화면 Class
class MonitClass(QWidget,monit_class):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.monit_label.setGeometry(0,0,1280,720)
        self.monit_label.setPixmap(QPixmap('./Assets/no-signal-icon-black.jpg'))
        self.setGeometry(0,0,1280,720)
        self.setFixedSize(self.width(),self.height())
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.show()

# TODO : main 화면 Class
class WindowClass(QMainWindow, form_class):
    def __init__(self):
        super().__init__()
        self.window_width = tkinter.Tk().winfo_screenwidth()
        self.window_height = tkinter.Tk().winfo_screenheight()
        self.setupUi(self)

        # TODO : selected color :: rgb(253, 8, 8) // no selected color :: rgb(190, 190, 190);
        self.selected_color="border : 2px solid rgb(253,8,8)"
        self.no_selected_color="border : 2px solid rgb(190, 190, 190)"

        #self.main1.resize(100, 10)
        # TODO : 영상 화면 비율 16:9
        self.rate = 16 / 9

        # TODO : 초기 RSTP 서버 초기값 None
        self.first_rtsp = Config.config['RTSP']['first_rtsp']
        self.second_rtsp = Config.config['RTSP']['second_rtsp']

        # TODO : rtsp 스레드 초기 선언
        self.rtsp_worker1 = None
        self.rtsp_worker2 = None

        # TODO : frame 없을때 기본 이미지 설정
        noSignalImage = QPixmap('./Assets/no-signal-icon-black.jpg')

        # TODO : 이미지 사이즈 사용자의 모니터 사이즈에 맞춰 16:9 비율로 설정
        #self.main_screen_width = round(self.window_width / 2)
        self.main_screen_width = round(self.window_width / 2.15)
        self.main_screen_height = round(self.main_screen_width / self.rate)

        # TODO : main rtsp 채널 초기 이미지 셋팅
        main_noSignalImage = noSignalImage.scaled(self.main_screen_width, self.main_screen_height)
        self.main1.setPixmap(main_noSignalImage)
        self.main2.setPixmap(main_noSignalImage)

        #self.sub_screen_width = round(self.main_screen_width / 2)
        self.sub_screen_width = round(self.main_screen_width / 2.5)
        self.sub_screen_height = round(self.sub_screen_width / self.rate)
        sub_noSignalImage = noSignalImage.scaled(self.sub_screen_width, self.sub_screen_height)

        # TODO : CH list 선언
        self.channel_list = [self.main1, self.main2, self.ch3, self.ch4, self.ch5, self.ch6, self.ch7, self.ch8, self.ch9, self.ch10, self.ch11, self.ch12]

        # TODO : crop 스레드 관리를 위한 dict, 화면 표출을 위한 dict
        self.crop_update_thread = {'ch3':None,'ch4':None,'ch5':None,'ch6':None,'ch7':None,'ch8':None,'ch9':None,'ch10':None,'ch11':None,'ch12':None}
        self.ch_rect = {'ch1':None,'ch2':None,'ch3': None, 'ch4': None, 'ch5': None, 'ch6': None, 'ch7': None, 'ch8': None,'ch9': None, 'ch10': None, 'ch11': None, 'ch12': None}

        # TODO : 하위 (crop) 채널 초기 이미지 셋팅
        self.ch3.setPixmap(sub_noSignalImage)
        self.ch4.setPixmap(sub_noSignalImage)
        self.ch5.setPixmap(sub_noSignalImage)
        self.ch6.setPixmap(sub_noSignalImage)
        self.ch7.setPixmap(sub_noSignalImage)
        self.ch8.setPixmap(sub_noSignalImage)
        self.ch9.setPixmap(sub_noSignalImage)
        self.ch10.setPixmap(sub_noSignalImage)
        self.ch11.setPixmap(sub_noSignalImage)
        self.ch12.setPixmap(sub_noSignalImage)

        # TODO : Menu 버튼의 RTSP 설정 버튼 slot 설정
        self.actionSet_first_RTSP.triggered.connect(lambda : self.getRtsp('First RTSP'))
        self.actionSet_second_RTSP.triggered.connect(lambda: self.getRtsp('Second RTSP'))

        # TODO : Menu 버튼의 RTSP 실행 버튼 slot 설정
        self.actionRun_Frist_RTSP_Server.triggered.connect(self.run_first_rtsp)
        self.actionRun_second_RTSP_Server.triggered.connect(self.run_second_rtsp)

        # TODO : Menu 버튼의 Screen 설정
        self.actionFull_Screen.triggered.connect(self.showFullScreen)
        self.actionMax_size_Screen.triggered.connect(self.showMaximized)
        self.actionQuit_q.triggered.connect(self.close)


        # TODO : Menu 버튼의 channel 설정
        self.actionSelect_first_RTSP.triggered.connect(lambda :self.getChannelSetting(rtsp_name="First RTSP"))
        self.actionSelect_second_RTSP.triggered.connect(lambda: self.getChannelSetting(rtsp_name="Second RTSP"))

        # TODO : OBS (방송) 화면 송출한 서브 화면 표시 (widget)
        self.monit_class = MonitClass()
        self.monit_thread = None
    # TODO : RTSP 주소 받기
    def getRtsp(self,server_num):
        dialog = rtsp_dialog.RSTP_dialog(server_num)
        if server_num == 'First RTSP':
            self.server_num = server_num
            dialog.rtsp_address_signal.connect(self.setRtsp)
        if server_num == 'Second RTSP':
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

    # TODO : crop 이미지 채널 설정 및 rect 설정
    def getChannelSetting(self,rtsp_name):
        global ch_frame
        if rtsp_name == "First RTSP":
            if ch_frame[0] != None:
                #dialog = set_Channel.Set_Channel_Dialog(frame=ch_frame[0].scaled(self.main_screen_width,self.main_screen_height),rtsp_name=rtsp_name)
                dialog = set_Channel.Set_Channel_Dialog(frame=self.main1.pixmap(), rtsp_name=rtsp_name)
                dialog.get_rectangle_signal.connect(self.setChannelRect)
                dialog.exec_()
            if ch_frame[0] == None:
                QMessageBox.about(self, "RTSP Connect Error", "First RTSP Server Not Connect")
        if rtsp_name == "Second RTSP":
            if ch_frame[1] != None:
                #dialog = set_Channel.Set_Channel_Dialog(frame=ch_frame[1].scaled(self.main_screen_width,self.main_screen_height),rtsp_name=rtsp_name)
                dialog = set_Channel.Set_Channel_Dialog(frame=self.main2.pixmap(), rtsp_name=rtsp_name)
                dialog.get_rectangle_signal.connect(self.setChannelRect)
                dialog.exec_()
            if ch_frame[1] == None:
                QMessageBox.about(self, "RTSP Connect Error", "Second RTSP Server Not Connect")

    # TODO : CH 셋팅에서 전달받은 값.. ch1, ch2 ... // First RTSP, Second RTSP // [left_top_x,left_top_y,width,height]
    def setChannelRect(self, ch, rtsp_name, rect_point):

        for i in self.crop_update_thread.keys():
            if i == ch and self.crop_update_thread[i] != None:
                self.crop_update_thread[i].stop()
                self.crop_update_thread[i].wait()

        self.crop_update_thread[ch] = CropUpdateThread(rtsp_name=rtsp_name, rect_point=rect_point, ch=ch, parent=self)
        self.crop_update_thread[ch].update_pixmap_signal.connect(self.update_channel_pixmap)

        self.crop_update_thread[ch].start()


    # TODO : crop 이미지 출력을 위한 slot
    @pyqtSlot(QImage, str)
    def update_channel_pixmap(self, pixmap,ch):
        pixmap = pixmap.scaled(self.sub_screen_width, self.sub_screen_height)
        pixmap = QPixmap.fromImage(pixmap)

        try:
            if ch == 'ch3':
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
            elif ch == 'ch11':
                self.ch11.setPixmap(pixmap)
            elif ch == 'ch12':
                self.ch12.setPixmap(pixmap)

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
            for ch in self.crop_update_thread.keys():
                if self.crop_update_thread[ch] != None:
                    self.crop_update_thread[ch].stop()
                    self.crop_update_thread[ch].wait()

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

        if event.key() == Qt.Key_F5:
            self.run_first_rtsp()

        if event.key() == Qt.Key_F6:
            self.run_second_rtsp()

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
                    if channel_rect[4] == 'ch1':
                        if self.monit_thread == None:
                            self.monit_thread = MonitThread(channel_rect=channel_rect,ch='ch1')
                            self.monit_thread.update_monit_frame.connect(self.update_monit_frame)
                            self.monit_thread.start()
                        if self.monit_thread != None:
                            self.monit_thread.change_channel_rect(channel_rect=channel_rect,ch='ch1')
                        #self.monit_class.monit_label.setPixmap(ch_frame[0].copy(channel_rect[0],channel_rect[1],channel_rect[2],channel_rect[3]).scaled(1280,720))

                    if channel_rect[4] == 'ch2':
                        if self.monit_thread == None:
                            self.monit_thread = MonitThread(channel_rect=channel_rect, ch='ch2')
                            self.monit_thread.update_monit_frame.connect(self.update_monit_frame)
                            self.monit_thread.start()
                        if self.monit_thread != None:
                            self.monit_thread.change_channel_rect(channel_rect=channel_rect,ch='ch2')
                        #self.monit_class.monit_label.setPixmap(ch_frame[1].copy(channel_rect[0], channel_rect[1], channel_rect[2], channel_rect[3]).scaled(1280,720))

                    #opencv_key = cv2.waitKey(1)
                except Exception as e:
                    print(f"key handle event error :: {e}")


        key_map = {
            Qt.Key_1: (self.main1, self.ch_rect['ch1']),
            Qt.Key_2: (self.main2, self.ch_rect['ch2']),
            Qt.Key_3: (self.ch3, self.ch_rect['ch3']),
            Qt.Key_4: (self.ch4, self.ch_rect['ch4']),
            Qt.Key_5: (self.ch5, self.ch_rect['ch5']),
            Qt.Key_6: (self.ch6, self.ch_rect['ch6']),
            Qt.Key_7: (self.ch7, self.ch_rect['ch7']),
            Qt.Key_8: (self.ch8, self.ch_rect['ch8']),
            Qt.Key_9: (self.ch9, self.ch_rect['ch9']),
            Qt.Key_0: (self.ch10, self.ch_rect['ch10']),
            Qt.Key_Minus: (self.ch11, self.ch_rect['ch11']),
            Qt.Key_Slash: (self.ch11, self.ch_rect['ch11']),
            Qt.Key_Equal: (self.ch12, self.ch_rect['ch12']),
            Qt.Key_Asterisk: (self.ch12, self.ch_rect['ch12'])
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


    def draw_crop_rect(self,frame,geometry,text):

        # TODO: 해당 rect는 원본 비율의 x, y, w, h
        pixmap_with_rects = frame
        painter = QPainter(pixmap_with_rects)
        pen = QPen(Qt.green)
        pen.setWidth(3)
        painter.setPen(pen)

        font = QFont()
        font.setFamily('Times')
        font.setBold(True)
        font.setPointSize(15)
        painter.setFont(font)

        x, y, w, h = geometry
        rect = QRect(x, y, w, h)
        painter.drawRect(rect)
        painter.drawText(round((w)/2+x-17), round((h/2)+y+5) ,text)  # rect 위에 key 값을 글자로 씀

        return pixmap_with_rects

    # TODO : main1, main2 화면에 출력 ( Rect ) signal 받는 slot 함수
    @pyqtSlot(np.ndarray, str)
    def update_frame(self, frame, name):
        global ch_frame

        h, w, c = frame.shape
        qImg = QImage(frame.data, w, h, w * c, QImage.Format.Format_BGR888)
        pixmap = QPixmap.fromImage(qImg)

        if name == 'first':
            ch_frame[0] = pixmap
            main_frame = pixmap.scaled(self.main_screen_width,self.main_screen_height)

            self.ch_rect['ch1'] = [0, 0, w, h,'ch1']

            for i in self.ch_rect.keys():
                try:
                    if i == 'ch1' or i == 'ch2':
                        continue
                    if self.ch_rect[i] != None and self.ch_rect[i][4] == 'ch1':
                        x,y,w,h = self.ch_rect[i][:4]
                        witdh_rate = self.main_screen_width/self.ch_rect['ch1'][2]
                        height_rate = self.main_screen_height/self.ch_rect['ch1'][3]
                        x = round(x*witdh_rate)
                        y = round(y*height_rate)
                        w = round(w*witdh_rate)
                        h = round(h*height_rate)
                        main_frame = self.draw_crop_rect(frame=main_frame,geometry=(x,y,w,h),text=i).copy()
                        
                except Exception as e:
                    print(f"draw_rect_errorr :: {e}")
                    continue


            #self.main1.setPixmap(main_frame.scaled(self.main_screen_width, self.main_screen_height))
            self.main1.setPixmap(main_frame)


        if name == 'second':
            ch_frame[1] = pixmap
            main_frame = pixmap.scaled(self.main_screen_width,self.main_screen_height)
            self.ch_rect['ch2'] = [0, 0, w, h,'ch2']

            for i in self.ch_rect.keys():
                try:
                    if i == 'ch1' or i == 'ch2':
                        continue
                    if self.ch_rect[i] != None and self.ch_rect[i][4] == 'ch2':
                        x, y, w, h = self.ch_rect[i][:4]
                        witdh_rate = self.main_screen_width / self.ch_rect['ch2'][2]
                        height_rate = self.main_screen_height / self.ch_rect['ch2'][3]
                        x = round(x * witdh_rate)
                        y = round(y * height_rate)
                        w = round(w * witdh_rate)
                        h = round(h * height_rate)
                        main_frame = self.draw_crop_rect(frame=main_frame, geometry=(x, y, w, h), text=i).copy()

                except Exception as e:
                    print(f"draw_rect_errorr :: {e}")
                    continue

            #self.main2.setPixmap(main_frame.scaled(self.main_screen_width, self.main_screen_height))
            self.main2.setPixmap(main_frame)



    def qpixmapToOpencv(self,qpixmap):
        # QPixmap을 QImage로 변환
        qimage = qpixmap.toImage()
        qimage = qimage.convertToFormat(QImage.Format.Format_RGBA8888)

        # QImage의 버퍼를 NumPy 배열로 변환
        width = qimage.width()
        height = qimage.height()
        ptr = qimage.bits()
        ptr.setsize(qimage.byteCount())
        arr = np.array(ptr).reshape(height, width, 4)  # RGBA 형식의 4채널 이미지

        # OpenCV에서 사용할 수 있도록 BGR 형식으로 변환
        cv_img = cv2.cvtColor(arr, cv2.COLOR_RGBA2BGRA)
        return cv_img

if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)
        myWindow = WindowClass()
        myWindow.showMaximized()
        sys.exit(app.exec_())
    except Exception as e:
        print(e)
