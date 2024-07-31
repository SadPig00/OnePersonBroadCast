from PyQt5 import uic
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import cv2
import sys

form_class = uic.loadUiType('./UI/Set_Channel.ui')[0]

class Set_Channel_Dialog(QDialog, form_class):
    # TODO : main UI에 좌표를 전달하는 signal
    get_rectangle_signal = pyqtSignal(str,str,list)

    def __init__(self, frame, rtsp_name):
        super().__init__()
        self.setupUi(self)
        self.frame = frame
        self.rtsp_name = rtsp_name
        self.setWindowTitle(self.rtsp_name)
        """
        self.frame = cv2.resize(self.frame, (1280, 720))
        self.frame_height, self.frame_width, self.channels = self.frame.shape
        """
        self.frame_height = self.frame.height()
        self.frame_width = self.frame.width()

        self.original_pixmap = frame.copy()
        self.rtsp_image.setPixmap(self.original_pixmap)

        self.rect_start_point = None
        self.rect_width = self.frame_width // 8
        self.rect_height = int(self.rect_width / (16 / 9))

        self.rtsp_image.mousePressEvent = self.mousePressEvent
        self.rtsp_image.wheelEvent = self.wheelEvent

        self.buttonBox.accepted.connect(self.emit_rectangle_signal)
        self.buttonBox.rejected.connect(self.reject)

    def draw_rectangle(self, center_point):
        self.clear_rectangle()

        half_width = self.rect_width // 2
        half_height = self.rect_height // 2
        top_left = QPoint(center_point.x() - half_width, center_point.y() - half_height)
        bottom_right = QPoint(center_point.x() + half_width, center_point.y() + half_height)

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
        painter.end()
        self.rtsp_image.setPixmap(self.pixmap)

    def clear_rectangle(self):
        self.pixmap = QPixmap(self.original_pixmap)
        self.rtsp_image.setPixmap(self.pixmap)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.draw_rectangle(event.pos())

    def wheelEvent(self, event):
        delta = event.angleDelta().y() // 120  # Typical wheel step is 120
        change = delta * 10
        new_width = self.rect_width + change
        new_height = int(new_width / (16 / 9))

        if new_width > 0 and new_height > 0 and new_width <= self.frame_width and new_height <= self.frame_height:
            self.rect_width = new_width
            self.rect_height = new_height

        if self.rect_start_point:
            center_point = self.rect_start_point + QPoint(self.rect_width // 2, self.rect_height // 2)
            self.draw_rectangle(center_point)
    def emit_rectangle_signal(self):
        selected_ch = self.channelBox.currentText()
        rect_point = [self.rect_start_point.x(),self.rect_start_point.y(),self.rect_width,self.rect_height]
        self.get_rectangle_signal.emit(selected_ch,self.rtsp_name,rect_point)
        self.accept()
