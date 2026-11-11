
from PyQt6 import uic
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QDialog


class SuccessDialog(QDialog):
    def __init__(self):
        super().__init__()

        uic.loadUi("app/design_ui/success_dialog.ui", self)

        image = QPixmap("app/pictch/win.jpg")

        image = image.scaled(
            250, 200,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )

        self.successImageLabel.setPixmap(image)
        self.successTextLabel.setText("Все задачи выполнены!")

        self.closeButton.clicked.connect(self.accept)
