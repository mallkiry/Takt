import sys
import sqlite3

from PyQt6 import uic
from PyQt6.QtCore import QDate, Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QDialog,
    QTableWidgetItem, QHeaderView, QMessageBox,
    QInputDialog, QColorDialog, QListWidgetItem
)

# главное окно всего приложения


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        uic.loadUi("app/design_ui/main_window.ui", self)

        self.tasksTable.horizontalHeader().setHighlightSections(False)

        self.tasksTable.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )

        self.tasksTable.setWordWrap(True)

        self.addTaskButton.clicked.connect(self.open_task_dialog)
        self.editTaskButton.clicked.connect(self.edit_task)

        self.selectedDateEdit.setDate(QDate.currentDate())
        self.selectedDateEdit.dateChanged.connect(self.load_tasks)

        self.load_tasks()

        self.tasksTable.itemChanged.connect(self.change_task_status)
        self.deleteTaskButton.clicked.connect(self.delete_task)
        self.tasksTable.setSortingEnabled(False)

        self.categoriesAction.triggered.connect(self.open_categories)
# открытие окна для добавления задачи + ее запись в БД

    def open_task_dialog(self):
        dialog = TaskDialog()

        if dialog.exec() == QDialog.DialogCode.Accepted:
            title = dialog.titleEdit.text().strip()
            description = dialog.descriptionEdit.toPlainText()
            date = dialog.taskDateEdit.date().toString("dd-MM-yyyy")
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

            print("Задача")
            self.load_tasks()
# добавление задачи из БД в таблицу планировщика + оформление выполненной задачи

    def load_tasks(self):
        date = self.selectedDateEdit.date().toString("dd-MM-yyyy")

        connection = sqlite3.connect("takt.db")
        cursor = connection.cursor()

        tasks = cursor.execute("""
            SELECT id, title, task_date, duration, status
            FROM tasks
            WHERE task_date = ?
            ORDER BY id
        """, (date,)).fetchall()

        connection.close()
        self.tasksTable.blockSignals(True)
        self.tasksTable.setRowCount(0)
        self.task_ids = []

        for i, task in enumerate(tasks):
            self.task_ids.append(task[0])
            self.tasksTable.insertRow(i)

            checkbox = QTableWidgetItem()

            if task[4] == "Готово":
                checkbox.setCheckState(Qt.CheckState.Checked)
            else:
                checkbox.setCheckState(Qt.CheckState.Unchecked)

            self.tasksTable.setItem(i, 0, checkbox)

            self.tasksTable.setItem(i, 1, QTableWidgetItem(task[1]))
            self.tasksTable.setItem(i, 2, QTableWidgetItem(task[2]))
            self.tasksTable.setItem(
                i, 3, QTableWidgetItem(f"{task[3]} мин")
            )
            self.tasksTable.setItem(
                i, 4, QTableWidgetItem("Без категории")
            )
            self.tasksTable.setItem(i, 5, QTableWidgetItem(task[4]))

            if task[4] == "Готово":
                for col in range(6):
                    self.tasksTable.item(i, col).setBackground(
                        QColor("#D3D3D3")
                    )

        self.tasksTable.resizeRowsToContents()
        self.tasksTable.blockSignals(False)
# изменение статуса задачи при изменении флажка готовности

    def change_task_status(self, item):
        if item.column() != 0:
            return

        row = item.row()
        task_id = self.task_ids[row]

        if item.checkState() == Qt.CheckState.Checked:
            status = "Готово"
        else:
            status = "Нужно сделать"

        connection = sqlite3.connect("takt.db")
        cursor = connection.cursor()

        cursor.execute(
            "UPDATE tasks SET status = ? WHERE id = ?",
            (status, task_id)
        )

        connection.commit()
        connection.close()

        self.load_tasks()
# редактирование задачи

    def edit_task(self):
        row = self.tasksTable.currentRow()

        if row == -1:
            QMessageBox.warning(
                self, "Ошибка", "Выберите задачу для изменения"
            )
            return

        task_id = self.task_ids[row]

        connection = sqlite3.connect("takt.db")
        cursor = connection.cursor()

        task = cursor.execute("""
            SELECT title, description, task_date, duration, status
            FROM tasks
            WHERE id = ?
        """, (task_id,)).fetchone()

        connection.close()

        if task is None:
            return

        dialog = TaskDialog()
        dialog.setWindowTitle("Изменить задачу")

        dialog.titleEdit.setText(task[0])
        dialog.descriptionEdit.setPlainText(task[1] or "")
        dialog.taskDateEdit.setDate(
            QDate.fromString(task[2], "dd-MM-yyyy")
        )
        dialog.durationSpinBox.setValue(task[3])
        dialog.statusComboBox.setCurrentText(task[4])

        if dialog.exec() == QDialog.DialogCode.Accepted:
            title = dialog.titleEdit.text().strip()
            description = dialog.descriptionEdit.toPlainText()
            date = dialog.taskDateEdit.date().toString("dd-MM-yyyy")
            duration = dialog.durationSpinBox.value()
            status = dialog.statusComboBox.currentText()

            if not title:
                QMessageBox.warning(
                    self, "Ошибка", "Введите название задачи"
                )
                return

            connection = sqlite3.connect("takt.db")
            cursor = connection.cursor()

            cursor.execute("""
                UPDATE tasks
                SET title = ?, description = ?, task_date = ?,
                    duration = ?, status = ?
                WHERE id = ?
            """, (title, description, date, duration, status, task_id))

            connection.commit()
            connection.close()

            self.load_tasks()
# удаление задачи

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
# открытие окна создания категории задач

    def open_categories(self):
        dialog = CategoryDialog()
        dialog.exec()

# окно создания задачи


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

# окно категории задач


class CategoryDialog(QDialog):
    def __init__(self):
        super().__init__()

        uic.loadUi("app/design_ui/category_dialog.ui", self)
        self.addCategoryButton.clicked.connect(self.add_category)
        self.colorCategoryButton.clicked.connect(self.change_category_color)
        self.load_categories()
# загрузка категорий в БД

    def load_categories(self):
        connection = sqlite3.connect("takt.db")
        cursor = connection.cursor()

        categories = cursor.execute(
            "SELECT name, color FROM categories ORDER BY name"
        ).fetchall()

        connection.close()

        self.categoriesList.clear()

        for name, color in categories:
            item = QListWidgetItem(name)
            item.setBackground(QColor(color))
            self.categoriesList.addItem(item)

        self.categoriesList.setCurrentRow(-1)
        self.categoriesList.clearSelection()

# добавление категорий

    def add_category(self):
        name, ok = QInputDialog.getText(
            self, "Новая категория", "Введите название категории:"
        )
        if not ok:
            return

        name = name.strip()

        if not name:
            QMessageBox.warning(
                self, "Ошибка", "Введите название категории"
            )
            return

        connection = sqlite3.connect("takt.db")
        cursor = connection.cursor()
        existing = cursor.execute(
            "SELECT id FROM categories WHERE name = ?", (name,)
        ).fetchone()

        if existing:
            QMessageBox.warning(
                self, "Ошибка", "Такая категория уже существует"
            )
            connection.close()
            return
        cursor.execute(
            "INSERT INTO categories (name) VALUES (?)", (name,)
        )

        connection.commit()
        connection.close()
        self.load_categories()

    def change_category_color(self):
        items = self.categoriesList.selectedItems()

        if not items:
            QMessageBox.warning(
                self, "Ошибка", "Сначала выберите категорию"
            )
            return

        item = items[0]
        name = item.text()

        color = QColorDialog.getColor(
            item.background().color(),
            self,
            "Выберите цвет категории"
        )

        if not color.isValid():
            return

        connection = sqlite3.connect("takt.db")
        cursor = connection.cursor()

        cursor.execute(
            "UPDATE categories SET color = ? WHERE name = ?",
            (color.name(), name)
        )

        connection.commit()
        connection.close()

        self.load_categories()


app = QApplication(sys.argv)
window = MainWindow()
window.show()
sys.exit(app.exec())
