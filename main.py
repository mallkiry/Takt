import sys
from pathlib import Path
import sqlite3

from PyQt6 import uic
from PyQt6.QtCore import QDate
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QDialog,
    QTableWidgetItem, QHeaderView, QMessageBox
)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        ui_path = Path(__file__).resolve().parent / "app" / \
            "design_ui" / "main_window.ui"
        uic.loadUi(str(ui_path), self)
        self.tasksTable.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )

        self.tasksTable.setWordWrap(True)

        self.addTaskButton.clicked.connect(self.open_task_dialog)
        self.selectedDateEdit.setDate(QDate.currentDate())

        self.selectedDateEdit.dateChanged.connect(self.load_tasks)

        self.load_tasks()
        self.deleteTaskButton.clicked.connect(self.delete_task)
        self.tasksTable.setSortingEnabled(False)
        self.deleteTaskButton.clicked.connect(self.delete_task)

    def open_task_dialog(self):
        dialog = TaskDialog()

        if dialog.exec() == QDialog.DialogCode.Accepted:
            title = dialog.titleEdit.text().strip()
            description = dialog.descriptionEdit.toPlainText()
            date = dialog.taskDateEdit.date().toString("yyyy-MM-dd")
            duration = dialog.durationSpinBox.value()
            status = dialog.statusComboBox.currentText()

            if not title:
                print("Введите название задачи")
                return

            connection = sqlite3.connect("takt.db")
            cursor = connection.cursor()

            cursor.execute("""
                INSERT INTO tasks
                (title, description, task_date, duration, category_id, status)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (title, description, date, duration, None, status))

            connection.commit()
            connection.close()

            print("Задача успешно сохранена!")
            self.load_tasks()

    def load_tasks(self):
        date = self.selectedDateEdit.date().toString("yyyy-MM-dd")

        connection = sqlite3.connect("takt.db")
        cursor = connection.cursor()

        tasks = cursor.execute("""
            SELECT id, title, task_date, duration, status
            FROM tasks
            WHERE task_date = ?
            ORDER BY id
        """, (date,)).fetchall()

        connection.close()

        self.tasksTable.setRowCount(0)
        self.task_ids = []

        for i, task in enumerate(tasks):
            self.task_ids.append(task[0])

            self.tasksTable.insertRow(i)
            self.tasksTable.setItem(i, 0, QTableWidgetItem(task[1]))
            self.tasksTable.setItem(i, 1, QTableWidgetItem(task[2]))
            self.tasksTable.setItem(
                i, 2, QTableWidgetItem(f"{task[3]} мин")
            )
            self.tasksTable.setItem(
                i, 3, QTableWidgetItem("Без категории")
            )
            self.tasksTable.setItem(i, 4, QTableWidgetItem(task[4]))

        self.tasksTable.resizeRowsToContents()

    def delete_task(self):
        row = self.tasksTable.currentRow()

        if row == -1:
            QMessageBox.warning(
                self, "Ошибка", "Выберите задачу для удаления"
            )
            return

        task_id = self.task_ids[row]

        answer = QMessageBox.question(
            self,
            "Удаление задачи",
            "Вы уверены, что хотите удалить задачу?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if answer == QMessageBox.StandardButton.Yes:
            connection = sqlite3.connect("takt.db")
            cursor = connection.cursor()

            cursor.execute(
                "DELETE FROM tasks WHERE id = ?", (task_id,)
            )

            connection.commit()
            connection.close()

            self.load_tasks()


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
