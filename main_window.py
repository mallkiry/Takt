import sqlite3

from PyQt6 import uic
from PyQt6.QtCore import QDate, Qt, QTime
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QMainWindow, QDialog, QTableWidgetItem,
    QHeaderView, QMessageBox, QFileDialog
)

from task_dialog import TaskDialog
from category_dialog import CategoryDialog
from datetime import datetime, timedelta, time


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        uic.loadUi("app/design_ui/main_window.ui", self)

        self.tasksTable.horizontalHeader().setHighlightSections(False)

        self.tasksTable.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )

        self.tasksTable.setWordWrap(True)
        self.planDayButton.clicked.connect(self.plan_day)
        self.exportScheduleButton.clicked.connect(self.export_schedule)
        self.addTaskButton.clicked.connect(self.open_task_dialog)
        self.editTaskButton.clicked.connect(self.edit_task)

        self.selectedDateEdit.setDate(QDate.currentDate())
        self.selectedDateEdit.setDisplayFormat("dd.MM.yyyy")
        self.selectedDateEdit.dateChanged.connect(self.load_tasks)

        self.load_tasks()

        self.tasksTable.itemChanged.connect(self.change_task_status)
        self.tasksTable.itemSelectionChanged.connect(
            self.show_description
        )
        self.deleteTaskButton.clicked.connect(self.delete_task)
        self.tasksTable.setSortingEnabled(False)

        self.categoriesAction.triggered.connect(self.open_categories)
# открытие окна для добавления задачи + ее запись в БД

    def open_task_dialog(self):
        dialog = TaskDialog()

        if dialog.exec() == QDialog.DialogCode.Accepted:
            title = dialog.titleEdit.text().strip()
            description = dialog.descriptionEdit.toPlainText()
            date = dialog.taskDateEdit.date().toString("yyyy-MM-dd")
            duration = dialog.durationSpinBox.value()
            status = dialog.statusComboBox.currentText()
            category = dialog.categoryComboBox.currentText()
            category_id = None
            start_time = None

            if dialog.fixedTimeCheckBox.isChecked():
                start_time = dialog.taskTimeEdit.time().toString("HH:mm")

            if not title:
                print("Введите название задачи")
                return
            connection = sqlite3.connect("takt.db")
            cursor = connection.cursor()

            if category != "Без категории":
                result = cursor.execute(
                    "SELECT id FROM categories WHERE name = ?",
                    (category,)
                ).fetchone()

                if result:
                    category_id = result[0]
            cursor.execute("""
                INSERT INTO tasks
                (title, description, task_date, duration,
                 category_id, status, start_time)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                title, description, date, duration,
                category_id, status, start_time
            ))

            connection.commit()
            connection.close()

            print("Задача")
            self.load_tasks()
# добавление задачи из БД в таблицу планировщика + оформление выполненной задачи

    def load_tasks(self):
        date = self.selectedDateEdit.date().toString("yyyy-MM-dd")

        connection = sqlite3.connect("takt.db")
        cursor = connection.cursor()

        tasks = cursor.execute("""
            SELECT tasks.id, tasks.title, tasks.task_date,
                   tasks.duration, tasks.status,
                   categories.name, categories.color,
                   tasks.start_time
            FROM tasks
            LEFT JOIN categories
            ON tasks.category_id = categories.id
            WHERE tasks.task_date = ?
            ORDER BY tasks.id
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

            date_text = QDate.fromString(
                task[2], "yyyy-MM-dd"
            ).toString("dd.MM.yyyy")

            if task[7]:
                date_text += f" {task[7]}"

            self.tasksTable.setItem(
                i, 2, QTableWidgetItem(date_text)
            )

            self.tasksTable.setItem(
                i, 3, QTableWidgetItem(f"{task[3]} мин")
            )
            category = task[5] or "Без категории"

            self.tasksTable.setItem(
                i, 4, QTableWidgetItem(category)
            )
            self.tasksTable.setItem(i, 5, QTableWidgetItem(task[4]))
            if task[6] and task[4] != "Готово":
                self.tasksTable.item(i, 4).setBackground(
                    QColor(task[6])
                )
            if task[4] == "Готово":
                for col in range(6):
                    self.tasksTable.item(i, col).setBackground(
                        QColor("#D3D3D3")
                    )

        self.tasksTable.resizeRowsToContents()
        self.tasksTable.blockSignals(False)

    def show_description(self):
        if not self.tasksTable.selectedItems():
            self.descriptionBrowser.clear()
            return

        row = self.tasksTable.currentRow()
        task_id = self.task_ids[row]

        connection = sqlite3.connect("takt.db")
        cursor = connection.cursor()

        task = cursor.execute(
            "SELECT description FROM tasks WHERE id = ?",
            (task_id,)
        ).fetchone()

        connection.close()

        if task and task[0]:
            self.descriptionBrowser.setPlainText(task[0])
        else:
            self.descriptionBrowser.setPlainText(
                "У этой задачи нет описания"
            )


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
            SELECT tasks.title, tasks.description, tasks.task_date,
                   tasks.duration, tasks.status, categories.name,
                   tasks.start_time
            FROM tasks
            LEFT JOIN categories
            ON tasks.category_id = categories.id
            WHERE tasks.id = ?
        """, (task_id,)).fetchone()

        connection.close()

        if task is None:
            return

        dialog = TaskDialog()
        dialog.setWindowTitle("Изменить задачу")

        dialog.titleEdit.setText(task[0])
        dialog.descriptionEdit.setPlainText(task[1] or "")
        dialog.taskDateEdit.setDate(
            QDate.fromString(task[2], "yyyy-MM-dd")
        )
        dialog.durationSpinBox.setValue(task[3])
        dialog.statusComboBox.setCurrentText(task[4])
        dialog.categoryComboBox.setCurrentText(task[5] or "Без категории")
        if task[6]:
            dialog.fixedTimeCheckBox.setChecked(True)
            dialog.taskTimeEdit.setTime(
                QTime.fromString(task[6], "HH:mm")
            )

        if dialog.exec() == QDialog.DialogCode.Accepted:
            title = dialog.titleEdit.text().strip()
            description = dialog.descriptionEdit.toPlainText()
            date = dialog.taskDateEdit.date().toString("yyyy-MM-dd")
            duration = dialog.durationSpinBox.value()
            status = dialog.statusComboBox.currentText()
            category = dialog.categoryComboBox.currentText()
            category_id = None
            start_time = None

            if dialog.fixedTimeCheckBox.isChecked():
                start_time = dialog.taskTimeEdit.time().toString("HH:mm")

            if not title:
                QMessageBox.warning(
                    self, "Ошибка", "Введите название задачи"
                )
                return

            connection = sqlite3.connect("takt.db")
            cursor = connection.cursor()
            if category != "Без категории":
                result = cursor.execute(
                    "SELECT id FROM categories WHERE name = ?",
                    (category,)
                ).fetchone()

                if result:
                    category_id = result[0]

            cursor.execute("""
                UPDATE tasks
                SET title = ?, description = ?, task_date = ?,
                    duration = ?, status = ?, category_id = ?,
                    start_time = ?
                WHERE id = ?
            """, (
                title, description, date, duration,
                status, category_id, start_time, task_id
            ))

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

    def plan_day(self):
        date = self.selectedDateEdit.date().toString("yyyy-MM-dd")
        day = self.selectedDateEdit.date().toPyDate()

        connection = sqlite3.connect("takt.db")
        cursor = connection.cursor()

        tasks = cursor.execute("""
            SELECT title, duration, start_time
            FROM tasks
            WHERE task_date = ? AND status != 'Готово'
            ORDER BY duration, id
        """, (date,)).fetchall()

        connection.close()

        if not tasks:
            self.scheduleBrowser.setPlainText(
                "На выбранный день нет невыполненных задач"
            )
            return

        fixed = []
        free = []

        for title, duration, start_time in tasks:
            if duration <= 0:
                QMessageBox.warning(
                    self, "Ошибка",
                    f"У задачи «{title}» некорректная длительность"
                )
                return

            if start_time:
                start = datetime.combine(
                    day,
                    datetime.strptime(start_time, "%H:%M").time()
                )
                end = start + timedelta(minutes=duration)
                fixed.append((start, end, title))
            else:
                free.append((title, duration))

        fixed.sort()

        for i in range(1, len(fixed)):
            if fixed[i][0] < fixed[i - 1][1]:
                QMessageBox.warning(
                    self,
                    "Ошибка расписания",
                    "Задачи с указанным временем пересекаются"
                )
                return

        schedule = fixed.copy()

        current = datetime.combine(day, time(9, 0))

        for title, duration in free:
            end = current + timedelta(minutes=duration)

            for start_fixed, end_fixed, name in fixed:
                if current < end_fixed and end > start_fixed:
                    current = end_fixed
                    end = current + timedelta(minutes=duration)

            schedule.append((current, end, title))
            current = end

        schedule.sort()

        lines = [
            "Расписание на день",
            self.selectedDateEdit.date().toString("dd.MM.yyyy"),
            "",
            f"{'Время':<30}Задача"
        ]

        for start, end, title in schedule:
            period = f"{start:%H:%M}–{end:%H:%M}"

            if start.date() != day or end.date() != day:
                period = (
                    f"{start:%d.%m %H:%M}–"
                    f"{end:%d.%m %H:%M}"
                )

            lines.append(f"{period:<30}{title}")

        self.scheduleBrowser.setPlainText("\n".join(lines))

    def export_schedule(self):
        text = self.scheduleBrowser.toPlainText()

        if not text.startswith("Расписание на день"):
            QMessageBox.warning(
                self,
                "Ошибка",
                "Сначала составьте расписание"
            )
            return

        file_name, ok = QFileDialog.getSaveFileName(
            self,
            "Сохранить расписание",
            "raspisanie.txt",
            "Текстовые файлы (*.txt)"
        )

        if not file_name:
            return

        if not file_name.lower().endswith(".txt"):
            file_name += ".txt"

        try:
            with open(file_name, "w", encoding="utf-8") as file:
                file.write(text)
        except OSError as error:
            QMessageBox.warning(
                self,
                "Ошибка",
                f"Не удалось сохранить файл:\n{error}"
            )
            return

        QMessageBox.information(
            self,
            "Готово",
            "Расписание успешно сохранено"
        )
