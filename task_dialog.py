import sqlite3

from PyQt6 import uic
from PyQt6.QtCore import QDate
from PyQt6.QtWidgets import QDialog


class TaskDialog(QDialog):
    def __init__(self):
        super().__init__()

        uic.loadUi("app/design_ui/task_dialog.ui", self)
        self.taskDateEdit.setDate(QDate.currentDate())

        connection = sqlite3.connect("takt.db")
        cursor = connection.cursor()

        categories = cursor.execute(
            "SELECT name FROM categories ORDER BY name"
        ).fetchall()

        connection.close()

        self.categoryComboBox.clear()
        self.categoryComboBox.addItem("Без категории")

        for category in categories:
            self.categoryComboBox.addItem(category[0])

        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
