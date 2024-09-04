import time

from PyQt5 import uic
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import cv2
import sys,os
import Config
import math

try:
    isExe = Config.config['PROGRAM']['isExe'] == 'true'

    if isExe:
        form_class = uic.loadUiType(f"{os.path.dirname(__file__)}\\UI\\Set_Channel.ui")[0]
    if not isExe:
        form_class = uic.loadUiType('./UI/Set_Channel.ui')[0]
except Exception as e:
    print(f"set Channel ixExe Error :: {e}")

class Set_Channel_Dialog(QDialog, form_class):
    # TODO : main UI에 좌표를 전달하는 signal
    get_rectangle_signal = pyqtSignal(str, str, list, int)

    def __init__(self, frame, rtsp_name,origin_width):
        try:
            super().__init__()
            self.setupUi(self)
            self.frame = frame
            self.rtsp_name = rtsp_name
            self.setWindowTitle(self.rtsp_name)
            self.forceSize = False
            self.forceSize_radio.clicked.connect(self.select_froceSize)

            self.frame_height = self.frame.height()
            self.frame_width = self.frame.width()
            self.origin_width = origin_width
            self.origin_width_rate = self.origin_width/self.frame_width

            self.resize(self.frame_width,self.frame_height)

            self.original_pixmap = self.frame.copy()
            self.rtsp_image.setPixmap(self.original_pixmap)

            self.rect_start_point = None

            self.rect_height = round(self.frame_height / 8)
            self.rect_width = round(self.rect_height * (16/9))

            self.rtsp_image.mousePressEvent = self.mousePressEvent
            self.rtsp_image.mouseMoveEvent = self.mouseMoveEvent
            self.rtsp_image.wheelEvent = self.wheelEvent

            self.buttonBox.accepted.connect(self.emit_rectangle_signal)
            self.buttonBox.rejected.connect(self.reject)

            self.diff_y = 0
            self.center_point = QPoint(0,0)


        except Exception as e:
            print(f"set Channel init Error :: {e}")
    def draw_rectangle(self):
        try:
            self.clear_rectangle()

            half_width = round(self.rect_width / 2)
            half_height = round(self.rect_height / 2)
            top_left = QPoint(self.center_point.x() - half_width, self.center_point.y() - half_height)
            bottom_right = QPoint(self.center_point.x() + half_width, self.center_point.y() + half_height)

            if self.forceSize and self.frame_width >= 1280:
                self.rect_width = round(1280* (self.frame_width/self.origin_width))
                self.rect_height = round(720*(self.frame_width/self.origin_width))
                half_width = round(self.rect_width / 2)
                half_height = round(self.rect_height / 2)
                self.top_left = QPoint(self.center_point.x() - half_width, self.center_point.y() - half_height)
                self.bottom_right = QPoint(self.center_point.x() + half_width, self.center_point.y() + half_height)

            if self.forceSize and self.frame_width < 1280:
                QMessageBox.about(self, "Set Channel", "This image width under 1280")

            if top_left.x() < 0:
                top_left.setX(0)
                bottom_right.setX(self.rect_width)
            if top_left.y() < 0:
                top_left.setY(0)
                bottom_right.setY(self.rect_height)
            if bottom_right.x() > self.frame_width:
                bottom_right.setX(self.frame_width)
                top_left.setX(self.frame_width - self.rect_width)
            if bottom_right.y() > self.frame_height:
                bottom_right.setY(self.frame_height)
                top_left.setY(self.frame_height - self.rect_height)

            self.rect_start_point = top_left

            """
            painter = QPainter(self.pixmap)
            painter.setPen(QPen(Qt.green, 2, Qt.SolidLine))
    
    
            rect = QRect(self.rect_start_point, QSize(self.rect_width, self.rect_height))
            painter.drawRect(rect)
    
            font = QFont()
            font.setFamily('Arial')
            font.setBold(True)
            font.setPointSize(15)
            painter.setFont(font)
            painter.drawText(QRect(self.rect_start_point.x() + 10, self.rect_start_point.y() + 10, self.rect_width,self.rect_height), Qt.TextWordWrap,f'{round(self.rect_width * self.origin_width_rate)} x {round(self.rect_height * self.origin_width_rate)}')  # rect 위에 key 값을 글자로 씀
            painter.end()
            """
            painter = QPainter(self.pixmap)

            center_x = self.rect_start_point.x() + self.rect_width / 2
            center_y = self.rect_start_point.y() + self.rect_height / 2

            painter.translate(center_x, center_y)  # 중심점으로 이동
            painter.rotate(self.diff_y)  # 회전
            painter.translate(-center_x, -center_y)  # 원래 위치로 이동

            painter.setPen(QPen(Qt.green, 2, Qt.SolidLine))
            rect = QRect(self.rect_start_point, QSize(self.rect_width, self.rect_height))

            painter.drawRect(rect)

            font = QFont()
            font.setFamily('Arial')
            font.setBold(True)
            font.setPointSize(15)
            painter.setFont(font)
            painter.drawText(QRect(self.rect_start_point.x() + 10, self.rect_start_point.y() + 10, self.rect_width,
                                   self.rect_height), Qt.TextWordWrap,
                             f'{round(self.rect_width * self.origin_width_rate)} x {round(self.rect_height * self.origin_width_rate)}')  # rect 위에 key 값을 글자로 씀
            painter.end()
            self.rtsp_image.setPixmap(self.pixmap)

        except Exception as e:
            print(f"draw rect Error :: {e}")
    def clear_rectangle(self):
        try:
            self.pixmap = QPixmap(self.original_pixmap)
            self.rtsp_image.setPixmap(self.pixmap)
        except Exception as e:
            print(f"clear rect Error :: {e}")

    def select_froceSize(self):
        try:
            if self.forceSize:
                self.forceSize = False
            else:
                self.forceSize = True
        except Exception as e:
            print(f"select forceSize Error :: {e}")
    def mousePressEvent(self, event):
        try:
            if event.button() == Qt.LeftButton and self.frame_width > event.pos().x() > 0 and self.frame_height > event.pos().y() > 0:
                self.center_point = event.pos()
                self.diff_y = 0
                self.draw_rectangle()
            if event.button() == Qt.RightButton and self.frame_width > event.pos().x() > 0 and self.frame_height > event.pos().y() > 0:
                self.prev_y = None

        except Exception as e:
            print(f"mousePress setChannel Error :: {e}")
    def mouseMoveEvent(self,event):
        try:
            if event.buttons() == Qt.MouseButton.LeftButton and self.frame_width > event.pos().x() > 0 and self.frame_height > event.pos().y() > 0:
                self.center_point = event.pos()
                self.draw_rectangle()
            if event.buttons() == Qt.MouseButton.RightButton and self.frame_width > event.pos().x() > 0 and self.frame_height > event.pos().y() > 0:
                if self.rect_start_point != None:
                    if self.prev_y != None:
                        if self.prev_y - event.pos().y() > 0 and self.diff_y > -90:
                            self.diff_y += -1
                            rotated_point = self.get_rotate_point()
                            if rotated_point[0].x() < 0 or rotated_point[0].y() < 0 or rotated_point[1].x() > self.frame_width or rotated_point[1].y() < 0 or rotated_point[2].x() < 0 or rotated_point[2].y() > self.frame_height or rotated_point[3].x() > self.frame_width or rotated_point[3].y() > self.frame_height:
                                self.diff_y += +1

                        if self.prev_y - event.pos().y() < 0 and self.diff_y < 90:
                            rotated_point = self.get_rotate_point()
                            self.diff_y += 1
                            rotated_point = self.get_rotate_point()
                            if rotated_point[0].x() < 0 or rotated_point[0].y() < 0 or rotated_point[1].x() > self.frame_width or rotated_point[1].y() < 0 or rotated_point[2].x() < 0 or rotated_point[2].y() > self.frame_height or rotated_point[3].x() > self.frame_width or rotated_point[3].y() > self.frame_height:
                                self.diff_y += -1
                        self.prev_y = None
                    if self.prev_y == None:
                        self.prev_y = event.pos().y()

                    self.draw_rectangle()
        except Exception as e:
            print(f"mouse Move setChannel Error :: {e}")
    # 회전 변환 함수
    def rotate_point(self,point, center, angle):
        try:
            x_new = (point.x() - center.x()) * math.cos(angle) - (point.y() - center.y()) * math.sin(angle) + center.x()
            y_new = (point.x() - center.x()) * math.sin(angle) + (point.y() - center.y()) * math.cos(angle) + center.y()
            return QPoint(round(x_new), round(y_new))
        except Exception as e:
            print(f"rotate point set Channel Error :: {e}")

    def get_rotate_point(self):
        try:
            # 사각형의 중심점 계산
            center_x = round(self.rect_start_point.x() + self.rect_width / 2)
            center_y = round(self.rect_start_point.y() + self.rect_height / 2)

            # 각 꼭짓점의 원래 좌표 계산
            top_left = QPoint(self.rect_start_point.x(), self.rect_start_point.y())
            top_right = QPoint(self.rect_start_point.x() + self.rect_width, self.rect_start_point.y())
            bottom_left = QPoint(self.rect_start_point.x(), self.rect_start_point.y() + self.rect_height)
            bottom_right = QPoint(self.rect_start_point.x() + self.rect_width,
                                  self.rect_start_point.y() + self.rect_height)

            # 회전 각도 (radian 단위로 변환)
            angle_rad = math.radians(self.diff_y)

            # 각 꼭짓점 회전
            rotated_top_left = self.rotate_point(top_left, QPoint(center_x, center_y), angle_rad)
            rotated_top_right = self.rotate_point(top_right, QPoint(center_x, center_y), angle_rad)
            rotated_bottom_left = self.rotate_point(bottom_left, QPoint(center_x, center_y), angle_rad)
            rotated_bottom_right = self.rotate_point(bottom_right, QPoint(center_x, center_y), angle_rad)

            return [rotated_top_left,rotated_top_right,rotated_bottom_left,rotated_bottom_right]
        except Exception as e:
            print(f"get rotate point set Channel Error :: {e}")
    def wheelEvent(self, event):
        try:
            if not self.forceSize:
                self.diff_y = 0
                delta = event.angleDelta().y() // 120  # Typical wheel step is 120
                change_w = delta * 16
                change_h = delta * 9

                new_width = self.rect_width + change_w
                new_height = self.rect_height + change_h

                if new_width > 0 and new_height > 0 and new_width <= self.frame_width and new_height <= self.frame_height:
                    self.rect_width = new_width
                    self.rect_height = new_height

                if self.rect_start_point is None:
                    self.center_point = QPoint(self.frame_width // 2, self.frame_height // 2)
                else:
                    self.center_point = self.rect_start_point + QPoint(self.rect_width // 2, self.rect_height // 2)


                self.draw_rectangle()
            event.accept()
        except Exception as e:
            print(f"wheel Event set Channel Error {e}")

    def emit_rectangle_signal(self):
        try:
            selected_ch = self.channelBox.currentText()

            if self.rect_start_point is None:
                return
            rect_point = [self.rect_start_point.x(), self.rect_start_point.y(), self.rect_width, self.rect_height]
            self.get_rectangle_signal.emit(selected_ch, self.rtsp_name, rect_point,self.diff_y)
            self.accept()
        except Exception as e:
            print(f"emit setChannel Error :: {e}")
