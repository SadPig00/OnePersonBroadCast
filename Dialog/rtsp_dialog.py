from PyQt5 import uic
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import Config
import tkinter
import sys, os
import Config
isExe = Config.config['PROGRAM']['isExe'] == 'true'
if isExe:
    form_class = uic.loadUiType(f"{os.path.dirname(__file__)}\\UI\\RTSP_Address.ui")[0]
if not isExe:
    form_class = uic.loadUiType('./UI/RTSP_Address.ui')[0]

class RTSP_dialog(QDialog, form_class):
    rtsp_address_signal = pyqtSignal(str)  # 커스텀 시그널 정의

    def __init__(self,server_num):
        super().__init__()
        self.setupUi(self)
        self.setFixedSize(self.width(),self.height())
        self.server_num = server_num
        self.setWindowTitle(self.server_num)


        self.first_rtsp = Config.config['RTSP']['first_rtsp']
        self.second_rtsp = Config.config['RTSP']['second_rtsp']
        self.third_rtsp = Config.config['RTSP']['third_rtsp']

        if self.server_num == "First RTSP":
            self.address_text.setPlainText(self.first_rtsp)
        if self.server_num == "Second RTSP":
            self.address_text.setPlainText(self.second_rtsp)
        if self.server_num == "Third RTSP":
            self.address_text.setPlainText(self.third_rtsp)

        # QDialogButtonBox와 신호-슬롯 연결
        self.rtsp_button.accepted.connect(self.emit_rtsp_address)
        self.rtsp_button.rejected.connect(self.reject)
    def emit_rtsp_address(self):
        address = self.address_text.toPlainText()
        if self.server_num == "First RTSP":
            Config.config.set('RTSP','first_rtsp',address)
        if self.server_num == "Second RTSP":
            Config.config.set('RTSP', 'second_rtsp', address)
        if self.server_num == "Third RTSP":
            Config.config.set('RTSP', 'third_rtsp', address)
        with open(Config.config_path,'w',encoding="UTF-8") as fp:
            Config.config.write(fp)
        self.rtsp_address_signal.emit(address)  # 시그널 발송
        self.accept()