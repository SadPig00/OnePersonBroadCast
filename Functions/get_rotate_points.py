from PyQt5.QtCore import *
from PyQt5.QtGui import *
import math
def rotate_point(point, center, angle):
    x_new = (point.x() - center.x()) * math.cos(angle) - (point.y() - center.y()) * math.sin(angle) + center.x()
    y_new = (point.x() - center.x()) * math.sin(angle) + (point.y() - center.y()) * math.cos(angle) + center.y()
    return QPoint(round(x_new), round(y_new))


def get_rotate_point(x,y,width,height,rotate):
    # 사각형의 중심점 계산
    center_x = round(x + width / 2)
    center_y = round(y + height / 2)

    # 각 꼭짓점의 원래 좌표 계산
    top_left = QPoint(x, y)
    top_right = QPoint(x + width, y)
    bottom_left = QPoint(x, y + height)
    bottom_right = QPoint(x + width, y + height)

    # 회전 각도 (radian 단위로 변환)
    angle_rad = math.radians(rotate)

    # 각 꼭짓점 회전
    rotated_top_left = rotate_point(top_left, QPoint(center_x, center_y), angle_rad)
    rotated_top_right = rotate_point(top_right, QPoint(center_x, center_y), angle_rad)
    rotated_bottom_left = rotate_point(bottom_left, QPoint(center_x, center_y), angle_rad)
    rotated_bottom_right = rotate_point(bottom_right, QPoint(center_x, center_y), angle_rad)

    return [rotated_top_left, rotated_top_right, rotated_bottom_left, rotated_bottom_right]