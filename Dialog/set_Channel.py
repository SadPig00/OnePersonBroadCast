from PyQt5 import uic
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import cv2
import sys,os
import Config
isExe = Config.config['PROGRAM']['isExe'] == 'true'

if isExe:
    form_class = uic.loadUiType(f"{os.path.dirname(__file__)}\\UI\\Set_Channel.ui")[0]
if not isExe:
    form_class = uic.loadUiType('./UI/Set_Channel.ui')[0]

class Set_Channel_Dialog(QDialog, form_class):
    # TODO : main UI에 좌표를 전달하는 signal
    get_rectangle_signal = pyqtSignal(str, str, list)

    def __init__(self, frame, rtsp_name,origin_width):
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
        self.rtsp_image.wheelEvent = self.wheelEvent

        self.buttonBox.accepted.connect(self.emit_rectangle_signal)
        self.buttonBox.rejected.connect(self.reject)

    def draw_rectangle(self, center_point):
        self.clear_rectangle()

        half_width = round(self.rect_width / 2)
        half_height = round(self.rect_height / 2)
        top_left = QPoint(center_point.x() - half_width, center_point.y() - half_height)
        bottom_right = QPoint(center_point.x() + half_width, center_point.y() + half_height)

        if self.forceSize and self.frame_width >= 1280:
            self.rect_width = round(1280* (self.frame_width/self.origin_width))
            self.rect_height = round(720*(self.frame_width/self.origin_width))
            half_width = round(self.rect_width / 2)
            half_height = round(self.rect_height / 2)
            top_left = QPoint(center_point.x() - half_width, center_point.y() - half_height)
            bottom_right = QPoint(center_point.x() + half_width, center_point.y() + half_height)

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
        painter = QPainter(self.pixmap)
        painter.setPen(QPen(Qt.green, 2, Qt.SolidLine))

        rect = QRect(self.rect_start_point, QSize(self.rect_width, self.rect_height))
        painter.drawRect(rect)

        font = QFont()
        font.setFamily('Times')
        font.setBold(True)
        font.setPointSize(15)
        painter.setFont(font)
        painter.drawText(QRect(self.rect_start_point.x() + 10, self.rect_start_point.y() + 10, self.rect_width,self.rect_height), Qt.TextWordWrap,f'{round(self.rect_width * self.origin_width_rate)} x {round(self.rect_height * self.origin_width_rate)}')  # rect 위에 key 값을 글자로 씀
        painter.end()

        self.rtsp_image.setPixmap(self.pixmap)

    def clear_rectangle(self):
        self.pixmap = QPixmap(self.original_pixmap)
        self.rtsp_image.setPixmap(self.pixmap)

    def select_froceSize(self):
        if self.forceSize:
            self.forceSize = False
        else:
            self.forceSize = True
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.frame_width > event.pos().x() > 0 and self.frame_height > event.pos().y() > 0:
            self.draw_rectangle(event.pos())

    def wheelEvent(self, event):
        if not self.forceSize:
            delta = event.angleDelta().y() // 120  # Typical wheel step is 120
            change_w = delta * 16
            change_h = delta * 9

            new_width = self.rect_width + change_w
            new_height = self.rect_height + change_h

            if new_width > 0 and new_height > 0 and new_width <= self.frame_width and new_height <= self.frame_height:
                self.rect_width = new_width
                self.rect_height = new_height

            if self.rect_start_point is None:
                center_point = QPoint(self.frame_width // 2, self.frame_height // 2)
            else:
                center_point = self.rect_start_point + QPoint(self.rect_width // 2, self.rect_height // 2)

            self.draw_rectangle(center_point)
        event.accept()

    def emit_rectangle_signal(self):
        selected_ch = self.channelBox.currentText()

        if self.rect_start_point is None:
            return
        rect_point = [self.rect_start_point.x(), self.rect_start_point.y(), self.rect_width, self.rect_height]
        self.get_rectangle_signal.emit(selected_ch, self.rtsp_name, rect_point)
        self.accept()
