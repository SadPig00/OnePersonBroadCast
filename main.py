import json
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
from Functions.get_rotate_points import get_rotate_point
import requests
import ast

#global ch_frame
global main1_frame
global main2_frame
global main3_frame

global selected_main1
global selected_main2
global selected_main3
global start_rtsp1
global start_rtsp2
global start_rtsp3

#global isCrop
#isCrop = False
global frame_mutex

frame_mutex = QMutex()

start_rtsp1 = False
start_rtsp2 = False
start_rtsp3 = False

selected_main1 = False
selected_main2 = False
selected_main3 = False

main1_frame = None
main2_frame = None
main3_frame = None

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
                                self.msleep(int(Config.config['ABS']['mtime_delay'])) # RTSP 서버와의 딜레이 조정
                                pitchInfo = data
                                pitch_temp = data
                                abs_start_time = time.time()
                            elif time.time() - abs_start_time > float(Config.config['ABS']['ball_reset_time']):
                                abs_start_time = 0
                                pitchInfo = None

                        if 'error' in data.keys():
                            pitchInfo = None
                        break
                self.msleep(100)
            except Exception as e:
                pitchInfo = None
                print(f"request fail :: {e}")

    def stop(self):
        self.working = False
        self.quit()
        self.wait(2000)

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

    def __init__(self, parent, url, name):
        super().__init__()
        self.parent = parent
        self.url = url
        self.name = name
        self.working = True

    def run(self):
        global video_fps
        global start_rtsp1
        global start_rtsp2
        global start_rtsp3
        global main1_frame
        global main2_frame
        global main3_frame
        global monit_fps
        global selected_main1
        global selected_main2
        global selected_main3


        #global isCrop
        try:
            self.main_monit_limit = int(Config.config['PROGRAM']['main_monit_testing'])
            cap = cv2.VideoCapture(self.url)
            frame_count = 0
            crop_frame_count = 1

            if self.name == 'first':
                start_rtsp1 = False
            if self.name == 'second':
                start_rtsp2 = False
            if self.name == 'third':
                start_rtsp3 = False

            global frame_mutex

            while cap.isOpened() and self.working:

                ret, frame = cap.read()

                if not ret:
                    # TODO : 인터넷 속도 문제로 RTSP 서버 끊겼을시 재접속
                    frame_count += 1
                    if frame_count == 1000:
                        cap = cv2.VideoCapture(self.url)
                        frame_count = 0
                        crop_frame_count = 1
                        if self.name == 'first':
                            start_rtsp1 = False
                        if self.name == 'second':
                            start_rtsp2 = False
                        if self.name == 'third':
                            start_rtsp3 = False

                    continue

                crop_frame_count += 1
                if crop_frame_count == video_fps+1:
                    crop_frame_count = 1


                crop_frame = None

                if self.name == 'first':
                    try:
                        #if not start_rtsp1:
                        if not start_rtsp1 and crop_frame_count % round(30/monit_fps) == 0:
                            h, w, c = frame.shape
                            qImg = QImage(frame.data, w, h, w * c, QImage.Format.Format_BGR888)
                            pixmap = QPixmap.fromImage(qImg)

                            width_rate = self.parent.main_screen_width / w
                            height_rate = self.parent.main_screen_height / h
                            
                            resize_image = pixmap.scaled(self.parent.main_screen_width, self.parent.main_screen_height)


                            for i in self.parent.ch_rect.keys():
                                if self.parent.ch_rect[i] != None and self.parent.ch_rect[i][4] == 'RTSP_1':
                                    # TODO : 초기 crop 화면을 이미지로 넣기 위한 전처리
                                    if i == 'ch1':
                                        if self.parent.ch_rect[i][6] != 0 :
                                            self.parent.ch1.setPixmap(self.parent.get_rotate_image(i,resize_image,width_rate,height_rate,self.parent.sub_screen_width, self.parent.sub_screen_height))
                                        else:
                                            self.parent.ch1.setPixmap(
                                                resize_image.copy(round(self.parent.ch_rect[i][0] * width_rate),
                                                                  round(self.parent.ch_rect[i][1] * height_rate),
                                                                  round(self.parent.ch_rect[i][2] * width_rate),
                                                                  round(self.parent.ch_rect[i][3] * height_rate)).scaled(
                                                    self.parent.sub_screen_width, self.parent.sub_screen_height))

                                    elif i == 'ch2':
                                        if self.parent.ch_rect[i][6] != 0:
                                            self.parent.ch2.setPixmap(
                                                self.parent.get_rotate_image(i, resize_image, width_rate, height_rate,
                                                                             self.parent.sub_screen_width,
                                                                             self.parent.sub_screen_height))
                                        else:
                                            self.parent.ch2.setPixmap(
                                                resize_image.copy(round(self.parent.ch_rect[i][0] * width_rate),
                                                                  round(self.parent.ch_rect[i][1] * height_rate),
                                                                  round(self.parent.ch_rect[i][2] * width_rate),
                                                                  round(
                                                                      self.parent.ch_rect[i][3] * height_rate)).scaled(
                                                    self.parent.sub_screen_width, self.parent.sub_screen_height))
                                    elif i == 'ch3':
                                        if self.parent.ch_rect[i][6] != 0:
                                            self.parent.ch3.setPixmap(
                                                self.parent.get_rotate_image(i, resize_image, width_rate, height_rate,
                                                                             self.parent.sub_screen_width,
                                                                             self.parent.sub_screen_height))
                                        else:
                                            self.parent.ch3.setPixmap(
                                                resize_image.copy(round(self.parent.ch_rect[i][0] * width_rate),
                                                                  round(self.parent.ch_rect[i][1] * height_rate),
                                                                  round(self.parent.ch_rect[i][2] * width_rate),
                                                                  round(
                                                                      self.parent.ch_rect[i][3] * height_rate)).scaled(
                                                    self.parent.sub_screen_width, self.parent.sub_screen_height))
                                    elif i == 'ch4':
                                        if self.parent.ch_rect[i][6] != 0:
                                            self.parent.ch4.setPixmap(
                                                self.parent.get_rotate_image(i, resize_image, width_rate, height_rate,
                                                                             self.parent.sub_screen_width,
                                                                             self.parent.sub_screen_height))
                                        else:
                                            self.parent.ch4.setPixmap(
                                                resize_image.copy(round(self.parent.ch_rect[i][0] * width_rate),
                                                                  round(self.parent.ch_rect[i][1] * height_rate),
                                                                  round(self.parent.ch_rect[i][2] * width_rate),
                                                                  round(
                                                                      self.parent.ch_rect[i][3] * height_rate)).scaled(
                                                    self.parent.sub_screen_width, self.parent.sub_screen_height))
                                    elif i == 'ch5':
                                        if self.parent.ch_rect[i][6] != 0:
                                            self.parent.ch5.setPixmap(
                                                self.parent.get_rotate_image(i, resize_image, width_rate, height_rate,
                                                                             self.parent.sub_screen_width,
                                                                             self.parent.sub_screen_height))
                                        else:
                                            self.parent.ch5.setPixmap(
                                                resize_image.copy(round(self.parent.ch_rect[i][0] * width_rate),
                                                                  round(self.parent.ch_rect[i][1] * height_rate),
                                                                  round(self.parent.ch_rect[i][2] * width_rate),
                                                                  round(
                                                                      self.parent.ch_rect[i][3] * height_rate)).scaled(
                                                    self.parent.sub_screen_width, self.parent.sub_screen_height))
                                    elif i == 'ch6':
                                        if self.parent.ch_rect[i][6] != 0:
                                            self.parent.ch6.setPixmap(
                                                self.parent.get_rotate_image(i, resize_image, width_rate, height_rate,
                                                                             self.parent.sub_screen_width,
                                                                             self.parent.sub_screen_height))
                                        else:
                                            self.parent.ch6.setPixmap(
                                                resize_image.copy(round(self.parent.ch_rect[i][0] * width_rate),
                                                                  round(self.parent.ch_rect[i][1] * height_rate),
                                                                  round(self.parent.ch_rect[i][2] * width_rate),
                                                                  round(
                                                                      self.parent.ch_rect[i][3] * height_rate)).scaled(
                                                    self.parent.sub_screen_width, self.parent.sub_screen_height))
                                    elif i == 'ch7':
                                        if self.parent.ch_rect[i][6] != 0:
                                            self.parent.ch7.setPixmap(
                                                self.parent.get_rotate_image(i, resize_image, width_rate, height_rate,
                                                                             self.parent.sub_screen_width,
                                                                             self.parent.sub_screen_height))
                                        else:
                                            self.parent.ch7.setPixmap(
                                                resize_image.copy(round(self.parent.ch_rect[i][0] * width_rate),
                                                                  round(self.parent.ch_rect[i][1] * height_rate),
                                                                  round(self.parent.ch_rect[i][2] * width_rate),
                                                                  round(
                                                                      self.parent.ch_rect[i][3] * height_rate)).scaled(
                                                    self.parent.sub_screen_width, self.parent.sub_screen_height))
                                    elif i == 'ch8':
                                        if self.parent.ch_rect[i][6] != 0:
                                            self.parent.ch8.setPixmap(
                                                self.parent.get_rotate_image(i, resize_image, width_rate, height_rate,
                                                                             self.parent.sub_screen_width,
                                                                             self.parent.sub_screen_height))
                                        else:
                                            self.parent.ch8.setPixmap(
                                                resize_image.copy(round(self.parent.ch_rect[i][0] * width_rate),
                                                                  round(self.parent.ch_rect[i][1] * height_rate),
                                                                  round(self.parent.ch_rect[i][2] * width_rate),
                                                                  round(
                                                                      self.parent.ch_rect[i][3] * height_rate)).scaled(
                                                    self.parent.sub_screen_width, self.parent.sub_screen_height))
                                    elif i == 'ch9':
                                        if self.parent.ch_rect[i][6] != 0:
                                            self.parent.ch9.setPixmap(
                                                self.parent.get_rotate_image(i, resize_image, width_rate, height_rate,
                                                                             self.parent.sub_screen_width,
                                                                             self.parent.sub_screen_height))
                                        else:
                                            self.parent.ch9.setPixmap(
                                                resize_image.copy(round(self.parent.ch_rect[i][0] * width_rate),
                                                                  round(self.parent.ch_rect[i][1] * height_rate),
                                                                  round(self.parent.ch_rect[i][2] * width_rate),
                                                                  round(
                                                                      self.parent.ch_rect[i][3] * height_rate)).scaled(
                                                    self.parent.sub_screen_width, self.parent.sub_screen_height))
                                    elif i == 'ch10':
                                        if self.parent.ch_rect[i][6] != 0:
                                            self.parent.ch10.setPixmap(
                                                self.parent.get_rotate_image(i, resize_image, width_rate, height_rate,
                                                                             self.parent.sub_screen_width,
                                                                             self.parent.sub_screen_height))
                                        else:
                                            self.parent.ch10.setPixmap(
                                                resize_image.copy(round(self.parent.ch_rect[i][0] * width_rate),
                                                                  round(self.parent.ch_rect[i][1] * height_rate),
                                                                  round(self.parent.ch_rect[i][2] * width_rate),
                                                                  round(
                                                                      self.parent.ch_rect[i][3] * height_rate)).scaled(
                                                    self.parent.sub_screen_width, self.parent.sub_screen_height))
                            if Config.config['PROGRAM']['iscrop_move'] != 'true':
                                  start_rtsp1 = True
                    except Exception as e:
                        print(f"초기 crop 이미지 오류 :: {e}")
                    try:

                        if selected_main1 == True or main1_frame == None:# or isCrop:
                            h, w, c = frame.shape
                            qImg = QImage(frame.data, w, h, w * c, QImage.Format.Format_BGR888)
                            pixmap = QPixmap.fromImage(qImg)
                            #frame_mutex.lock()
                            main1_frame = pixmap
                            #isCrop = False
                            #frame_mutex.unlock()

                        if crop_frame_count % round(30/self.main_monit_limit) != 0:
                            self.msleep(1)
                            continue


                        if selected_main1 != True:
                            h, w, c = frame.shape
                            qImg = QImage(frame.data, w, h, w * c, QImage.Format.Format_BGR888)
                            pixmap = QPixmap.fromImage(qImg)


                        main_frame = pixmap.scaled(self.parent.main_screen_width, self.parent.main_screen_height)


                        # if crop_frame_count % round(video_fps/monit_fps) == 0:
                        #    crop_frame = main_frame.copy()

                        self.parent.ch_rect['RTSP_1'] = [0, 0, w, h, 'RTSP_1', False, 0]

                        for i in self.parent.ch_rect.keys():
                            try:
                                if i == 'RTSP_2' or i == 'RTSP_3':
                                    continue
                                if self.parent.ch_rect[i] != None and self.parent.ch_rect[i][4] == 'RTSP_1':
                                    x, y, w, h = self.parent.ch_rect[i][:4]
                                    width_rate = self.parent.main_screen_width / self.parent.ch_rect['RTSP_1'][2]
                                    height_rate = self.parent.main_screen_height / self.parent.ch_rect['RTSP_1'][3]
                                    x = round(x * width_rate)
                                    y = round(y * height_rate)
                                    w = round(w * width_rate)
                                    h = round(h * height_rate)
                                    main_frame = self.draw_crop_rect(frame=main_frame, geometry=(x, y, w, h),
                                                                     text=f'{i}\n{self.parent.ch_rect[i][2]}x{self.parent.ch_rect[i][3]}',
                                                                     ch=i, selected=self.parent.ch_rect[i][5],
                                                                     rotate=self.parent.ch_rect[i][6])
                                    # main_frame = self.draw_crop_rect(frame=main_frame, geometry=(x, y, w, h),text=f'{i}', ch=i,selected=self.ch_rect[i][5]).copy()
                                    """
                                    if crop_frame_count % round(video_fps/monit_fps) != 0 or crop_frame == None:
                                        continue
                                    elif i == 'ch1':
                                        self.ch1.setPixmap(crop_frame.copy(round(self.ch_rect[i][0]*width_rate),round(self.ch_rect[i][1]*height_rate),round(self.ch_rect[i][2]*width_rate),round(self.ch_rect[i][3]*height_rate)).scaled(self.sub_screen_width,self.sub_screen_height))
                                    elif i == 'ch2':
                                        self.ch2.setPixmap(crop_frame.copy(round(self.ch_rect[i][0]*width_rate),round(self.ch_rect[i][1]*height_rate),round(self.ch_rect[i][2]*width_rate),round(self.ch_rect[i][3]*height_rate)).scaled(self.sub_screen_width,self.sub_screen_height))
                                    elif i == 'ch3':
                                        self.ch3.setPixmap(crop_frame.copy(round(self.ch_rect[i][0]*width_rate),round(self.ch_rect[i][1]*height_rate),round(self.ch_rect[i][2]*width_rate),round(self.ch_rect[i][3]*height_rate)).scaled(self.sub_screen_width,self.sub_screen_height))
                                    elif i == 'ch4':
                                        self.ch4.setPixmap(crop_frame.copy(round(self.ch_rect[i][0]*width_rate),round(self.ch_rect[i][1]*height_rate),round(self.ch_rect[i][2]*width_rate),round(self.ch_rect[i][3]*height_rate)).scaled(self.sub_screen_width,self.sub_screen_height))
                                    elif i == 'ch5':
                                        self.ch5.setPixmap(crop_frame.copy(round(self.ch_rect[i][0]*width_rate),round(self.ch_rect[i][1]*height_rate),round(self.ch_rect[i][2]*width_rate),round(self.ch_rect[i][3]*height_rate)).scaled(self.sub_screen_width,self.sub_screen_height))
                                    elif i == 'ch6':
                                        self.ch6.setPixmap(crop_frame.copy(round(self.ch_rect[i][0]*width_rate),round(self.ch_rect[i][1]*height_rate),round(self.ch_rect[i][2]*width_rate),round(self.ch_rect[i][3]*height_rate)).scaled(self.sub_screen_width,self.sub_screen_height))
                                    elif i == 'ch7':
                                        self.ch7.setPixmap(crop_frame.copy(round(self.ch_rect[i][0]*width_rate),round(self.ch_rect[i][1]*height_rate),round(self.ch_rect[i][2]*width_rate),round(self.ch_rect[i][3]*height_rate)).scaled(self.sub_screen_width,self.sub_screen_height))
                                    elif i == 'ch8':
                                        self.ch8.setPixmap(crop_frame.copy(round(self.ch_rect[i][0]*width_rate),round(self.ch_rect[i][1]*height_rate),round(self.ch_rect[i][2]*width_rate),round(self.ch_rect[i][3]*height_rate)).scaled(self.sub_screen_width,self.sub_screen_height))
                                    elif i == 'ch9':
                                        self.ch9.setPixmap(crop_frame.copy(round(self.ch_rect[i][0]*width_rate),round(self.ch_rect[i][1]*height_rate),round(self.ch_rect[i][2]*width_rate),round(self.ch_rect[i][3]*height_rate)).scaled(self.sub_screen_width,self.sub_screen_height))
                                    elif i == 'ch10':
                                        self.ch10.setPixmap(crop_frame.copy(round(self.ch_rect[i][0]*width_rate),round(self.ch_rect[i][1]*height_rate),round(self.ch_rect[i][2]*width_rate),round(self.ch_rect[i][3]*height_rate)).scaled(self.sub_screen_width,self.sub_screen_height))
                                    """
                            except Exception as e:
                                print(f"draw_rect_errorr :: {e}")
                                continue
                        #frame_mutex.lock()

                        self.parent.main1.setPixmap(main_frame)
                        #frame_mutex.unlock()
                        # self.main1.setPixmap(main_frame.scaled(self.main_screen_width, self.main_screen_height))
                    except Exception as e:
                        print(f"setPixmap main errer :: {e}")
                    self.msleep(int(Config.config['PROGRAM']['msleep_rtsp1']))
                    #self.update_frame.emit(frame, self.name, crop_frame_count)


                if self.name == 'second':
                    try:
                        #if not start_rtsp2:
                        if not start_rtsp2 and crop_frame_count % round(30/monit_fps) == 0:
                            h, w, c = frame.shape
                            qImg = QImage(frame.data, w, h, w * c, QImage.Format.Format_BGR888)
                            pixmap = QPixmap.fromImage(qImg)

                            width_rate = self.parent.main_screen_width / w
                            height_rate = self.parent.main_screen_height / h
                            resize_image = pixmap.scaled(self.parent.main_screen_width, self.parent.main_screen_height)
                            for i in self.parent.ch_rect.keys():
                                if self.parent.ch_rect[i] != None and self.parent.ch_rect[i][4] == 'RTSP_2':
                                    # TODO : 초기 crop 화면을 이미지로 넣기 위한 전처리
                                    if i == 'ch1':
                                        if self.parent.ch_rect[i][6] != 0:
                                            self.parent.ch1.setPixmap(
                                                self.parent.get_rotate_image(i, resize_image, width_rate, height_rate,
                                                                             self.parent.sub_screen_width,
                                                                             self.parent.sub_screen_height))
                                        else:
                                            self.parent.ch1.setPixmap(
                                                resize_image.copy(round(self.parent.ch_rect[i][0] * width_rate),
                                                                  round(self.parent.ch_rect[i][1] * height_rate),
                                                                  round(self.parent.ch_rect[i][2] * width_rate),
                                                                  round(
                                                                      self.parent.ch_rect[i][3] * height_rate)).scaled(
                                                    self.parent.sub_screen_width, self.parent.sub_screen_height))

                                    elif i == 'ch2':
                                        if self.parent.ch_rect[i][6] != 0:
                                            self.parent.ch2.setPixmap(
                                                self.parent.get_rotate_image(i, resize_image, width_rate, height_rate,
                                                                             self.parent.sub_screen_width,
                                                                             self.parent.sub_screen_height))
                                        else:
                                            self.parent.ch2.setPixmap(
                                                resize_image.copy(round(self.parent.ch_rect[i][0] * width_rate),
                                                                  round(self.parent.ch_rect[i][1] * height_rate),
                                                                  round(self.parent.ch_rect[i][2] * width_rate),
                                                                  round(
                                                                      self.parent.ch_rect[i][3] * height_rate)).scaled(
                                                    self.parent.sub_screen_width, self.parent.sub_screen_height))
                                    elif i == 'ch3':
                                        if self.parent.ch_rect[i][6] != 0:
                                            self.parent.ch3.setPixmap(
                                                self.parent.get_rotate_image(i, resize_image, width_rate, height_rate,
                                                                             self.parent.sub_screen_width,
                                                                             self.parent.sub_screen_height))
                                        else:
                                            self.parent.ch3.setPixmap(
                                                resize_image.copy(round(self.parent.ch_rect[i][0] * width_rate),
                                                                  round(self.parent.ch_rect[i][1] * height_rate),
                                                                  round(self.parent.ch_rect[i][2] * width_rate),
                                                                  round(
                                                                      self.parent.ch_rect[i][3] * height_rate)).scaled(
                                                    self.parent.sub_screen_width, self.parent.sub_screen_height))
                                    elif i == 'ch4':
                                        if self.parent.ch_rect[i][6] != 0:
                                            self.parent.ch4.setPixmap(
                                                self.parent.get_rotate_image(i, resize_image, width_rate, height_rate,
                                                                             self.parent.sub_screen_width,
                                                                             self.parent.sub_screen_height))
                                        else:
                                            self.parent.ch4.setPixmap(
                                                resize_image.copy(round(self.parent.ch_rect[i][0] * width_rate),
                                                                  round(self.parent.ch_rect[i][1] * height_rate),
                                                                  round(self.parent.ch_rect[i][2] * width_rate),
                                                                  round(
                                                                      self.parent.ch_rect[i][3] * height_rate)).scaled(
                                                    self.parent.sub_screen_width, self.parent.sub_screen_height))
                                    elif i == 'ch5':
                                        if self.parent.ch_rect[i][6] != 0:
                                            self.parent.ch5.setPixmap(
                                                self.parent.get_rotate_image(i, resize_image, width_rate, height_rate,
                                                                             self.parent.sub_screen_width,
                                                                             self.parent.sub_screen_height))
                                        else:
                                            self.parent.ch5.setPixmap(
                                                resize_image.copy(round(self.parent.ch_rect[i][0] * width_rate),
                                                                  round(self.parent.ch_rect[i][1] * height_rate),
                                                                  round(self.parent.ch_rect[i][2] * width_rate),
                                                                  round(
                                                                      self.parent.ch_rect[i][3] * height_rate)).scaled(
                                                    self.parent.sub_screen_width, self.parent.sub_screen_height))
                                    elif i == 'ch6':
                                        if self.parent.ch_rect[i][6] != 0:
                                            self.parent.ch6.setPixmap(
                                                self.parent.get_rotate_image(i, resize_image, width_rate, height_rate,
                                                                             self.parent.sub_screen_width,
                                                                             self.parent.sub_screen_height))
                                        else:
                                            self.parent.ch6.setPixmap(
                                                resize_image.copy(round(self.parent.ch_rect[i][0] * width_rate),
                                                                  round(self.parent.ch_rect[i][1] * height_rate),
                                                                  round(self.parent.ch_rect[i][2] * width_rate),
                                                                  round(
                                                                      self.parent.ch_rect[i][3] * height_rate)).scaled(
                                                    self.parent.sub_screen_width, self.parent.sub_screen_height))
                                    elif i == 'ch7':
                                        if self.parent.ch_rect[i][6] != 0:
                                            self.parent.ch7.setPixmap(
                                                self.parent.get_rotate_image(i, resize_image, width_rate, height_rate,
                                                                             self.parent.sub_screen_width,
                                                                             self.parent.sub_screen_height))
                                        else:
                                            self.parent.ch7.setPixmap(
                                                resize_image.copy(round(self.parent.ch_rect[i][0] * width_rate),
                                                                  round(self.parent.ch_rect[i][1] * height_rate),
                                                                  round(self.parent.ch_rect[i][2] * width_rate),
                                                                  round(
                                                                      self.parent.ch_rect[i][3] * height_rate)).scaled(
                                                    self.parent.sub_screen_width, self.parent.sub_screen_height))
                                    elif i == 'ch8':
                                        if self.parent.ch_rect[i][6] != 0:
                                            self.parent.ch8.setPixmap(
                                                self.parent.get_rotate_image(i, resize_image, width_rate, height_rate,
                                                                             self.parent.sub_screen_width,
                                                                             self.parent.sub_screen_height))
                                        else:
                                            self.parent.ch8.setPixmap(
                                                resize_image.copy(round(self.parent.ch_rect[i][0] * width_rate),
                                                                  round(self.parent.ch_rect[i][1] * height_rate),
                                                                  round(self.parent.ch_rect[i][2] * width_rate),
                                                                  round(
                                                                      self.parent.ch_rect[i][3] * height_rate)).scaled(
                                                    self.parent.sub_screen_width, self.parent.sub_screen_height))
                                    elif i == 'ch9':
                                        if self.parent.ch_rect[i][6] != 0:
                                            self.parent.ch9.setPixmap(
                                                self.parent.get_rotate_image(i, resize_image, width_rate, height_rate,
                                                                             self.parent.sub_screen_width,
                                                                             self.parent.sub_screen_height))
                                        else:
                                            self.parent.ch9.setPixmap(
                                                resize_image.copy(round(self.parent.ch_rect[i][0] * width_rate),
                                                                  round(self.parent.ch_rect[i][1] * height_rate),
                                                                  round(self.parent.ch_rect[i][2] * width_rate),
                                                                  round(
                                                                      self.parent.ch_rect[i][3] * height_rate)).scaled(
                                                    self.parent.sub_screen_width, self.parent.sub_screen_height))
                                    elif i == 'ch10':
                                        if self.parent.ch_rect[i][6] != 0:
                                            self.parent.ch10.setPixmap(
                                                self.parent.get_rotate_image(i, resize_image, width_rate, height_rate,
                                                                             self.parent.sub_screen_width,
                                                                             self.parent.sub_screen_height))
                                        else:
                                            self.parent.ch10.setPixmap(
                                                resize_image.copy(round(self.parent.ch_rect[i][0] * width_rate),
                                                                  round(self.parent.ch_rect[i][1] * height_rate),
                                                                  round(self.parent.ch_rect[i][2] * width_rate),
                                                                  round(
                                                                      self.parent.ch_rect[i][3] * height_rate)).scaled(
                                                    self.parent.sub_screen_width, self.parent.sub_screen_height))
                            if Config.config['PROGRAM']['iscrop_move'] != 'true':
                                start_rtsp2 = True
                    except Exception as e:
                        print(f"초기 crop 이미지 오류 :: {e}")
                    try:
                        if selected_main2 == True or main2_frame == None:# or isCrop:
                            h, w, c = frame.shape
                            qImg = QImage(frame.data, w, h, w * c, QImage.Format.Format_BGR888)
                            pixmap = QPixmap.fromImage(qImg)
                            #frame_mutex.lock()
                            main2_frame = pixmap
                            #isCrop = False
                            #frame_mutex.unlock()
                        if crop_frame_count % round(30/self.main_monit_limit) != 0:
                            self.msleep(1)
                            continue

                        if selected_main2 != True :
                            h, w, c = frame.shape
                            qImg = QImage(frame.data, w, h, w * c, QImage.Format.Format_BGR888)
                            pixmap = QPixmap.fromImage(qImg)

                        main_frame = pixmap.scaled(self.parent.main_screen_width, self.parent.main_screen_height)


                        # if crop_frame_count % round(video_fps/monit_fps) == 0:
                        #    crop_frame = main_frame.copy()

                        self.parent.ch_rect['RTSP_2'] = [0, 0, w, h, 'RTSP_2', False, 0]

                        for i in self.parent.ch_rect.keys():
                            try:
                                if i == 'RTSP_1' or i == 'RTSP_3':
                                    continue
                                if self.parent.ch_rect[i] != None and self.parent.ch_rect[i][4] == 'RTSP_2':
                                    x, y, w, h = self.parent.ch_rect[i][:4]
                                    width_rate = self.parent.main_screen_width / self.parent.ch_rect['RTSP_2'][2]
                                    height_rate = self.parent.main_screen_height / self.parent.ch_rect['RTSP_2'][3]
                                    x = round(x * width_rate)
                                    y = round(y * height_rate)
                                    w = round(w * width_rate)
                                    h = round(h * height_rate)
                                    main_frame = self.draw_crop_rect(frame=main_frame, geometry=(x, y, w, h),
                                                                     text=f'{i}\n{self.parent.ch_rect[i][2]}x{self.parent.ch_rect[i][3]}',
                                                                     ch=i, selected=self.parent.ch_rect[i][5],
                                                                     rotate=self.parent.ch_rect[i][6])
                                    # main_frame = self.draw_crop_rect(frame=main_frame, geometry=(x, y, w, h),text=f'{i}', ch=i,selected=self.ch_rect[i][5]).copy()
                                    """
                                    if crop_frame_count % round(video_fps/monit_fps) != 0 or crop_frame == None:
                                        continue
                                    elif i == 'ch1':
                                        self.ch1.setPixmap(crop_frame.copy(round(self.ch_rect[i][0]*width_rate),round(self.ch_rect[i][1]*height_rate),round(self.ch_rect[i][2]*width_rate),round(self.ch_rect[i][3]*height_rate)).scaled(self.sub_screen_width,self.sub_screen_height))
                                    elif i == 'ch2':
                                        self.ch2.setPixmap(crop_frame.copy(round(self.ch_rect[i][0]*width_rate),round(self.ch_rect[i][1]*height_rate),round(self.ch_rect[i][2]*width_rate),round(self.ch_rect[i][3]*height_rate)).scaled(self.sub_screen_width,self.sub_screen_height))
                                    elif i == 'ch3':
                                        self.ch3.setPixmap(crop_frame.copy(round(self.ch_rect[i][0]*width_rate),round(self.ch_rect[i][1]*height_rate),round(self.ch_rect[i][2]*width_rate),round(self.ch_rect[i][3]*height_rate)).scaled(self.sub_screen_width,self.sub_screen_height))
                                    elif i == 'ch4':
                                        self.ch4.setPixmap(crop_frame.copy(round(self.ch_rect[i][0]*width_rate),round(self.ch_rect[i][1]*height_rate),round(self.ch_rect[i][2]*width_rate),round(self.ch_rect[i][3]*height_rate)).scaled(self.sub_screen_width,self.sub_screen_height))
                                    elif i == 'ch5':
                                        self.ch5.setPixmap(crop_frame.copy(round(self.ch_rect[i][0]*width_rate),round(self.ch_rect[i][1]*height_rate),round(self.ch_rect[i][2]*width_rate),round(self.ch_rect[i][3]*height_rate)).scaled(self.sub_screen_width,self.sub_screen_height))
                                    elif i == 'ch6':
                                        self.ch6.setPixmap(crop_frame.copy(round(self.ch_rect[i][0]*width_rate),round(self.ch_rect[i][1]*height_rate),round(self.ch_rect[i][2]*width_rate),round(self.ch_rect[i][3]*height_rate)).scaled(self.sub_screen_width,self.sub_screen_height))
                                    elif i == 'ch7':
                                        self.ch7.setPixmap(crop_frame.copy(round(self.ch_rect[i][0]*width_rate),round(self.ch_rect[i][1]*height_rate),round(self.ch_rect[i][2]*width_rate),round(self.ch_rect[i][3]*height_rate)).scaled(self.sub_screen_width,self.sub_screen_height))
                                    elif i == 'ch8':
                                        self.ch8.setPixmap(crop_frame.copy(round(self.ch_rect[i][0]*width_rate),round(self.ch_rect[i][1]*height_rate),round(self.ch_rect[i][2]*width_rate),round(self.ch_rect[i][3]*height_rate)).scaled(self.sub_screen_width,self.sub_screen_height))
                                    elif i == 'ch9':
                                        self.ch9.setPixmap(crop_frame.copy(round(self.ch_rect[i][0]*width_rate),round(self.ch_rect[i][1]*height_rate),round(self.ch_rect[i][2]*width_rate),round(self.ch_rect[i][3]*height_rate)).scaled(self.sub_screen_width,self.sub_screen_height))
                                    elif i == 'ch10':
                                        self.ch10.setPixmap(crop_frame.copy(round(self.ch_rect[i][0]*width_rate),round(self.ch_rect[i][1]*height_rate),round(self.ch_rect[i][2]*width_rate),round(self.ch_rect[i][3]*height_rate)).scaled(self.sub_screen_width,self.sub_screen_height))
                                    """
                            except Exception as e:
                                print(f"draw_rect_errorr :: {e}")
                                continue
                        #frame_mutex.lock()
                        self.parent.main2.setPixmap(main_frame)
                        #frame_mutex.unlock()
                        # self.main1.setPixmap(main_frame.scaled(self.main_screen_width, self.main_screen_height))
                    except Exception as e:
                        print(f"setPixmap main errer :: {e}")

                    self.msleep(int(Config.config['PROGRAM']['msleep_rtsp2']))
                    #self.update_frame.emit(frame, self.name, crop_frame_count)

                if self.name == 'third':
                    try:
                        #if not start_rtsp3:
                        if not start_rtsp3 and crop_frame_count % round(30/monit_fps) == 0:
                            h, w, c = frame.shape
                            qImg = QImage(frame.data, w, h, w * c, QImage.Format.Format_BGR888)
                            pixmap = QPixmap.fromImage(qImg)

                            width_rate = self.parent.main_screen_width / w
                            height_rate = self.parent.main_screen_height / h
                            resize_image = pixmap.scaled(self.parent.main_screen_width, self.parent.main_screen_height)

                            for i in self.parent.ch_rect.keys():
                                if self.parent.ch_rect[i] != None and self.parent.ch_rect[i][4] == 'RTSP_3':
                                    # TODO : 초기 crop 화면을 이미지로 넣기 위한 전처리
                                    if i == 'ch1':
                                        if self.parent.ch_rect[i][6] != 0:
                                            self.parent.ch1.setPixmap(
                                                self.parent.get_rotate_image(i, resize_image, width_rate, height_rate,
                                                                             self.parent.sub_screen_width,
                                                                             self.parent.sub_screen_height))
                                        else:
                                            self.parent.ch1.setPixmap(
                                                resize_image.copy(round(self.parent.ch_rect[i][0] * width_rate),
                                                                  round(self.parent.ch_rect[i][1] * height_rate),
                                                                  round(self.parent.ch_rect[i][2] * width_rate),
                                                                  round(
                                                                      self.parent.ch_rect[i][3] * height_rate)).scaled(
                                                    self.parent.sub_screen_width, self.parent.sub_screen_height))

                                    elif i == 'ch2':
                                        if self.parent.ch_rect[i][6] != 0:
                                            self.parent.ch2.setPixmap(
                                                self.parent.get_rotate_image(i, resize_image, width_rate, height_rate,
                                                                             self.parent.sub_screen_width,
                                                                             self.parent.sub_screen_height))
                                        else:
                                            self.parent.ch2.setPixmap(
                                                resize_image.copy(round(self.parent.ch_rect[i][0] * width_rate),
                                                                  round(self.parent.ch_rect[i][1] * height_rate),
                                                                  round(self.parent.ch_rect[i][2] * width_rate),
                                                                  round(
                                                                      self.parent.ch_rect[i][3] * height_rate)).scaled(
                                                    self.parent.sub_screen_width, self.parent.sub_screen_height))
                                    elif i == 'ch3':
                                        if self.parent.ch_rect[i][6] != 0:
                                            self.parent.ch3.setPixmap(
                                                self.parent.get_rotate_image(i, resize_image, width_rate, height_rate,
                                                                             self.parent.sub_screen_width,
                                                                             self.parent.sub_screen_height))
                                        else:
                                            self.parent.ch3.setPixmap(
                                                resize_image.copy(round(self.parent.ch_rect[i][0] * width_rate),
                                                                  round(self.parent.ch_rect[i][1] * height_rate),
                                                                  round(self.parent.ch_rect[i][2] * width_rate),
                                                                  round(
                                                                      self.parent.ch_rect[i][3] * height_rate)).scaled(
                                                    self.parent.sub_screen_width, self.parent.sub_screen_height))
                                    elif i == 'ch4':
                                        if self.parent.ch_rect[i][6] != 0:
                                            self.parent.ch4.setPixmap(
                                                self.parent.get_rotate_image(i, resize_image, width_rate, height_rate,
                                                                             self.parent.sub_screen_width,
                                                                             self.parent.sub_screen_height))
                                        else:
                                            self.parent.ch4.setPixmap(
                                                resize_image.copy(round(self.parent.ch_rect[i][0] * width_rate),
                                                                  round(self.parent.ch_rect[i][1] * height_rate),
                                                                  round(self.parent.ch_rect[i][2] * width_rate),
                                                                  round(
                                                                      self.parent.ch_rect[i][3] * height_rate)).scaled(
                                                    self.parent.sub_screen_width, self.parent.sub_screen_height))
                                    elif i == 'ch5':
                                        if self.parent.ch_rect[i][6] != 0:
                                            self.parent.ch5.setPixmap(
                                                self.parent.get_rotate_image(i, resize_image, width_rate, height_rate,
                                                                             self.parent.sub_screen_width,
                                                                             self.parent.sub_screen_height))
                                        else:
                                            self.parent.ch5.setPixmap(
                                                resize_image.copy(round(self.parent.ch_rect[i][0] * width_rate),
                                                                  round(self.parent.ch_rect[i][1] * height_rate),
                                                                  round(self.parent.ch_rect[i][2] * width_rate),
                                                                  round(
                                                                      self.parent.ch_rect[i][3] * height_rate)).scaled(
                                                    self.parent.sub_screen_width, self.parent.sub_screen_height))
                                    elif i == 'ch6':
                                        if self.parent.ch_rect[i][6] != 0:
                                            self.parent.ch6.setPixmap(
                                                self.parent.get_rotate_image(i, resize_image, width_rate, height_rate,
                                                                             self.parent.sub_screen_width,
                                                                             self.parent.sub_screen_height))
                                        else:
                                            self.parent.ch6.setPixmap(
                                                resize_image.copy(round(self.parent.ch_rect[i][0] * width_rate),
                                                                  round(self.parent.ch_rect[i][1] * height_rate),
                                                                  round(self.parent.ch_rect[i][2] * width_rate),
                                                                  round(
                                                                      self.parent.ch_rect[i][3] * height_rate)).scaled(
                                                    self.parent.sub_screen_width, self.parent.sub_screen_height))
                                    elif i == 'ch7':
                                        if self.parent.ch_rect[i][6] != 0:
                                            self.parent.ch7.setPixmap(
                                                self.parent.get_rotate_image(i, resize_image, width_rate, height_rate,
                                                                             self.parent.sub_screen_width,
                                                                             self.parent.sub_screen_height))
                                        else:
                                            self.parent.ch7.setPixmap(
                                                resize_image.copy(round(self.parent.ch_rect[i][0] * width_rate),
                                                                  round(self.parent.ch_rect[i][1] * height_rate),
                                                                  round(self.parent.ch_rect[i][2] * width_rate),
                                                                  round(
                                                                      self.parent.ch_rect[i][3] * height_rate)).scaled(
                                                    self.parent.sub_screen_width, self.parent.sub_screen_height))
                                    elif i == 'ch8':
                                        if self.parent.ch_rect[i][6] != 0:
                                            self.parent.ch8.setPixmap(
                                                self.parent.get_rotate_image(i, resize_image, width_rate, height_rate,
                                                                             self.parent.sub_screen_width,
                                                                             self.parent.sub_screen_height))
                                        else:
                                            self.parent.ch8.setPixmap(
                                                resize_image.copy(round(self.parent.ch_rect[i][0] * width_rate),
                                                                  round(self.parent.ch_rect[i][1] * height_rate),
                                                                  round(self.parent.ch_rect[i][2] * width_rate),
                                                                  round(
                                                                      self.parent.ch_rect[i][3] * height_rate)).scaled(
                                                    self.parent.sub_screen_width, self.parent.sub_screen_height))
                                    elif i == 'ch9':
                                        if self.parent.ch_rect[i][6] != 0:
                                            self.parent.ch9.setPixmap(
                                                self.parent.get_rotate_image(i, resize_image, width_rate, height_rate,
                                                                             self.parent.sub_screen_width,
                                                                             self.parent.sub_screen_height))
                                        else:
                                            self.parent.ch9.setPixmap(
                                                resize_image.copy(round(self.parent.ch_rect[i][0] * width_rate),
                                                                  round(self.parent.ch_rect[i][1] * height_rate),
                                                                  round(self.parent.ch_rect[i][2] * width_rate),
                                                                  round(
                                                                      self.parent.ch_rect[i][3] * height_rate)).scaled(
                                                    self.parent.sub_screen_width, self.parent.sub_screen_height))
                                    elif i == 'ch10':
                                        if self.parent.ch_rect[i][6] != 0:
                                            self.parent.ch10.setPixmap(
                                                self.parent.get_rotate_image(i, resize_image, width_rate, height_rate,
                                                                             self.parent.sub_screen_width,
                                                                             self.parent.sub_screen_height))
                                        else:
                                            self.parent.ch10.setPixmap(
                                                resize_image.copy(round(self.parent.ch_rect[i][0] * width_rate),
                                                                  round(self.parent.ch_rect[i][1] * height_rate),
                                                                  round(self.parent.ch_rect[i][2] * width_rate),
                                                                  round(
                                                                      self.parent.ch_rect[i][3] * height_rate)).scaled(
                                                    self.parent.sub_screen_width, self.parent.sub_screen_height))
                            if Config.config['PROGRAM']['iscrop_move'] != 'true':
                                start_rtsp3 = True
                    except Exception as e:
                        print(f"초기 crop 이미지 오류 :: {e}")
                    try:

                        if selected_main3 == True or main3_frame == None:# or isCrop:
                            h, w, c = frame.shape
                            qImg = QImage(frame.data, w, h, w * c, QImage.Format.Format_BGR888)
                            pixmap = QPixmap.fromImage(qImg)
                            #frame_mutex.lock()
                            main3_frame = pixmap
                            #isCrop = False
                            #frame_mutex.unlock()
                        if crop_frame_count % round(30/self.main_monit_limit) != 0:
                            self.msleep(1)
                            continue

                        if selected_main3 != True :
                            h, w, c = frame.shape
                            qImg = QImage(frame.data, w, h, w * c, QImage.Format.Format_BGR888)
                            pixmap = QPixmap.fromImage(qImg)

                        main_frame = pixmap.scaled(self.parent.main_screen_width, self.parent.main_screen_height)

                        # if crop_frame_count % round(video_fps/monit_fps) == 0:
                        #    crop_frame = main_frame.copy()

                        self.parent.ch_rect['RTSP_3'] = [0, 0, w, h, 'RTSP_3', False, 0]

                        for i in self.parent.ch_rect.keys():
                            try:
                                if i == 'RTSP_1' or i == 'RTSP_2':
                                    continue
                                if self.parent.ch_rect[i] != None and self.parent.ch_rect[i][4] == 'RTSP_3':
                                    x, y, w, h = self.parent.ch_rect[i][:4]
                                    width_rate = self.parent.main_screen_width / self.parent.ch_rect['RTSP_3'][2]
                                    height_rate = self.parent.main_screen_height / self.parent.ch_rect['RTSP_3'][3]
                                    x = round(x * width_rate)
                                    y = round(y * height_rate)
                                    w = round(w * width_rate)
                                    h = round(h * height_rate)
                                    main_frame = self.draw_crop_rect(frame=main_frame, geometry=(x, y, w, h),
                                                                     text=f'{i}\n{self.parent.ch_rect[i][2]}x{self.parent.ch_rect[i][3]}',
                                                                     ch=i, selected=self.parent.ch_rect[i][5],
                                                                     rotate=self.parent.ch_rect[i][6])
                                    # main_frame = self.draw_crop_rect(frame=main_frame, geometry=(x, y, w, h),text=f'{i}', ch=i,selected=self.ch_rect[i][5]).copy()
                                    """
                                    if crop_frame_count % round(video_fps/monit_fps) != 0 or crop_frame == None:
                                        continue
                                    elif i == 'ch1':
                                        self.ch1.setPixmap(crop_frame.copy(round(self.ch_rect[i][0]*width_rate),round(self.ch_rect[i][1]*height_rate),round(self.ch_rect[i][2]*width_rate),round(self.ch_rect[i][3]*height_rate)).scaled(self.sub_screen_width,self.sub_screen_height))
                                    elif i == 'ch2':
                                        self.ch2.setPixmap(crop_frame.copy(round(self.ch_rect[i][0]*width_rate),round(self.ch_rect[i][1]*height_rate),round(self.ch_rect[i][2]*width_rate),round(self.ch_rect[i][3]*height_rate)).scaled(self.sub_screen_width,self.sub_screen_height))
                                    elif i == 'ch3':
                                        self.ch3.setPixmap(crop_frame.copy(round(self.ch_rect[i][0]*width_rate),round(self.ch_rect[i][1]*height_rate),round(self.ch_rect[i][2]*width_rate),round(self.ch_rect[i][3]*height_rate)).scaled(self.sub_screen_width,self.sub_screen_height))
                                    elif i == 'ch4':
                                        self.ch4.setPixmap(crop_frame.copy(round(self.ch_rect[i][0]*width_rate),round(self.ch_rect[i][1]*height_rate),round(self.ch_rect[i][2]*width_rate),round(self.ch_rect[i][3]*height_rate)).scaled(self.sub_screen_width,self.sub_screen_height))
                                    elif i == 'ch5':
                                        self.ch5.setPixmap(crop_frame.copy(round(self.ch_rect[i][0]*width_rate),round(self.ch_rect[i][1]*height_rate),round(self.ch_rect[i][2]*width_rate),round(self.ch_rect[i][3]*height_rate)).scaled(self.sub_screen_width,self.sub_screen_height))
                                    elif i == 'ch6':
                                        self.ch6.setPixmap(crop_frame.copy(round(self.ch_rect[i][0]*width_rate),round(self.ch_rect[i][1]*height_rate),round(self.ch_rect[i][2]*width_rate),round(self.ch_rect[i][3]*height_rate)).scaled(self.sub_screen_width,self.sub_screen_height))
                                    elif i == 'ch7':
                                        self.ch7.setPixmap(crop_frame.copy(round(self.ch_rect[i][0]*width_rate),round(self.ch_rect[i][1]*height_rate),round(self.ch_rect[i][2]*width_rate),round(self.ch_rect[i][3]*height_rate)).scaled(self.sub_screen_width,self.sub_screen_height))
                                    elif i == 'ch8':
                                        self.ch8.setPixmap(crop_frame.copy(round(self.ch_rect[i][0]*width_rate),round(self.ch_rect[i][1]*height_rate),round(self.ch_rect[i][2]*width_rate),round(self.ch_rect[i][3]*height_rate)).scaled(self.sub_screen_width,self.sub_screen_height))
                                    elif i == 'ch9':
                                        self.ch9.setPixmap(crop_frame.copy(round(self.ch_rect[i][0]*width_rate),round(self.ch_rect[i][1]*height_rate),round(self.ch_rect[i][2]*width_rate),round(self.ch_rect[i][3]*height_rate)).scaled(self.sub_screen_width,self.sub_screen_height))
                                    elif i == 'ch10':
                                        self.ch10.setPixmap(crop_frame.copy(round(self.ch_rect[i][0]*width_rate),round(self.ch_rect[i][1]*height_rate),round(self.ch_rect[i][2]*width_rate),round(self.ch_rect[i][3]*height_rate)).scaled(self.sub_screen_width,self.sub_screen_height))
                                    """
                            except Exception as e:
                                print(f"draw_rect_errorr :: {e}")
                                continue
                        #frame_mutex.lock()
                        self.parent.main3.setPixmap(main_frame)
                        #frame_mutex.unlock()
                        # self.main1.setPixmap(main_frame.scaled(self.main_screen_width, self.main_screen_height))
                    except Exception as e:
                        print(f"setPixmap main errer :: {e}")

                    self.msleep(int(Config.config['PROGRAM']['msleep_rtsp3']))
                    #self.update_frame.emit(frame, self.name, crop_frame_count)

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
    def draw_crop_rect(self,frame,geometry,text,ch,selected, rotate):

        # TODO: 해당 rect는 원본 비율의 x, y, w, h
        pixmap_with_rects = frame
        painter = QPainter(pixmap_with_rects)
        painter.setRenderHint(QPainter.Antialiasing)
        if not selected:
            pen = QPen(Qt.green)
            #pen = QPen(Qt.yellow)
        if selected:
            pen = QPen(Qt.red)
        pen.setWidth(2)
        painter.setPen(pen)

        font = QFont()
        #font.setFamily('Arial')
        font.setFamily(f"{os.path.dirname(__file__)}\\Assets\\NotoSans-Regular.ttf")
        font.setBold(True)
        font.setPointSize(round(10))
        painter.setFont(font)

        x, y, w, h = geometry
        if ch != 'RTSP_1' and ch != 'RTSP_2' and ch != 'RTSP_3':
            rect = QRect(x, y, w, h)
            center_x = x + w / 2
            center_y = y + h / 2

            painter.translate(center_x, center_y)  # 중심점으로 이동
            painter.rotate(rotate)  # 회전
            painter.translate(-center_x, -center_y)  # 원래 위치로 이동

            painter.drawRect(rect)

        if self.parent.isABS[ch]: # onABS
            painter.drawText(QRect(x+10,y+10,w,h),Qt.TextWordWrap, text+'\nABS')  # rect 위에 key 값을 글자로 씀
        if not self.parent.isABS[ch]: # offABS
            painter.drawText(QRect(x + 10, y + 10, w, h), Qt.TextWordWrap, text)  # rect 위에 key 값을 글자로 씀
        painter.end()

        return pixmap_with_rects

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
    update_pixmap = pyqtSignal(QPixmap)
    def __init__(self,channel_rect,ch, isABS,selected_ch, parent,isFirst):
        super().__init__()
        self.monit_class = MonitClass()
        self.working = True
        self.channel_rect = channel_rect
        self.ch = ch
        self.isABS = isABS
        self.selected_ch = selected_ch
        self.parent = parent
        self.isFirst = isFirst

    def run(self):
        #global ch_frame
        global main1_frame
        global main2_frame
        global main3_frame

        global config_width
        global config_height
        global pitchInfo
        global frame_mutex
        try:
            while self.working :
                if self.isFirst:
                    self.msleep(100)
                    continue
                if self.ch == 'RTSP_1':

                    if self.channel_rect[6] == 0:
                        self.selected_ch = "no_rotate"
                        #frame_mutex.lock()
                        frame = main1_frame.copy(self.channel_rect[0], self.channel_rect[1], self.channel_rect[2], self.channel_rect[3]).scaled(config_width,config_height)
                        #frame_mutex.unlock()

                    else:
                        #frame_mutex.lock()
                        frame = main1_frame.copy()
                        #frame_mutex.unlock()
                if self.ch == 'RTSP_2':
                    if self.channel_rect[6] == 0:
                        self.selected_ch = "no_rotate"
                        #frame_mutex.lock()
                        frame = main2_frame.copy(self.channel_rect[0], self.channel_rect[1], self.channel_rect[2],
                                                 self.channel_rect[3]).scaled(config_width, config_height)
                        #frame_mutex.unlock()
                    else:
                        #frame_mutex.lock()
                        frame = main2_frame.copy()
                        #frame_mutex.unlock()
                if self.ch == 'RTSP_3':
                    if self.channel_rect[6] == 0:
                        self.selected_ch = "no_rotate"
                        #frame_mutex.lock()
                        frame = main3_frame.copy(self.channel_rect[0], self.channel_rect[1], self.channel_rect[2],
                                                 self.channel_rect[3]).scaled(config_width, config_height)
                        #frame_mutex.unlock()
                    else:
                        #frame_mutex.lock()
                        frame = main3_frame.copy()
                        #frame_mutex.unlock()

                if self.selected_ch != 'no_rotate' and self.channel_rect != None:
                    #frame_mutex.lock()
                    pixmap = self.get_rotate_image(self.channel_rect, frame,1,1,config_width,config_height)
                    #frame_mutex.unlock()

                else:
                    #frame_mutex.lock()
                    pixmap = frame
                    #frame_mutex.unlock()
                # TODO : 스트라이크존 isABS 판별
                if self.isABS:
                    painter = QPainter(pixmap)
                    painter.setOpacity(0.6)
                    painter.drawPixmap(self.parent.strike_zone_image_x, self.parent.strike_zone_image_y, self.parent.strike_zone)

                    if pitchInfo is not None:
                        try:
                            if Config.config['ABS']['reverse'] == 'true':
                                x_rate = ((self.parent.zone_width / 2) + (pitchInfo['pitch_x'] / 10000)) / self.parent.zone_width
                                x_point = round(self.parent.strike_zone_start_x + (
                                            (self.parent.strike_zone_end_x - self.parent.strike_zone_start_x) * x_rate))
                                x_point = round(2 * (self.parent.strike_zone_start_x + (
                                            self.parent.strike_zone_end_x - self.parent.strike_zone_start_x) / 2) - x_point)

                            if Config.config['ABS']['reverse'] == 'false':
                                x_rate = ((self.parent.zone_width / 2) + (pitchInfo['pitch_x'] / 10000)) / self.parent.zone_width
                                x_point = round(self.parent.strike_zone_start_x + (
                                            (self.parent.strike_zone_end_x - self.parent.strike_zone_start_x) * x_rate))
                            y_rate = ((pitchInfo['pitch_y'] - pitchInfo['box_bottom']) / (
                                        pitchInfo['box_top'] - pitchInfo['box_bottom']))
                            y_point = round(
                                self.parent.strike_zone_end_y - ((self.parent.strike_zone_end_y - self.parent.strike_zone_start_y) * y_rate))

                            if x_point <= self.parent.strike_zone_image_x:
                                x_point = self.parent.strike_zone_image_x + self.parent.ball_size
                            if x_point >= self.parent.strike_zone_image_x + self.parent.strike_zone.width():
                                x_point = self.parent.strike_zone_image_x + self.parent.strike_zone.width() - 2 * self.parent.ball_size
                            if y_point <= self.parent.strike_zone_image_y:
                                y_point = self.parent.strike_zone_image_y + self.parent.ball_size
                            if y_point >= self.parent.strike_zone_image_y + self.parent.km_start_y:
                                y_point = self.parent.strike_zone_image_y + self.parent.km_start_y - 2 * self.parent.ball_size

                            painter.setPen(QPen(Qt.gray, self.parent.ball_size))
                            painter.drawEllipse(x_point, y_point, self.parent.ball_size, self.parent.ball_size)
                            # global config_width
                            painter.setPen(QPen(Qt.red))
                            painter.setFont(QFont(f"{os.path.dirname(__file__)}\\Assets\\NotoSans-Regular.ttf",
                                                  round(25 * (config_width / 1920)), QFont.Bold))
                            painter.drawText(QRect(self.parent.km_start_x, self.parent.km_start_y, self.parent.strike_zone.width(),
                                                   self.parent.strike_zone_image_y + self.parent.strike_zone.height() - self.parent.km_start_y),
                                             Qt.AlignCenter, f"{pitchInfo['speed']} KM")
                            painter.end()
                        except Exception as e:
                            print(f"ABS ball point error :: {e}")

                try:
                    #if frame_mutex.tryLock():
                    #self.monit_class.monit_label.setPixmap(pixmap)
                    self.update_pixmap.emit(pixmap)
                    self.msleep(int(Config.config['PROGRAM']['monit_msleep']))


                except Exception as e:
                    print(f"monit label setPixmap Error :: {e}")
        except Exception as e:
            print(f"monit thread exception :: {e}")


    def change_channel_rect(self,channel_rect,ch, isABS,selected_ch,isFirst):
        self.channel_rect = channel_rect
        self.ch = ch
        self.isABS = isABS
        self.selected_ch = selected_ch
        self.isFirst = isFirst

    def get_rotate_image(self, channel_rect, main_frame ,width_rate,height_rate, scaled_width, scaled_height):
        global frame_mutex
        try:
            top_left, top_right, bottom_left, bottom_right = get_rotate_point(round(channel_rect[0] * width_rate )
                                                                              , round(channel_rect[1] * height_rate)
                                                                              , round(channel_rect[2] * width_rate)
                                                                              , round(channel_rect[3] * height_rate),
                                                                              channel_rect[6])
            #frame_mutex.lock()
            resize_image = main_frame
            #frame_mutex.unlock()

            # 사각형 영역을 QPolygon으로 정의
            polygon = QPolygon([top_left, top_right, bottom_right, bottom_left])

            # QRegion으로 마스크 생성
            region = QRegion(polygon)

            # 필요한 부분만 crop하기 위해 boundingRect 사용
            cropped_rect = region.boundingRect()
            cropped_pixmap = resize_image.copy(cropped_rect)

            min_x = 9999
            min_y = 9999
            max_x = 0
            max_y = 0
            for i in polygon:
                min_x = min(min_x, i.x())
                min_y = min(min_y, i.y())
                max_x = max(max_x, i.x())
                max_y = max(max_y, i.y())

            rotate_width = abs(round(max_x - min_x))
            rotate_height = abs(round(max_y - min_y))

            if rotate_width < rotate_height:
                rotate_width = abs(round(max_y - min_y))
                rotate_height = abs(round(max_x - min_x))

            rotated_pixmap = QPixmap(rotate_width, rotate_height)
            #rotated_pixmap.fill(Qt.transparent)  # 투명 배경으로 채우기

            # 크롭된 이미지의 중심 좌표 계산
            center_x = round(rotate_width / 2)
            center_y = round(rotate_height / 2)

            # 원래의 대각선 각도로 되돌리기 위한 변환
            transform = QTransform()
            transform.translate(center_x, center_y)  # 중심으로 이동
            transform.rotate(-channel_rect[6])  # 원래의 대각선 각도로 회전 (예: -45도)
            transform.translate(-center_x, -center_y)  # 다시 원래 위치로 이동

            # QPainter를 사용하여 회전된 이미지 그리기
            painter = QPainter(rotated_pixmap)
            painter.setTransform(transform)
            painter.drawPixmap((rotate_width - cropped_pixmap.width()) // 2,
                               (rotate_height - cropped_pixmap.height()) // 2,
                               cropped_pixmap)
            painter.end()

            # 유효한 부분만 크롭
            final_pixmap = rotated_pixmap.copy(round(((rotate_width-channel_rect[2]*width_rate))/2 ),round(((rotate_height-channel_rect[3]*height_rate))/2 ),
                                               round(channel_rect[2]),round(channel_rect[3]))

            return final_pixmap.scaled(int(scaled_width),int(scaled_height))
        except Exception as e:
            print(e)

    def stop(self):
        self.working = False
        self.monit_class.close()
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

        self.resize(config_width, config_height)
        self.setFixedSize(self.width(),self.height())
        self.monit_label.setGeometry(0, 0, config_width, config_height)
        if isExe:
            self.monit_label.setPixmap(QPixmap(f"{os.path.dirname(__file__)}\\Assets\\no-signal-icon-black.jpg"))
        if not isExe:
            self.monit_label.setPixmap(QPixmap('./Assets/no-signal-icon-black.jpg'))

        self.setGeometry(-(config_width+1), -(config_height+1), config_width, config_height)
        self.setWindowFlags(Qt.FramelessWindowHint)
        #self.setCursor(QCursor(Qt.BlankCursor))
        self.setWindowOpacity(0.9999)
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

        #self.resize(round(self.window_width*0.8), round(self.window_height*0.8))
        self.resize(round(self.window_width * 0.6), round(self.window_height * 0.6))
        self.rtsp_num = int(Config.config['RTSP']['rtsp_num'])
        # TODO : selected color :: rgb(253, 8, 8) // no selected color :: rgb(190, 190, 190);
        self.selected_color="border : 2px solid rgb(253,8,8)"
        self.no_selected_color="border : 2px solid rgb(190, 190, 190)"
        self.dialog = None

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

        # TODO : PIP 모니터 화면 크기 설정 및 초기 이미지 선언
        #self.sub_screen_width = round(self.main_screen_width / 2)
        self.sub_screen_width = round(self.window_width / 5.4)
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
        for i in Config.config['PIP'].items():
            if i[1] != "None":
                value = i[1]
                if value.find('false') != -1:
                    value = i[1].replace('false','False')
                if value.find('true') != -1:
                    value = i[1].replace('true', 'True')
                self.ch_rect[i[0]] = eval(value)

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
        try:
            self.actionSelect_first_RTSP.triggered.connect(lambda :self.getChannelSetting(rtsp_name="First RTSP"))
            self.actionSelect_Second_RTSP.triggered.connect(lambda: self.getChannelSetting(rtsp_name="Second RTSP"))
            self.actionSelect_Third_RTSP.triggered.connect(lambda: self.getChannelSetting(rtsp_name="Third RTSP"))
        except Exception as e:
            print(f"actionSelect Error :: {e}")

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

        #self.actionStop_CH_1.mousePressEvent = lambda: self.stop_ch(ch='ch1')

        # TODO : ABS 송출을 위한 스트라이크존 ( 방송 출력 모니터 비율에 맞춰 scaled )
        self.strike_zone = QPixmap(f"{os.path.dirname(__file__)}\\Assets\\strikeZone.png")
        #self.strike_zone = QPixmap(f"{os.path.dirname(__file__)}\\Assets\\strikeZone2.png")
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
        """
        self.strike_zone_start_x = self.strike_zone_image_x + round(strike_zone_width * 60 / 200) - int(self.ball_size / 2)  # 실질적인 스트라이크존 좌상단 x
        self.strike_zone_start_y = self.strike_zone_image_y + round(strike_zone_height * 56 / 240) - int(self.ball_size / 2)  # 실질적인 스트라이크존 좌상단 y
        self.strike_zone_end_x = self.strike_zone_image_x + round(strike_zone_width * 139 / 200) - int(self.ball_size / 2)  # 실질적인 스트라이크존 우하단 x
        self.strike_zone_end_y = self.strike_zone_image_y + round(strike_zone_height * 153 / 240) - int(self.ball_size / 2)  # 실질적인 스트라이크존 우하단 y
        """
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

        # TODO : ABS 서버 통신 쓰레드
        #self.abs_request_thread = threading.Thread(target=getPitchInfo)
        #self.abs_request_thread.start()
        self.abs_request_thread = GetPitchInfo(parent=self)
        self.abs_request_thread.start()

        # TODO : RTSP 서버 click 우클릭시 setChannel창 표출

        self.main1.mousePressEvent = lambda event : self.rtspClickSetChannel(event,'rtsp1')
        self.main2.mousePressEvent = lambda event : self.rtspClickSetChannel(event,'rtsp2')
        self.main3.mousePressEvent = lambda event : self.rtspClickSetChannel(event,'rtsp3')

        # TODO : RTSP 서버 마우스 이동시 rect 변경
        """
        self.main1.mouseMoveEvent = lambda event : self.rtspMoveCrop(event,'RTSP_1')
        self.main2.mouseMoveEvent = lambda event: self.rtspMoveCrop(event, 'RTSP_2')
        self.main3.mouseMoveEvent = lambda event: self.rtspMoveCrop(event, 'RTSP_3')
        """

        # TODO : CH 더블클릭 이벤트 ( ch 삭제 )
        self.ch1.mouseDoubleClickEvent = lambda event : self.chDbClickStop(event,'ch1')
        self.ch2.mouseDoubleClickEvent = lambda event : self.chDbClickStop(event, 'ch2')
        self.ch3.mouseDoubleClickEvent = lambda event : self.chDbClickStop(event, 'ch3')
        self.ch4.mouseDoubleClickEvent = lambda event : self.chDbClickStop(event, 'ch4')
        self.ch5.mouseDoubleClickEvent = lambda event : self.chDbClickStop(event, 'ch5')
        self.ch6.mouseDoubleClickEvent = lambda event : self.chDbClickStop(event, 'ch6')
        self.ch7.mouseDoubleClickEvent = lambda event : self.chDbClickStop(event, 'ch7')
        self.ch8.mouseDoubleClickEvent = lambda event : self.chDbClickStop(event, 'ch8')
        self.ch9.mouseDoubleClickEvent = lambda event : self.chDbClickStop(event, 'ch9')
        self.ch10.mouseDoubleClickEvent = lambda event : self.chDbClickStop(event, 'ch10')

        # TODO : OBS (방송) 화면 송출한 서브 화면 표시 (widget)
        self.isFirstMonit = True
        self.monit_thread = MonitThread(None, None, None, None, self, self.isFirstMonit)
        self.monit_thread.update_pixmap.connect(self.update_monit_label)
        self.monit_thread.start()



    # TODO : rtsp 마우스 움직임 함수
    """
    def rtspMoveCrop(self,event,param):
        try:
            selected_ch = None
            for i in self.ch_rect.keys():
                if self.ch_rect[i] != None and self.ch_rect[i][4] == param and self.ch_rect[i][5] == True:
                    selected_ch = self.ch_rect[i]
            x = event.pos().x()
            y = event.pos().y()
            if selected_ch != None:
                selected_ch[0]=x
                selected_ch[1]=y
            print(x, y)
        except Exception as e:
            print(e)
    """

    """
    def moveEvent(self, a0):
        x = self.geometry().x()
        y = self.geometry().y()
        self.monit_class.setGeometry(x,y,self.monit_class.width(),self.monit_class.height())
    """
    # TODO : 모니터 스레드 화면 업데이트
    @pyqtSlot(QPixmap)
    def update_monit_label(self, pixmap):
        self.monit_thread.monit_class.monit_label.setPixmap(pixmap)

    # TODO : rtsp 우클릭 이벤트 함수
    def rtspClickSetChannel(self,event,param):
        if event.button() == Qt.RightButton:
            try:
                if param == 'rtsp1':
                    self.getChannelSetting(rtsp_name="First RTSP")
                if param == 'rtsp2':
                    self.getChannelSetting(rtsp_name="Second RTSP")
                if param == 'rtsp3':
                    self.getChannelSetting(rtsp_name="Third RTSP")
            except Exception as e:
                print(f"click get channel Error :: {e}")

    # TODO : ch 더블클릭 삭제 이벤트 함수
    def chDbClickStop(self,event,param):
        try:
            if param == 'ch1':
                self.stop_ch('ch1')
            if param == 'ch2':
                self.stop_ch('ch2')
            if param == 'ch3':
                self.stop_ch('ch3')
            if param == 'ch4':
                self.stop_ch('ch4')
            if param == 'ch5':
                self.stop_ch('ch5')
            if param == 'ch6':
                self.stop_ch('ch6')
            if param == 'ch7':
                self.stop_ch('ch7')
            if param == 'ch8':
                self.stop_ch('ch8')
            if param == 'ch9':
                self.stop_ch('ch9')
            if param == 'ch10':
                self.stop_ch('ch10')
        except Exception as e:
            print(e)
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
        #frame_mutex.lock()
        try:
            global frame_mutex

            global main1_frame
            global main2_frame
            global main3_frame
            global isMonitRunning
            global selected_main1
            global selected_main2
            global selected_main3
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
                    try:
                        if not selected_main1:
                            selected_main1 = True
                            frame = self.main1.pixmap().scaled(self.crop_ch_rect['RTSP_1'][0],self.crop_ch_rect['RTSP_1'][1])
                            dialog = set_Channel.Set_Channel_Dialog(frame=frame, rtsp_name=rtsp_name,origin_width=self.ch_rect['RTSP_1'][2])
                            dialog.get_rectangle_signal.connect(self.setChannelRect)
                            dialog.exec_()
                            selected_main1 = False
                        else:
                            frame = self.main1.pixmap().scaled(self.crop_ch_rect['RTSP_1'][0],
                                                               self.crop_ch_rect['RTSP_1'][1])
                            dialog = set_Channel.Set_Channel_Dialog(frame=frame, rtsp_name=rtsp_name,
                                                                    origin_width=self.ch_rect['RTSP_1'][2])
                            dialog.get_rectangle_signal.connect(self.setChannelRect)
                            dialog.exec_()

                    except Exception as e:
                        print(f"set Channel dialog Error : {e}")

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

                    try:
                        if not selected_main2:
                            selected_main2 = True
                            frame = self.main2.pixmap().scaled(self.crop_ch_rect['RTSP_2'][0],self.crop_ch_rect['RTSP_2'][1])
                            dialog = set_Channel.Set_Channel_Dialog(frame=frame, rtsp_name=rtsp_name,origin_width=self.ch_rect['RTSP_2'][2])
                            dialog.get_rectangle_signal.connect(self.setChannelRect)
                            dialog.exec_()
                            selected_main2 = False
                        else:
                            frame = self.main2.pixmap().scaled(self.crop_ch_rect['RTSP_2'][0],
                                                               self.crop_ch_rect['RTSP_2'][1])
                            dialog = set_Channel.Set_Channel_Dialog(frame=frame, rtsp_name=rtsp_name,
                                                                    origin_width=self.ch_rect['RTSP_2'][2])
                            dialog.get_rectangle_signal.connect(self.setChannelRect)
                            dialog.exec_()

                    except Exception as e:
                         print(f"set Channel dialog Error : {e}")

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

                    try:
                        if not selected_main3:
                            selected_main3 = True
                            frame = self.main3.pixmap().scaled(self.crop_ch_rect['RTSP_3'][0],self.crop_ch_rect['RTSP_3'][1])
                            dialog = set_Channel.Set_Channel_Dialog(frame=frame, rtsp_name=rtsp_name,origin_width=self.ch_rect['RTSP_3'][2])
                            dialog.get_rectangle_signal.connect(self.setChannelRect)
                            dialog.exec_()
                            selected_main3 = False
                        else:
                            frame = self.main3.pixmap().scaled(self.crop_ch_rect['RTSP_3'][0],
                                                               self.crop_ch_rect['RTSP_3'][1])
                            dialog = set_Channel.Set_Channel_Dialog(frame=frame, rtsp_name=rtsp_name,
                                                                    origin_width=self.ch_rect['RTSP_3'][2])
                            dialog.get_rectangle_signal.connect(self.setChannelRect)
                            dialog.exec_()


                    except Exception as e:
                        print(f"set Channel dialog Error : {e}")

                if main3_frame == None:
                    QMessageBox.about(self, "RTSP Connect Error", "Third RTSP Server Not Connect")
        except Exception as e:
            print(f"get channel error : {e}")

        #frame_mutex.unlock()
    # TODO : CH 셋팅에서 전달받은 값.. ch1, ch2 ... // First RTSP, Second RTSP // [left_top_x,left_top_y,width,height] // rotate
    def setChannelRect(self, ch, rtsp_name, rect_point, rotate):
        #global ch_frame
        try:

            global main1_frame
            global main2_frame
            global main3_frame
            #global isCrop
            global frame_mutex
            #isCrop = True
            ##########################################
            #while True:
            #    if isCrop == False:
            #        break
            crop_x, crop_y, crop_width, crop_height = rect_point
            #width_rate = self.ch_rect['ch1'][2] / self.main_screen_width
            #height_rate = self.ch_rect['ch1'][3] / self.main_screen_height

            if rtsp_name == 'First RTSP' and main1_frame != None:

                width_rate = self.ch_rect['RTSP_1'][2] / self.crop_ch_rect['RTSP_1'][0]
                height_rate = self.ch_rect['RTSP_1'][3] / self.crop_ch_rect['RTSP_1'][1]

                # TODO : crop 화면을 이미지로 넣기 위한 전처리
                #frame_mutex.lock()
                resize_image = main1_frame.scaled(self.main_screen_width, self.main_screen_height)
                #frame_mutex.unlock()
                self.ch_rect[ch] = [round(crop_x * width_rate), round(crop_y * height_rate),round(crop_width * width_rate), round(crop_height * height_rate),'RTSP_1',False, rotate]
                width_rate = self.main_screen_width / self.ch_rect['RTSP_1'][2]
                #width_rate = resize_image.width() / self.ch_rect['RTSP_1'][2]
                height_rate = self.main_screen_height / self.ch_rect['RTSP_1'][3]
                #height_rate = resize_image.height() / self.ch_rect['RTSP_1'][3]

                # TODO : crop 화면 이미지 처리
                if ch == 'ch1':
                    if self.ch_rect[ch][6] != 0 :
                        self.ch1.setPixmap(self.get_rotate_image(ch,resize_image,width_rate,height_rate,self.sub_screen_width,self.sub_screen_height))
                    else:
                        self.ch1.setPixmap(
                            resize_image.copy(round(self.ch_rect[ch][0] * width_rate), round(self.ch_rect[ch][1] * height_rate),
                                            round(self.ch_rect[ch][2] * width_rate),
                                            round(self.ch_rect[ch][3] * height_rate)).scaled(self.sub_screen_width, self.sub_screen_height))



                elif ch == 'ch2':
                    if self.ch_rect[ch][6] != 0 :
                        self.ch2.setPixmap(self.get_rotate_image(ch,resize_image,width_rate,height_rate,self.sub_screen_width,self.sub_screen_height))
                    else:
                        self.ch2.setPixmap(
                            resize_image.copy(round(self.ch_rect[ch][0] * width_rate), round(self.ch_rect[ch][1] * height_rate),
                                              round(self.ch_rect[ch][2] * width_rate),
                                              round(self.ch_rect[ch][3] * height_rate)).scaled(self.sub_screen_width,
                                                                                               self.sub_screen_height))
                elif ch == 'ch3':
                    if self.ch_rect[ch][6] != 0 :
                        self.ch3.setPixmap(self.get_rotate_image(ch,resize_image,width_rate,height_rate,self.sub_screen_width,self.sub_screen_height))
                    else:
                        self.ch3.setPixmap(
                            resize_image.copy(round(self.ch_rect[ch][0] * width_rate), round(self.ch_rect[ch][1] * height_rate),
                                              round(self.ch_rect[ch][2] * width_rate),
                                              round(self.ch_rect[ch][3] * height_rate)).scaled(self.sub_screen_width,
                                                                                               self.sub_screen_height))
                elif ch == 'ch4':
                    if self.ch_rect[ch][6] != 0 :
                        self.ch4.setPixmap(self.get_rotate_image(ch,resize_image,width_rate,height_rate,self.sub_screen_width,self.sub_screen_height))
                    else:
                        self.ch4.setPixmap(
                            resize_image.copy(round(self.ch_rect[ch][0] * width_rate), round(self.ch_rect[ch][1] * height_rate),
                                              round(self.ch_rect[ch][2] * width_rate),
                                              round(self.ch_rect[ch][3] * height_rate)).scaled(self.sub_screen_width,
                                                                                               self.sub_screen_height))
                elif ch == 'ch5':
                    if self.ch_rect[ch][6] != 0 :
                        self.ch5.setPixmap(self.get_rotate_image(ch,resize_image,width_rate,height_rate,self.sub_screen_width,self.sub_screen_height))
                    else:
                        self.ch5.setPixmap(
                            resize_image.copy(round(self.ch_rect[ch][0] * width_rate), round(self.ch_rect[ch][1] * height_rate),
                                              round(self.ch_rect[ch][2] * width_rate),
                                              round(self.ch_rect[ch][3] * height_rate)).scaled(self.sub_screen_width,
                                                                                               self.sub_screen_height))
                elif ch == 'ch6':
                    if self.ch_rect[ch][6] != 0 :
                        self.ch6.setPixmap(self.get_rotate_image(ch,resize_image,width_rate,height_rate,self.sub_screen_width,self.sub_screen_height))
                    else:
                        self.ch6.setPixmap(
                            resize_image.copy(round(self.ch_rect[ch][0] * width_rate), round(self.ch_rect[ch][1] * height_rate),
                                              round(self.ch_rect[ch][2] * width_rate),
                                              round(self.ch_rect[ch][3] * height_rate)).scaled(self.sub_screen_width,
                                                                                               self.sub_screen_height))
                elif ch == 'ch7':
                    if self.ch_rect[ch][6] != 0 :
                        self.ch7.setPixmap(self.get_rotate_image(ch,resize_image,width_rate,height_rate,self.sub_screen_width,self.sub_screen_height))
                    else:
                        self.ch7.setPixmap(
                            resize_image.copy(round(self.ch_rect[ch][0] * width_rate), round(self.ch_rect[ch][1] * height_rate),
                                              round(self.ch_rect[ch][2] * width_rate),
                                              round(self.ch_rect[ch][3] * height_rate)).scaled(self.sub_screen_width,
                                                                                               self.sub_screen_height))
                elif ch == 'ch8':
                    if self.ch_rect[ch][6] != 0 :
                        self.ch8.setPixmap(self.get_rotate_image(ch,resize_image,width_rate,height_rate,self.sub_screen_width,self.sub_screen_height))
                    else:
                        self.ch8.setPixmap(
                            resize_image.copy(round(self.ch_rect[ch][0] * width_rate), round(self.ch_rect[ch][1] * height_rate),
                                              round(self.ch_rect[ch][2] * width_rate),
                                              round(self.ch_rect[ch][3] * height_rate)).scaled(self.sub_screen_width,
                                                                                               self.sub_screen_height))
                elif ch == 'ch9':
                    if self.ch_rect[ch][6] != 0 :
                        self.ch9.setPixmap(self.get_rotate_image(ch,resize_image,width_rate,height_rate,self.sub_screen_width,self.sub_screen_height))
                    else:
                        self.ch9.setPixmap(
                            resize_image.copy(round(self.ch_rect[ch][0] * width_rate), round(self.ch_rect[ch][1] * height_rate),
                                              round(self.ch_rect[ch][2] * width_rate),
                                              round(self.ch_rect[ch][3] * height_rate)).scaled(self.sub_screen_width,
                                                                                               self.sub_screen_height))
                elif ch == 'ch10':
                    if self.ch_rect[ch][6] != 0 :
                        self.ch10.setPixmap(self.get_rotate_image(ch,resize_image,width_rate,height_rate,self.sub_screen_width,self.sub_screen_height))
                    else:
                        self.ch10.setPixmap(
                            resize_image.copy(round(self.ch_rect[ch][0] * width_rate), round(self.ch_rect[ch][1] * height_rate),
                                              round(self.ch_rect[ch][2] * width_rate),
                                              round(self.ch_rect[ch][3] * height_rate)).scaled(self.sub_screen_width,
                                                                                               self.sub_screen_height))



            if rtsp_name == 'Second RTSP' and main2_frame != None:

                width_rate = self.ch_rect['RTSP_2'][2] / self.crop_ch_rect['RTSP_2'][0]
                height_rate = self.ch_rect['RTSP_2'][3] / self.crop_ch_rect['RTSP_2'][1]

                # TODO : crop 화면을 이미지로 넣기 위한 전처리
                resize_image = main2_frame.scaled(self.main_screen_width, self.main_screen_height)
                self.ch_rect[ch] = [round(crop_x * width_rate), round(crop_y * height_rate),round(crop_width * width_rate), round(crop_height * height_rate), 'RTSP_2',False, rotate]
                width_rate = self.main_screen_width / self.ch_rect['RTSP_2'][2]
                height_rate = self.main_screen_height / self.ch_rect['RTSP_2'][3]

                # TODO : crop 화면 이미지 처리
                if ch == 'ch1':
                    self.ch1.setPixmap(
                        resize_image.copy(round(self.ch_rect[ch][0] * width_rate), round(self.ch_rect[ch][1] * height_rate),
                                        round(self.ch_rect[ch][2] * width_rate),
                                        round(self.ch_rect[ch][3] * height_rate)).scaled(self.sub_screen_width,                                                        self.sub_screen_height))
                elif ch == 'ch2':
                    self.ch2.setPixmap(
                        resize_image.copy(round(self.ch_rect[ch][0] * width_rate), round(self.ch_rect[ch][1] * height_rate),
                                          round(self.ch_rect[ch][2] * width_rate),
                                          round(self.ch_rect[ch][3] * height_rate)).scaled(self.sub_screen_width,
                                                                                           self.sub_screen_height))
                elif ch == 'ch3':
                    self.ch3.setPixmap(
                        resize_image.copy(round(self.ch_rect[ch][0] * width_rate), round(self.ch_rect[ch][1] * height_rate),
                                          round(self.ch_rect[ch][2] * width_rate),
                                          round(self.ch_rect[ch][3] * height_rate)).scaled(self.sub_screen_width,
                                                                                           self.sub_screen_height))
                elif ch == 'ch4':
                    self.ch4.setPixmap(
                        resize_image.copy(round(self.ch_rect[ch][0] * width_rate), round(self.ch_rect[ch][1] * height_rate),
                                          round(self.ch_rect[ch][2] * width_rate),
                                          round(self.ch_rect[ch][3] * height_rate)).scaled(self.sub_screen_width,
                                                                                           self.sub_screen_height))
                elif ch == 'ch5':
                    self.ch5.setPixmap(
                        resize_image.copy(round(self.ch_rect[ch][0] * width_rate), round(self.ch_rect[ch][1] * height_rate),
                                          round(self.ch_rect[ch][2] * width_rate),
                                          round(self.ch_rect[ch][3] * height_rate)).scaled(self.sub_screen_width,
                                                                                           self.sub_screen_height))
                elif ch == 'ch6':
                    self.ch6.setPixmap(
                        resize_image.copy(round(self.ch_rect[ch][0] * width_rate), round(self.ch_rect[ch][1] * height_rate),
                                          round(self.ch_rect[ch][2] * width_rate),
                                          round(self.ch_rect[ch][3] * height_rate)).scaled(self.sub_screen_width,
                                                                                           self.sub_screen_height))
                elif ch == 'ch7':
                    self.ch7.setPixmap(
                        resize_image.copy(round(self.ch_rect[ch][0] * width_rate), round(self.ch_rect[ch][1] * height_rate),
                                          round(self.ch_rect[ch][2] * width_rate),
                                          round(self.ch_rect[ch][3] * height_rate)).scaled(self.sub_screen_width,
                                                                                           self.sub_screen_height))
                elif ch == 'ch8':
                    self.ch8.setPixmap(
                        resize_image.copy(round(self.ch_rect[ch][0] * width_rate), round(self.ch_rect[ch][1] * height_rate),
                                          round(self.ch_rect[ch][2] * width_rate),
                                          round(self.ch_rect[ch][3] * height_rate)).scaled(self.sub_screen_width,
                                                                                           self.sub_screen_height))
                elif ch == 'ch9':
                    self.ch9.setPixmap(
                        resize_image.copy(round(self.ch_rect[ch][0] * width_rate), round(self.ch_rect[ch][1] * height_rate),
                                          round(self.ch_rect[ch][2] * width_rate),
                                          round(self.ch_rect[ch][3] * height_rate)).scaled(self.sub_screen_width,
                                                                                           self.sub_screen_height))
                elif ch == 'ch10':
                    self.ch10.setPixmap(
                        resize_image.copy(round(self.ch_rect[ch][0] * width_rate), round(self.ch_rect[ch][1] * height_rate),
                                          round(self.ch_rect[ch][2] * width_rate),
                                          round(self.ch_rect[ch][3] * height_rate)).scaled(self.sub_screen_width,
                                                                                           self.sub_screen_height))


            if rtsp_name == 'Third RTSP' and main3_frame != None:

                width_rate = self.ch_rect['RTSP_3'][2] / self.crop_ch_rect['RTSP_3'][0]
                height_rate = self.ch_rect['RTSP_3'][3] / self.crop_ch_rect['RTSP_3'][1]

                # TODO : crop 화면을 이미지로 넣기 위한 전처리
                resize_image = main3_frame.scaled(self.main_screen_width, self.main_screen_height)
                self.ch_rect[ch] = [round(crop_x * width_rate), round(crop_y * height_rate),round(crop_width * width_rate), round(crop_height * height_rate), 'RTSP_3',False, rotate]
                width_rate = self.main_screen_width / self.ch_rect['RTSP_3'][2]
                height_rate = self.main_screen_height / self.ch_rect['RTSP_3'][3]

                # TODO : crop 화면 이미지 처리
                if ch == 'ch1':
                    self.ch1.setPixmap(
                        resize_image.copy(round(self.ch_rect[ch][0] * width_rate), round(self.ch_rect[ch][1] * height_rate),
                                        round(self.ch_rect[ch][2] * width_rate),
                                        round(self.ch_rect[ch][3] * height_rate)).scaled(self.sub_screen_width,self.sub_screen_height))
                elif ch == 'ch2':
                    self.ch2.setPixmap(
                        resize_image.copy(round(self.ch_rect[ch][0] * width_rate), round(self.ch_rect[ch][1] * height_rate),
                                          round(self.ch_rect[ch][2] * width_rate),
                                          round(self.ch_rect[ch][3] * height_rate)).scaled(self.sub_screen_width,
                                                                                           self.sub_screen_height))
                elif ch == 'ch3':
                    self.ch3.setPixmap(
                        resize_image.copy(round(self.ch_rect[ch][0] * width_rate), round(self.ch_rect[ch][1] * height_rate),
                                          round(self.ch_rect[ch][2] * width_rate),
                                          round(self.ch_rect[ch][3] * height_rate)).scaled(self.sub_screen_width,
                                                                                           self.sub_screen_height))
                elif ch == 'ch4':
                    self.ch4.setPixmap(
                        resize_image.copy(round(self.ch_rect[ch][0] * width_rate), round(self.ch_rect[ch][1] * height_rate),
                                          round(self.ch_rect[ch][2] * width_rate),
                                          round(self.ch_rect[ch][3] * height_rate)).scaled(self.sub_screen_width,
                                                                                           self.sub_screen_height))
                elif ch == 'ch5':
                    self.ch5.setPixmap(
                        resize_image.copy(round(self.ch_rect[ch][0] * width_rate), round(self.ch_rect[ch][1] * height_rate),
                                          round(self.ch_rect[ch][2] * width_rate),
                                          round(self.ch_rect[ch][3] * height_rate)).scaled(self.sub_screen_width,
                                                                                           self.sub_screen_height))
                elif ch == 'ch6':
                    self.ch6.setPixmap(
                        resize_image.copy(round(self.ch_rect[ch][0] * width_rate), round(self.ch_rect[ch][1] * height_rate),
                                          round(self.ch_rect[ch][2] * width_rate),
                                          round(self.ch_rect[ch][3] * height_rate)).scaled(self.sub_screen_width,
                                                                                           self.sub_screen_height))
                elif ch == 'ch7':
                    self.ch7.setPixmap(
                        resize_image.copy(round(self.ch_rect[ch][0] * width_rate), round(self.ch_rect[ch][1] * height_rate),
                                          round(self.ch_rect[ch][2] * width_rate),
                                          round(self.ch_rect[ch][3] * height_rate)).scaled(self.sub_screen_width,
                                                                                           self.sub_screen_height))
                elif ch == 'ch8':
                    self.ch8.setPixmap(
                        resize_image.copy(round(self.ch_rect[ch][0] * width_rate), round(self.ch_rect[ch][1] * height_rate),
                                          round(self.ch_rect[ch][2] * width_rate),
                                          round(self.ch_rect[ch][3] * height_rate)).scaled(self.sub_screen_width,
                                                                                           self.sub_screen_height))
                elif ch == 'ch9':
                    self.ch9.setPixmap(
                        resize_image.copy(round(self.ch_rect[ch][0] * width_rate), round(self.ch_rect[ch][1] * height_rate),
                                          round(self.ch_rect[ch][2] * width_rate),
                                          round(self.ch_rect[ch][3] * height_rate)).scaled(self.sub_screen_width,
                                                                                           self.sub_screen_height))
                elif ch == 'ch10':
                    self.ch10.setPixmap(
                        resize_image.copy(round(self.ch_rect[ch][0] * width_rate), round(self.ch_rect[ch][1] * height_rate),
                                          round(self.ch_rect[ch][2] * width_rate),
                                          round(self.ch_rect[ch][3] * height_rate)).scaled(self.sub_screen_width,
                                                                                           self.sub_screen_height))


            # TODO : config 저장 ( ch )
            Config.config['PIP'][ch] = json.dumps(self.ch_rect[ch])

        except Exception as e:
            print(f"setChannel Error :: {e}")
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
    """
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
    """



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
            #self.monit_class.close()
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
            with open(Config.config_path, 'w', encoding='utf-8') as configfile:
                Config.config.write(configfile)
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
        def handle_channel_key(channel, channel_rect, isABS, selected_ch):
            #global isClose
            #while channel_rect != None:
            global selected_main1
            global selected_main2
            global selected_main3
            global main1_frame
            global main2_frame
            global main3_frame

            if channel_rect != None:
                try:
                    if channel_rect[4] == 'RTSP_1' and main1_frame != None:
                        self.isFirstMonit = False
                        for i in self.channel_list:
                            if i == channel:
                                i.setStyleSheet(self.selected_color)
                            else:
                                i.setStyleSheet(self.no_selected_color)
                        for j in self.ch_rect.keys():
                            if self.ch_rect[j] == None:
                                continue
                            if channel_rect == self.ch_rect[j]:
                                self.ch_rect[j][5] = True
                            else:
                                self.ch_rect[j][5] = False

                        selected_main1 = True
                        selected_main2 = False
                        selected_main3 = False
                        self.monit_thread.change_channel_rect(channel_rect=channel_rect,ch='RTSP_1',isABS=isABS,selected_ch=selected_ch,isFirst=self.isFirstMonit)

                        #self.monit_class.monit_label.setPixmap(ch_frame[0].copy(channel_rect[0],channel_rect[1],channel_rect[2],channel_rect[3]).scaled(1280,720))

                    if channel_rect[4] == 'RTSP_2' and main2_frame != None:
                        self.isFirstMonit = False
                        for i in self.channel_list:
                            if i == channel:
                                i.setStyleSheet(self.selected_color)
                            else:
                                i.setStyleSheet(self.no_selected_color)
                        for j in self.ch_rect.keys():
                            if self.ch_rect[j] == None:
                                continue
                            if channel_rect == self.ch_rect[j]:
                                self.ch_rect[j][5] = True
                            else:
                                self.ch_rect[j][5] = False

                        selected_main1 = False
                        selected_main2 = True
                        selected_main3 = False
                        self.monit_thread.change_channel_rect(channel_rect=channel_rect,ch='RTSP_2',isABS=isABS,selected_ch=selected_ch,isFirst=self.isFirstMonit)


                    if channel_rect[4] == 'RTSP_3' and main3_frame != None:
                        self.isFirstMonit = False
                        for i in self.channel_list:
                            if i == channel:
                                i.setStyleSheet(self.selected_color)
                            else:
                                i.setStyleSheet(self.no_selected_color)
                        for j in self.ch_rect.keys():
                            if self.ch_rect[j] == None:
                                continue
                            if channel_rect == self.ch_rect[j]:
                                self.ch_rect[j][5] = True
                            else:
                                self.ch_rect[j][5] = False

                        selected_main1 = False
                        selected_main2 = False
                        selected_main3 = True
                        self.monit_thread.change_channel_rect(channel_rect=channel_rect,ch='RTSP_3',isABS=isABS,selected_ch=selected_ch,isFirst=self.isFirstMonit)


                except Exception as e:
                    print(f"key handle event error :: {e}")

        if self.rtsp_num == 2:
            key_map = {
                Qt.Key.Key_Insert: (self.main1, self.ch_rect['RTSP_1'],self.isABS['RTSP_1'], 'RTSP_1'),
                Qt.Key.Key_Home: (self.main2, self.ch_rect['RTSP_2'],self.isABS['RTSP_2'], 'RTSP_2'),
                Qt.Key.Key_1: (self.ch1, self.ch_rect['ch1'],self.isABS['ch1'], "ch1"),
                Qt.Key.Key_2: (self.ch2, self.ch_rect['ch2'],self.isABS['ch2'], "ch2"),
                Qt.Key.Key_3: (self.ch3, self.ch_rect['ch3'],self.isABS['ch3'], "ch3"),
                Qt.Key.Key_4: (self.ch4, self.ch_rect['ch4'],self.isABS['ch4'], "ch4"),
                Qt.Key.Key_5: (self.ch5, self.ch_rect['ch5'],self.isABS['ch5'], "ch5"),
                Qt.Key.Key_6: (self.ch6, self.ch_rect['ch6'],self.isABS['ch6'], "ch6"),
                Qt.Key.Key_7: (self.ch7, self.ch_rect['ch7'],self.isABS['ch7'], "ch7"),
                Qt.Key.Key_8: (self.ch8, self.ch_rect['ch8'],self.isABS['ch8'], "ch8"),
                Qt.Key.Key_9: (self.ch9, self.ch_rect['ch9'],self.isABS['ch9'], "ch9"),
                Qt.Key.Key_0: (self.ch10, self.ch_rect['ch10'],self.isABS['ch10'], "ch10"),
            }
        if self.rtsp_num == 3:
            key_map = {
                Qt.Key.Key_Insert: (self.main1, self.ch_rect['RTSP_1'],self.isABS['RTSP_1'], "RTSP_1"),
                Qt.Key.Key_Home: (self.main2, self.ch_rect['RTSP_2'],self.isABS['RTSP_2'], "RTSP_2"),
                Qt.Key.Key_PageUp: (self.main3, self.ch_rect['RTSP_3'],self.isABS['RTSP_3'], "RTSP_3"),
                Qt.Key.Key_1: (self.ch1, self.ch_rect['ch1'],self.isABS['ch1'], "ch1"),
                Qt.Key.Key_2: (self.ch2, self.ch_rect['ch2'],self.isABS['ch2'], "ch2"),
                Qt.Key.Key_3: (self.ch3, self.ch_rect['ch3'],self.isABS['ch3'], "ch3"),
                Qt.Key.Key_4: (self.ch4, self.ch_rect['ch4'],self.isABS['ch4'], "ch4"),
                Qt.Key.Key_5: (self.ch5, self.ch_rect['ch5'],self.isABS['ch5'], "ch5"),
                Qt.Key.Key_6: (self.ch6, self.ch_rect['ch6'],self.isABS['ch6'], "ch6"),
                Qt.Key.Key_7: (self.ch7, self.ch_rect['ch7'],self.isABS['ch7'], "ch7"),
                Qt.Key.Key_8: (self.ch8, self.ch_rect['ch8'],self.isABS['ch8'], "ch8"),
                Qt.Key.Key_9: (self.ch9, self.ch_rect['ch9'],self.isABS['ch9'], "ch9"),
                Qt.Key.Key_0: (self.ch10, self.ch_rect['ch10'],self.isABS['ch10'], "ch10"),
            }


        if event.key() in key_map:
            channel, channel_rect, isABS, selected_ch = key_map[event.key()]
            handle_channel_key(channel, channel_rect, isABS, selected_ch)

    # TODO : 첫번째 rtsp 서버 실행 함수
    def run_first_rtsp(self):
        try:
            if self.first_rtsp != None:
                if self.rtsp_worker1 != None:
                    self.rtsp_worker1.stop()
                self.rtsp_worker1 = rtsp_worker(parent=self, url=self.first_rtsp,name="first")

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

                self.rtsp_worker2 = rtsp_worker(parent=self, url=self.second_rtsp,name="second")

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
                self.rtsp_worker3 = rtsp_worker(parent=self, url=self.third_rtsp, name="third")

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
        Config.config['PIP'][ch] = 'None'

    def get_rotate_image(self, ch, main_frame, width_rate, height_rate, scaled_width, scaled_height):
        try:
            top_left, top_right, bottom_left, bottom_right = get_rotate_point(
                round(self.ch_rect[ch][0] * width_rate),
                round(self.ch_rect[ch][1] * height_rate),
                round(self.ch_rect[ch][2] * width_rate),
                round(self.ch_rect[ch][3] * height_rate),
                self.ch_rect[ch][6]
            )
        except Exception as e:
            print(e)
            return None

        resize_image = main_frame

        # 사각형 영역을 QPolygon으로 정의
        polygon = QPolygon([top_left, top_right, bottom_right, bottom_left])

        region = QRegion(polygon)
        
        # 필요한 부분만 crop하기 위해 boundingRect 사용
        cropped_rect = region.boundingRect()
        cropped_pixmap = resize_image.copy(cropped_rect)

        min_x = 9999
        min_y = 9999
        max_x = 0
        max_y = 0
        for i in polygon:
            min_x = min(min_x, i.x())
            min_y = min(min_y, i.y())
            max_x = max(max_x, i.x())
            max_y = max(max_y, i.y())

        rotate_width = abs(round(max_x - min_x))
        rotate_height = abs(round(max_y - min_y))

        if rotate_width < rotate_height:
            rotate_width = abs(round(max_y - min_y))
            rotate_height = abs(round(max_x - min_x))

        # 회전된 이미지의 크기 설정
        rotated_pixmap = QPixmap(rotate_width, rotate_height)
        #rotated_pixmap.fill(Qt.transparent)  # 투명 배경으로 초기화

        # 중심 좌표 계산
        center_x = round(rotate_width / 2)
        center_y = round(rotate_height / 2)

        # 원래의 대각선 각도로 되돌리기 위한 변환
        transform = QTransform()
        transform.translate(center_x, center_y)  # 중심으로 이동
        transform.rotate(-self.ch_rect[ch][6])  # 원래의 대각선 각도로 회전 (예: -45도)
        transform.translate(-center_x, -center_y)  # 다시 원래 위치로 이동


        # QPainter를 사용하여 회전된 이미지 그리기
        painter = QPainter(rotated_pixmap)
        painter.setTransform(transform)
        painter.drawPixmap((rotate_width - cropped_pixmap.width()) // 2,
                           (rotate_height - cropped_pixmap.height()) // 2,
                           cropped_pixmap)
        painter.end()

        # 회전된 이미지에서 크롭할 영역 재계산
        final_pixmap = rotated_pixmap.copy((rotate_width - round(self.ch_rect[ch][2] * width_rate)) // 2,
                                           (rotate_height - round(self.ch_rect[ch][3] * height_rate)) // 2,
                                           round(self.ch_rect[ch][2] * width_rate),
                                           round(self.ch_rect[ch][3] * height_rate))

        return final_pixmap.scaled(int(scaled_width), int(scaled_height))


if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)
        myWindow = WindowClass()
        myWindow.showMaximized()
        sys.exit(app.exec_())
    except Exception as e:
        print(e)
