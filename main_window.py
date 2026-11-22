import sqlite3

from PyQt6 import uic
from PyQt6.QtCore import QDate, Qt, QTime, QTimer, QSize, QSettings
from PyQt6.QtGui import QColor, QPixmap, QPainter, QIcon, QBrush, QTextCharFormat
from PyQt6.QtWidgets import (
    QMainWindow, QDialog, QTableWidgetItem,
    QHeaderView, QMessageBox,
    QListWidgetItem, QAbstractItemView, QInputDialog,
    QHBoxLayout, QVBoxLayout, QGroupBox, QListWidget,
    QColorDialog
)

from task_dialog import TaskDialog
from category_dialog import CategoryDialog
from schedule_dialog import ScheduleDialog
from success_dialog import SuccessDialog


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi("app/design_ui/main_window.ui", self)
        self.tabWidget.setCurrentWidget(self.todayTab)

        self.calendarWidget.selectionChanged.connect(self.load_calendar_tasks)
        self.calendar_dates = []

        self.settings = QSettings("Takt", "Takt")
        self.main_color = self.settings.value(
            "main_color", "#F6C5D6"
        )
        self.themeAction.triggered.connect(
            self.change_app_color
        )

        self.apply_app_color(self.main_color)

        self.tasksTable.horizontalHeader().setHighlightSections(False)
        self.tasksTable.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch)
        self.tasksTable.setWordWrap(True)

        self.selectedDateEdit.setDate(QDate.currentDate())
        self.selectedDateEdit.setDisplayFormat("dd.MM.yyyy")
        self.selectedDateEdit.dateChanged.connect(self.load_tasks)

        self.addTaskButton.clicked.connect(self.open_task_dialog)
        self.editTaskButton.clicked.connect(self.edit_task)
        self.deleteTaskButton.clicked.connect(self.delete_task)
        self.planDayButton.clicked.connect(self.open_schedule)
        self.categoriesAction.triggered.connect(self.open_categories)

        self.user_boards = {}
        self.kanban_loading = False

        self.customLayout = QHBoxLayout(self.customBoardScrollArea.widget())
        self.customLayout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.customBoardScrollArea.setWidgetResizable(True)

        self.boardComboBox.addItem("Основная доска")
        self.boardStack.setCurrentIndex(0)
        self.addColumnButton.setEnabled(False)
        self.addBoardTaskButton.setEnabled(False)

        self.addBoardButton.clicked.connect(self.add_board)
        self.addColumnButton.clicked.connect(self.add_column)
        self.addBoardTaskButton.clicked.connect(self.add_board_task)
        self.boardComboBox.currentTextChanged.connect(self.show_board)

        for lst in (self.todoList, self.progressList, self.doneList):
            lst.setDragEnabled(True)
            lst.setAcceptDrops(True)
            lst.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
            lst.setDefaultDropAction(Qt.DropAction.MoveAction)
            lst.setWordWrap(True)

        self.todoList.model().rowsInserted.connect(
            lambda: self.save_kanban_status(
                self.todoList, "Нужно сделать"))

        self.progressList.model().rowsInserted.connect(
            lambda: self.save_kanban_status(
                self.progressList, "В процессе"))

        self.doneList.model().rowsInserted.connect(
            lambda: self.save_kanban_status(
                self.doneList, "Готово"))

        self.load_tasks()
        self.load_calendar_tasks()
        self.tasksTable.itemChanged.connect(self.change_task_status)
        self.tasksTable.itemSelectionChanged.connect(self.show_description)

        self.tabWidget.currentChanged.connect(self.show_progress)
# открытие окна для создания задачи

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
                category_id, status, start_time))
            connection.commit()
            connection.close()

            print("Задача")
            self.load_tasks()
# изменение задачи

    def edit_task(self):
        row = self.tasksTable.currentRow()
        if row == -1:
            QMessageBox.warning(
                self, "Ошибка", "Выберите задачу для изменения")
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
        dialog.taskDateEdit.setDate(QDate.fromString(task[2], "yyyy-MM-dd"))
        dialog.durationSpinBox.setValue(task[3])
        dialog.statusComboBox.setCurrentText(task[4])
        dialog.categoryComboBox.setCurrentText(task[5] or "Без категории")
        if task[6]:
            dialog.fixedTimeCheckBox.setChecked(True)
            dialog.taskTimeEdit.setTime(QTime.fromString(task[6], "HH:mm"))

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
                QMessageBox.warning(self, "Ошибка", "Введите название задачи")
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
# выгрузка + заполнение таблицы

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
                task[2], "yyyy-MM-dd").toString("dd.MM.yyyy")

            if task[7]:
                date_text += f" {task[7]}"

            self.tasksTable.setItem(i, 2, QTableWidgetItem(date_text))
            self.tasksTable.setItem(i, 3, QTableWidgetItem(f"{task[3]} мин"))
            category = task[5] or "Без категории"
            self.tasksTable.setItem(i, 4, QTableWidgetItem(category))
            self.tasksTable.setItem(i, 5, QTableWidgetItem(task[4]))
            if task[6] and task[4] != "Готово":
                self.tasksTable.item(i, 4).setBackground(QColor(task[6]))
            if task[4] == "Готово":
                for col in range(6):
                    self.tasksTable.item(i, col).setBackground(
                        QColor("#D3D3D3"))

        self.tasksTable.resizeRowsToContents()
        self.tasksTable.blockSignals(False)

        total = len(tasks)
        done = 0
        for task in tasks:
            if task[4] == "Готово":
                done += 1
        if total > 0:
            percent = round(done / total * 100)
            self.tasksProgressBar.setValue(percent)
            self.tasksProgressBar.setFormat(
                f"Выполнено: {done} из {total} ({percent}%)")
        else:
            self.tasksProgressBar.setValue(0)
            self.tasksProgressBar.setFormat("Нет задач")

        if self.boardComboBox.currentText() == "Основная доска":
            self.load_kanban()
        self.load_calendar_tasks()
        self.mark_calendar_dates()
# удаление

    def delete_task(self):
        row = self.tasksTable.currentRow()
        if row == -1:
            QMessageBox.warning(self, "Ошибка", "Выберите задачу для удаления")
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
# флажок готовносссти задачи

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

        total = self.tasksTable.rowCount()
        done = 0

        for row in range(total):
            if self.tasksTable.item(row, 0).checkState() == Qt.CheckState.Checked:
                done += 1
        if total > 0 and done == total:
            dialog = SuccessDialog()
            dialog.exec()
# прогресс бар

    def show_progress(self, index):
        if index == self.tabWidget.indexOf(self.todayTab):
            self.progressLabel.show()
            self.tasksProgressBar.show()
        else:
            self.progressLabel.hide()
            self.tasksProgressBar.hide()
# виузал описания задачи

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
            self.descriptionBrowser.setMarkdown(task[0])
        else:
            self.descriptionBrowser.setPlainText("У этой задачи нет описания")
# заполнение канбан доски

    def load_kanban(self):
        self.kanban_loading = True
        self.todoList.clear()
        self.progressList.clear()
        self.doneList.clear()

        connection = sqlite3.connect("takt.db")
        cursor = connection.cursor()
        tasks = cursor.execute("""
            SELECT id, title, task_date, status
            FROM tasks
            ORDER BY task_date, id
        """).fetchall()
        connection.close()

        for task_id, title, date, status in tasks:
            date_text = QDate.fromString(
                date, "yyyy-MM-dd").toString("dd.MM.yyyy")
            item = QListWidgetItem(f"{title} ({date_text})")
            item.setData(Qt.ItemDataRole.UserRole, task_id)
            item.setSizeHint(QSize(0, 65))

            if status == "Нужно сделать":
                self.todoList.addItem(item)
            elif status == "В процессе":
                self.progressList.addItem(item)
            elif status == "Готово":
                self.doneList.addItem(item)

        self.kanban_loading = False
# ожидание сохранения

    def save_kanban_status(self, lst, status):
        if self.kanban_loading:
            return
        QTimer.singleShot(0, lambda: self.finish_kanban_drop(lst, status))
# сохранения изменения статуса в бд после канбан

    def finish_kanban_drop(self, lst, status):
        connection = sqlite3.connect("takt.db")
        cursor = connection.cursor()
        for row in range(lst.count()):
            item = lst.item(row)
            task_id = item.data(Qt.ItemDataRole.UserRole)
            if task_id is not None:
                cursor.execute(
                    "UPDATE tasks SET status = ? WHERE id = ?",
                    (status, task_id))
        connection.commit()
        connection.close()
        self.load_tasks()
# добавление доски

    def add_board(self):
        name, ok = QInputDialog.getText(
            self,
            "Новая доска",
            "Введите название доски:")
        if not ok:
            return

        name = name.strip()
        if not name:
            QMessageBox.warning(
                self, "Ошибка", "Введите название доски")
            return

        self.user_boards[name] = {}
        self.boardComboBox.addItem(name)
        self.boardComboBox.setCurrentText(name)
# визуал досок

    def show_board(self, name):
        if name == "Основная доска":
            self.boardStack.setCurrentIndex(0)
            self.addColumnButton.setEnabled(False)
            self.addBoardTaskButton.setEnabled(False)
            self.load_kanban()
        else:
            self.boardStack.setCurrentIndex(1)
            self.addColumnButton.setEnabled(True)
            self.addBoardTaskButton.setEnabled(True)
            self.load_custom_board(name)
# визуал новой доски

    def load_custom_board(self, name):
        while self.customLayout.count():
            item = self.customLayout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.custom_lists = {}

        connection = sqlite3.connect("takt.db")
        cursor = connection.cursor()
        tasks = cursor.execute("""
            SELECT id, title, task_date
            FROM tasks
        """).fetchall()
        connection.close()

        task_data = {}
        for task_id, title, date in tasks:
            task_data[task_id] = (title, date)

        for column, task_ids in self.user_boards[name].items():
            group = QGroupBox(column)
            group.setStyleSheet("""
                QGroupBox {
                    background-color: #FFFFFF;
                    border: 1px solid #F2B2C9;
                    border-radius: 12px;
                    margin-top: 18px;
                    padding: 10px;
                    font-size: 14px;
                    font-weight: bold;
                    color: #30232A;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    subcontrol-position: top center;
                    background-color: #F6C5D6;
                    padding: 5px 15px;
                    border-radius: 7px;
                }
            """.replace("#F6C5D6", self.main_color)
                .replace("#F2B2C9", self.main_color))
            group.setMinimumWidth(200)
            group.setMaximumWidth(240)
            layout = QVBoxLayout(group)
            lst = QListWidget()
            lst.setStyleSheet("""
                QListWidget {
                    background-color: #FFFFFF;
                    border: 1px solid #F5D3DF;
                    border-radius: 10px;
                }
                QListWidget::item {
                    background-color: #FFF0F5;
                    color: #30232A;
                    border: 1px solid #F2B2C9;
                    border-radius: 7px;
                    padding: 8px;
                    margin: 4px;
                }
                QListWidget::item:selected {
                    background-color: #E8A5BA;
                }
            """.replace("#F5D3DF", self.main_color)
               .replace("#F2B2C9", self.main_color)
               .replace("#E8A5BA", self.main_color)
               .replace(
                   "#FFF0F5",
                   QColor(self.main_color).lighter(155).name()
            ))

            lst.setWordWrap(True)
            lst.setDragEnabled(True)
            lst.setAcceptDrops(True)
            lst.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
            lst.setDefaultDropAction(Qt.DropAction.MoveAction)

            for task_id in task_ids:
                if task_id in task_data:
                    title, date = task_data[task_id]
                    date_text = QDate.fromString(
                        date, "yyyy-MM-dd").toString("dd.MM.yyyy")
                    item = QListWidgetItem(f"{title}\n{date_text}")
                    item.setSizeHint(QSize(0, 65))
                    item.setData(Qt.ItemDataRole.UserRole, task_id)
                    lst.addItem(item)

            self.custom_lists[column] = lst
            lst.model().rowsInserted.connect(
                lambda parent, first, last,
                board=name, col=column, target=lst:
                self.custom_drop(board, col, target, first))
            layout.addWidget(lst)
            self.customLayout.addWidget(group)
# ожидание сохранения

    def custom_drop(self, board, column, lst, row):
        QTimer.singleShot(0, lambda: self.finish_custom_drop(
            board, column, lst, row))
# добавление задач между колонками

    def finish_custom_drop(self, board, column, lst, row):
        if self.boardComboBox.currentText() != board:
            return
        if self.custom_lists.get(column) is not lst:
            return
        item = lst.item(row)
        if item is None:
            return
        task_id = item.data(Qt.ItemDataRole.UserRole)
        if task_id is None:
            return

        found = False
        for task_ids in self.user_boards[board].values():
            if task_id in task_ids:
                found = True
        if not found:
            self.load_custom_board(board)
            return

        for task_ids in self.user_boards[board].values():
            if task_id in task_ids:
                task_ids.remove(task_id)
        self.user_boards[board][column].append(task_id)

# добавление колонок

    def add_column(self):
        board = self.boardComboBox.currentText()
        if board == "Основная доска":
            return

        name, ok = QInputDialog.getText(
            self,
            "Новая колонка",
            "Введите название колонки:")
        if not ok:
            return

        name = name.strip()
        if not name:
            QMessageBox.warning(
                self, "Ошибка", "Введите название колонки")
            return
        if name in self.user_boards[board]:
            QMessageBox.warning(
                self, "Ошибка", "Такая колонка уже существует")
            return

        self.user_boards[board][name] = []
        self.load_custom_board(board)
# добавление задач в колонку

    def add_board_task(self):
        board = self.boardComboBox.currentText()
        if board == "Основная доска":
            return

        connection = sqlite3.connect("takt.db")
        cursor = connection.cursor()
        tasks = cursor.execute("""
            SELECT id, title
            FROM tasks
            ORDER BY id
        """).fetchall()
        connection.close()

        used = []
        for column in self.user_boards[board].values():
            for task_id in column:
                used.append(task_id)
        available = []

        for task in tasks:
            if task[0] not in used:
                available.append(task)
        if not available:
            QMessageBox.warning(
                self, "Ошибка", "Нет доступных задач")
            return

        names = []
        for task_id, title in available:
            names.append(title)
        name, ok = QInputDialog.getItem(
            self, "Добавление задачи",
            "Выберите задачу:",
            names,
            0,
            False)
        if not ok:
            return

        i = names.index(name)
        task_id = available[i][0]
        column, ok = QInputDialog.getItem(
            self,
            "Выбор колонки",
            "В какую колонку добавить задачу?",
            list(self.user_boards[board]),
            0,
            False)

        if not ok:
            return
        self.user_boards[board][column].append(task_id)
        self.load_custom_board(board)

    def open_categories(self):
        dialog = CategoryDialog()
        dialog.exec()
        self.load_tasks()

    def open_schedule(self):
        date = QDate.currentDate()
        dialog = ScheduleDialog(date)
        dialog.exec()

    def load_calendar_tasks(self):
        date = self.calendarWidget.selectedDate().toString("yyyy-MM-dd")

        con = sqlite3.connect("takt.db")
        cur = con.cursor()

        tasks = cur.execute("""
            SELECT tasks.title, tasks.start_time,
                   tasks.status, categories.color
            FROM tasks
            LEFT JOIN categories
                ON tasks.category_id = categories.id
            WHERE tasks.task_date = ?
            ORDER BY tasks.start_time IS NULL,
                     tasks.start_time, tasks.id
        """, (date,)).fetchall()

        con.close()

        self.calendarTasksList.clear()

        if not tasks:
            self.calendarTasksList.addItem("На этот день задач нет")
            return

        for title, start_time, status, color in tasks:
            if start_time:
                text = f"{start_time} — {title}"
            else:
                text = f"Без времени — {title}"

            if status == "Готово":
                text += " (готово)"
            elif status == "В процессе":
                text += " (в процессе)"

            item = QListWidgetItem(text)

            if not color or not QColor(color).isValid():
                color = "#CCCCCC"

            picture = QPixmap(16, 16)
            picture.fill(Qt.GlobalColor.transparent)

            painter = QPainter(picture)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(color))
            painter.drawEllipse(2, 2, 12, 12)

            painter.end()

            item.setIcon(QIcon(picture))

            self.calendarTasksList.addItem(item)

    def mark_calendar_dates(self):

        for date in self.calendar_dates:
            day = QDate.fromString(date, "yyyy-MM-dd")
            self.calendarWidget.setDateTextFormat(
                day, QTextCharFormat()
            )

        self.calendar_dates = []

        con = sqlite3.connect("takt.db")
        cur = con.cursor()

        dates = cur.execute("""
            SELECT DISTINCT task_date
            FROM tasks
        """).fetchall()

        con.close()

        fmt = QTextCharFormat()
        fmt.setBackground(QBrush(QColor(self.main_color)))
        fmt.setForeground(QBrush(QColor("#30232A")))

        for row in dates:
            date = row[0]
            day = QDate.fromString(date, "yyyy-MM-dd")

            if day.isValid():
                self.calendarWidget.setDateTextFormat(day, fmt)
                self.calendar_dates.append(date)

    def change_app_color(self):
        color = QColorDialog.getColor(
            QColor(self.main_color),
            self,
            "Выберите цвет Takt"
        )
        if not color.isValid():
            return
        self.main_color = color.name()
        self.settings.setValue(
            "main_color", self.main_color
        )
        self.apply_app_color(self.main_color)

        board = self.boardComboBox.currentText()
        if board in self.user_boards:
            self.load_custom_board(board)

    def apply_app_color(self, color):
        main = QColor(color)

        if not main.isValid():
            main = QColor("#F6C5D6")

        hover = main.darker(110).name()
        light = main.lighter(155).name()
        color = main.name()

        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {light};
            }}
    
            QPushButton {{
                background-color: {color};
                color: #30232A;
                border: 1px solid {hover};
                border-radius: 10px;
                padding: 8px;
            }}
    
            QPushButton:hover {{
                background-color: {hover};
            }}
    
            QTabWidget::pane {{
                border: 1px solid {color};
            }}
    
            QTabBar::tab:selected {{
                background-color: {color};
            }}
    
            QProgressBar::chunk {{
                background-color: {color};
            }}
        """)

        buttons = [
            self.addTaskButton,
            self.editTaskButton,
            self.deleteTaskButton,
            self.planDayButton,
            self.addBoardButton,
            self.addColumnButton,
            self.addBoardTaskButton
        ]

        for button in buttons:
            button.setStyleSheet(f"""
                QPushButton {{
                    background-color: {color};
                    color: #30232A;
                    border: 1px solid {hover};
                    border-radius: 10px;
                    padding: 8px;
                }}
    
                QPushButton:hover {{
                    background-color: {hover};
                }}
    
                QPushButton:disabled {{
                    background-color: #EEEEEE;
                    color: #999999;
                    border: 1px solid #DDDDDD;
                }}
            """)

        self.tabWidget.setStyleSheet(f"""
            QTabBar::tab {{
                background-color: {light};
                color: #30232A;
                padding: 8px 16px;
                border-radius: 8px;
                margin: 2px;
            }}
    
            QTabBar::tab:selected {{
                background-color: {color};
            }}
        """)

        self.selectedDateEdit.setStyleSheet(f"""
            QDateEdit {{
                background-color: white;
                border: 2px solid {color};
                border-radius: 5px;
                padding: 3px;
            }}
        """)

        self.boardComboBox.setStyleSheet(f"""
            QComboBox {{
                background-color: white;
                border: 2px solid {color};
                border-radius: 5px;
                padding: 3px;
            }}
        """)

        self.tasksProgressBar.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid {color};
                border-radius: 6px;
                text-align: center;
            }}
    
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 5px;
            }}
        """)

        self.calendarWidget.setStyleSheet(f"""
            QCalendarWidget QWidget#qt_calendar_navigationbar {{
                background-color: {color};
            }}
    
            QCalendarWidget QToolButton {{
                background-color: {color};
                color: #30232A;
                border: none;
                padding: 5px;
            }}
    
            QCalendarWidget QAbstractItemView:enabled {{
                selection-background-color: {color};
                selection-color: #30232A;
            }}
        """)

        if hasattr(self, "calendar_dates"):
            self.mark_calendar_dates()

        groups = [
            self.todoGroupBox,
            self.progressGroupBox,
            self.doneGroupBox
        ]

        for group in groups:
            group.setStyleSheet(f"""
                QGroupBox {{
                    background-color: white;
                    border: 1px solid {hover};
                    border-radius: 12px;
                    margin-top: 18px;
                    padding: 10px;
                    color: #30232A;
                }}
    
                QGroupBox::title {{
                    subcontrol-origin: margin;
                    subcontrol-position: top center;
                    background-color: {color};
                    padding: 5px 15px;
                    border-radius: 7px;
                }}
            """)

        lists = [
            self.todoList,
            self.progressList,
            self.doneList
        ]

        for lst in lists:
            lst.setStyleSheet(f"""
                QListWidget {{
                    background-color: white;
                    border: 1px solid {hover};
                    border-radius: 10px;
                }}
    
                QListWidget::item {{
                    background-color: {light};
                    color: #30232A;
                    border: 1px solid {color};
                    border-radius: 7px;
                    padding: 8px;
                    margin: 4px;
                }}
    
                QListWidget::item:selected {{
                    background-color: {color};
                }}
            """)
