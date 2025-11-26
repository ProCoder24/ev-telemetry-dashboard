import sys
import os
#os.chdir("/home/userpi/Py_Dash_F2")

from PyQt6 import QtWidgets, QtGui
from PyQt6.QtCore import QTimer, Qt, QRect
from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QLabel
from PyQt6.QtGui import QFontDatabase, QPixmap, QPainter, QColor

from DashWindow_p5 import Ui_MainWindow

class NeedleIndicator:
    def __init__(self, scene, pixmap_path, pivot, percent_range, start_angle, max_value):
        self.pixmap = QtGui.QPixmap(pixmap_path)
        self.item = QGraphicsPixmapItem(self.pixmap)
        self.item.setTransformOriginPoint(*pivot)
        self.item.setPos(0, 0)
        scene.addItem(self.item)
        self.angle_range = percent_range
        self.start_angle = start_angle
        self.target_value = 0
        self.current_value = 0
        self.smooth_factor = 0.2
        self.max_value = max_value

    def set_target(self, value):
        self.target_value = value

    def update(self):
        diff = self.target_value - self.current_value
        self.current_value += diff * self.smooth_factor
        percent = max(0, min(self.current_value / self.max_value, 1.0))
        rotation = self.start_angle + percent * self.angle_range
        self.item.setRotation(rotation)

class NumberLabel(QLabel):
    def __init__(self, parent, font_family, font_size, color, geometry):
        super().__init__(parent)
        font = QtGui.QFont(font_family, font_size, QtGui.QFont.Weight.Bold)
        self.setFont(font)
        self.setStyleSheet(f"color: {color}; background: transparent;")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setGeometry(*geometry)
        self.target_value = 0
        self.current_value = 0
        self.smooth_factor = 0.2

    def set_target(self, value):
        self.target_value = value

    def update(self):
        diff = self.target_value - self.current_value
        self.current_value += diff * self.smooth_factor
        self.setText(f"{int(self.current_value):4d}")

class ColoredStatusLetter(QLabel):
    def __init__(self, parent, letter, geometry, font_family, font_size, active_color, inactive_color="gray"):
        super().__init__(parent)
        self.letter = letter
        self.active_color = active_color
        self.inactive_color = inactive_color
        self.setText(letter)
        font = QtGui.QFont(font_family, font_size, QtGui.QFont.Weight.Bold)
        self.setFont(font)
        self.setGeometry(*geometry)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.set_status(False)

    def set_status(self, active=True):
        color = self.active_color if active else self.inactive_color
        self.setStyleSheet(f"color: {color}; background: transparent;")


class ColoredCircleIndicator(QLabel):
    def __init__(self, parent, geometry):
        super().__init__(parent)
        self.setGeometry(*geometry)
        self.current_color = QColor("transparent")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def set_color(self, color_name):
        self.current_color = QColor(color_name)
        self.update()  # Triggers paintEvent

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        diameter = min(self.width(), self.height()) * 0.85
        center_x = self.width() // 2
        center_y = self.height() // 2

        rect = QRect(
            int(center_x - diameter / 2),
            int(center_y - diameter / 2),
            int(diameter),
            int(diameter)
        )
        painter.setBrush(self.current_color)
        painter.setPen(Qt.GlobalColor.black)  # Black border
        painter.drawEllipse(rect)

class DashboardTester:
    def __init__(self, dashboard, testing_mode=True):
        self.dashboard = dashboard
        self.testing_mode = testing_mode
        self.bus = None
        if not testing_mode:
            try:
                import can
                self.bus = can.Bus(
                    interface='socketcan',
                    channel='can0',
                    bitrate=500000
                )
                print("✓ CAN interface initialized")
            except ImportError:
                print("✗ python-can library not installed")
                self.bus = None
            except Exception as e:
                print(f"✗ CAN initialization error: {e}")
                self.bus = None

    def update(self):
        if self.testing_mode or self.bus is None:
            return
        d = self.dashboard
        try:
            while True:
                msg = self.bus.recv(timeout=0)
                if msg is None:
                    break
                print(f"ID: {msg.arbitration_id}, DLC: {msg.dlc}, DATA: {msg.data}")
                print(
                    f"CAN RX: arb_id=0x{msg.arbitration_id:X}, len={msg.dlc}, data={msg.data.hex()}"
                )

                cmd_id = (msg.arbitration_id >> 8) & 0xFF

                if cmd_id == 9 and len(msg.data) >= 8:
                    erpm = int.from_bytes(msg.data[0:4], 'big', signed=True)
                    current_out = int.from_bytes(msg.data[4:6], 'big', signed=True) / 10.0
                    print(f"VESC STATUS: erpm={erpm}, out_current={current_out}")
                    d.target_values['rpm'] = max(0, min(int(erpm/4), 8000))
                    d.target_values['out_curr'] = max(0, min(int(current_out), 500))

                elif cmd_id == 16 and len(msg.data) >= 8:
                    temp_drive = int.from_bytes(msg.data[0:2], 'big', signed=True) / 10.0
                    temp_motor = int.from_bytes(msg.data[2:4], 'big', signed=True) / 10.0
                    current_in = int.from_bytes(msg.data[4:6], 'big', signed=True) / 10.0
                    temp_mr = int.from_bytes(msg.data[6:8], 'big', signed=True) / 10.0
                    print(
                        f"VESC STATUS_4: temp_drive={temp_drive}, temp_motor={temp_motor}, in_current={current_in}, temp_mr={temp_mr}"
                    )
                    d.target_values['in_curr'] = max(0, min(int(current_in), 500))
                    d.target_values['temp_drive'] = max(25, min(int(temp_drive), 200))
                    d.target_values['temp_motor'] = max(25, min(int(temp_motor), 200))
                    d.target_values['temp_mr'] = max(25, min(int(temp_mr), 200))

                elif msg.arbitration_id == 0x101 and len(msg.data) >= 8:
                    gear         = int.from_bytes(msg.data[0:1], 'big', signed=False)
                    etat         = int.from_bytes(msg.data[1:2], 'big', signed=False)
                    manuel_auto  = int.from_bytes(msg.data[2:3], 'big', signed=False)
                    vitesse      = int.from_bytes(msg.data[3:4], 'big', signed=False)
                    temp_mr      = int.from_bytes(msg.data[4:5], 'big', signed=False)
                    rpm          = int.from_bytes(msg.data[5:6], 'big', signed=False)
                    curren_outAC = int.from_bytes(msg.data[6:7], 'big', signed=False)
                    # msg.data[7] left for future use/filling/unneeded

                    gear_unsigned = gear if gear >= 0 else gear + 256
                    etat_unsigned = etat if etat >= 0 else etat + 256
                    manuel_auto_unsigned = manuel_auto if manuel_auto >= 0 else manuel_auto + 256

                    print(
                        f"VCU AFF CAN [0x101]: raw={msg.data.hex()} | "
                        f"GEAR={gear} ({gear_unsigned}), "
                        f"ETAT={etat} ({etat_unsigned}), "
                        f"MANUEL_AUTO={manuel_auto} ({manuel_auto_unsigned}), "
                        f"VITESSE={vitesse}, "
                        f"TEMP_MR={temp_mr}, "
                        f"RPM={rpm}, "
                        f"Curren_outAC={curren_outAC}"
                    )

                    if hasattr(d, 'circle_state_indicator') and d.circle_state_indicator:
                        if etat_unsigned < 75:
                            d.circle_state_indicator.set_color("orange")
                        elif 75 <= etat_unsigned < 125:
                            d.circle_state_indicator.set_color("green")
                        elif 175 <= etat_unsigned < 225:
                            d.circle_state_indicator.set_color("red")
                        else:
                            d.circle_state_indicator.set_color("transparent")

                    d.letters_speed['R'].set_status(gear_unsigned >= 175)
                    d.letters_speed['1'].set_status(gear_unsigned < 75)
                    d.letters_speed['2'].set_status(75 <= gear_unsigned < 125)
                    d.letters_speed['3'].set_status(125 <= gear_unsigned < 175)

                    d.letters_mode['M'].set_status(manuel_auto_unsigned > 150)
                    d.letters_mode['A'].set_status(manuel_auto_unsigned < 150)

                    d.target_values['kmh'] = vitesse
                    d.target_values['temp_mr'] = max(25, temp_mr)
                    d.target_values['rpm'] = rpm
                    d.target_values['out_curr'] = curren_outAC

        except Exception as e:
            print("CAN read error:", e)

class DashboardWindow(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)

        self.lbl_Tach1.deleteLater()
        self.lbl_Tach2.deleteLater()
        self.lbl_RPM_888.hide()
        self.lbl_KM_H_888.hide()
        self.lbl_888_IN_CURR.hide()
        self.lbl_888_OUT_CURRENT.hide()
        self.lbl_888_T_MR.hide()
        self.lbl_888_T_MOTEUR.hide()
        self.lbl_888_T_DRIVE.hide()
        self.lbl_MODE_M.hide()
        self.lbl_MODE_A.hide()
        self.lbl_num_R.hide()
        self.lbl_num_1.hide()
        self.lbl_num_2.hide()
        self.lbl_num_3.hide()

        font_path = os.path.join(os.path.dirname(__file__), "FONT", "Sportypo.ttf")
        font_id = QFontDatabase.addApplicationFont(font_path)
        if font_id == -1:
            sportypo_family = "Arial"
        else:
            sportypo_family = QFontDatabase.applicationFontFamilies(font_id)[0]

        self.scene = QGraphicsScene()
        try:
            label_geometry = self.lbl_Tach1.geometry()
            label_parent = self.lbl_Tach1.parent()
        except Exception:
            label_geometry = self.geometry()
            label_parent = self
        self.lbl_Tach1 = QGraphicsView(label_parent)
        self.lbl_Tach1.setGeometry(label_geometry)
        self.lbl_Tach1.setScene(self.scene)
        self.lbl_Tach1.setStyleSheet("background: transparent; border: none;")
        self.lbl_Tach1.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.lbl_Tach1.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.kmh_needle = NeedleIndicator(
            self.scene, "IMAGE/Tach.png", (1560.130, 394.130), 270, 41, 150
        )
        self.rpm_needle = NeedleIndicator(
            self.scene, "IMAGE/Tach2.png", (359.553, 394.468), 270, 41, 10000
        )
        self.scene.setSceneRect(0, 0, self.kmh_needle.pixmap.width(), self.kmh_needle.pixmap.height())
        self.lbl_Tach1.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

        self.animated_labels = {
            'kmh': NumberLabel(self.centralwidget, sportypo_family, 60, "deepskyblue", (1380, 590, 330, 110)),
            'rpm': NumberLabel(self.centralwidget, sportypo_family, 60, "deepskyblue", (180, 590, 330, 110)),
            'in_curr': NumberLabel(self.centralwidget, sportypo_family, 30, "magenta", (1330, 730, 310, 110)),
            'out_curr': NumberLabel(self.centralwidget, sportypo_family, 30, "magenta", (1330, 850, 310, 110)),
            'temp_motor': NumberLabel(self.centralwidget, sportypo_family, 30, "red", (320, 742, 310, 110)),
            'temp_drive': NumberLabel(self.centralwidget, sportypo_family, 30, "red", (320, 825, 310, 110)),
            'temp_mr': NumberLabel(self.centralwidget, sportypo_family, 30, "red", (320, 905, 310, 110)),
        }

        self.letters_mode = {
            'M': ColoredStatusLetter(self.centralwidget, "MANUEL", (715, 190, 500, 90), sportypo_family, 50, "lime"),
            'A': ColoredStatusLetter(self.centralwidget, "AUTO", (700, 310, 500, 90), sportypo_family, 50, "orange"),
        }
        self.letters_speed = {
            'R': ColoredStatusLetter(self.centralwidget, "R", (710, 490, 100, 90), sportypo_family, 60, "red"),
            '1': ColoredStatusLetter(self.centralwidget, "1", (840, 490, 100, 90), sportypo_family, 60, "yellow"),
            '2': ColoredStatusLetter(self.centralwidget, "2", (980, 490, 100, 90), sportypo_family, 60, "yellow"),
            '3': ColoredStatusLetter(self.centralwidget, "3", (1130, 490, 100, 90), sportypo_family, 60, "yellow"),
        }

        self.circle_state_indicator = ColoredCircleIndicator(
            self.centralwidget,
            (900, 850, 150, 150)
        )

        self.TESTING_MODE = False
        self.target_values = {
            'rpm': 0,
            'kmh': 0,
            'in_curr': 0,
            'out_curr': 0,
            'temp_motor': 25,
            'temp_drive': 25,
            'temp_mr': 25,
        }

        self.tester = DashboardTester(self, testing_mode=self.TESTING_MODE)

        print("=" * 50)
        print("CAN MODE: Dashboard receives VESC packets & VCU AFF CAN")
        print("=" * 50)

        self.timer = QTimer(self)
        self.timer.setInterval(50)
        self.timer.timeout.connect(self.updateData)
        self.timer.start()

    def updateData(self):
        self.tester.update()
        for key, label in self.animated_labels.items():
            print(f"DEBUG label: {key}, target={self.target_values[key]}")
            label.set_target(self.target_values[key])
            label.update()
        self.kmh_needle.set_target(self.target_values['kmh'])
        self.kmh_needle.update()
        self.rpm_needle.set_target(self.target_values['rpm'])
        self.rpm_needle.update()

    def closeEvent(self, event):
        if hasattr(self.tester, "bus") and self.tester.bus is not None:
            try:
                self.tester.bus.shutdown()
            except Exception:
                pass
        event.accept()

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = DashboardWindow()
    window.show()
    sys.exit(app.exec())
