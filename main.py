import sys
from pathlib import Path

from PyQt6 import uic
from PyQt6.QtCore import QDate
from PyQt6.QtWidgets import QApplication, QMainWindow, QDialog


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        ui_path = Path(__file__).resolve().parent / "app" / \
            "design_ui" / "main_window.ui"
        uic.loadUi(str(ui_path), self)

        self.addTaskButton.clicked.connect(self.open_task_dialog)

    def open_task_dialog(self):
        dialog = TaskDialog()

        if dialog.exec() == QDialog.DialogCode.Accepted:
            title = dialog.titleEdit.text()
            description = dialog.descriptionEdit.toPlainText()
            date = dialog.taskDateEdit.date().toString("dd.MM.yyyy")
            duration = dialog.durationSpinBox.value()
            category = dialog.categoryComboBox.currentText()
            status = dialog.statusComboBox.currentText()

            print("Название:", title)
            print("Описание:", description)
            print("Дата:", date)
            print("Длительность:", duration)
            print("Категория:", category)
            print("Статус:", status)


class TaskDialog(QDialog):
    def __init__(self):
        super().__init__()

        ui_path = (
            Path(__file__).resolve().parent
            / "app" / "design_ui" / "task_dialog.ui"
        )
        uic.loadUi(str(ui_path), self)
        self.taskDateEdit.setDate(QDate.currentDate())

        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)


app = QApplication(sys.argv)
window = MainWindow()
window.show()
sys.exit(app.exec())
