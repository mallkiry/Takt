import sys
import sqlite3
import os
import shutil

if getattr(sys, "frozen", False):
    folder = os.path.expanduser(
        "~/Library/Application Support/Takt"
    )
    os.makedirs(folder, exist_ok=True)

    shutil.copytree(
        os.path.join(sys._MEIPASS, "app"),
        os.path.join(folder, "app"),
        dirs_exist_ok=True
    )

    db = os.path.join(folder, "takt.db")
    if not os.path.exists(db):
        shutil.copy2(
            os.path.join(sys._MEIPASS, "takt.db"),
            db
        )

    os.chdir(folder)


from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from main_window import MainWindow


app = QApplication(sys.argv)
window = MainWindow()


def show_today():
    window.tabWidget.setCurrentWidget(window.todayTab)
    window.showMaximized()


def add_task():
    show_today()
    window.open_task_dialog()


def load_today_tasks():
    today_menu.clear()

    date = QDate.currentDate().toString("yyyy-MM-dd")

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

    done = 0

    for title, start_time, status, color in tasks:
        if status == "Готово":
            done += 1

    header = today_menu.addAction(
        f"Сегодня: {len(tasks)} задач | Готово: {done}"
    )
    header.setEnabled(False)

    if not tasks:
        empty = today_menu.addAction("На сегодня задач нет")
        empty.setEnabled(False)
        return

    for title, start_time, status, color in tasks:
        if start_time:
            time = start_time
        else:
            time = "Без времени"
        text = f"{time}  |  {title}"
        if status == "Готово":
            text += " (готово)"
        action = today_menu.addAction(text)

        if not color or not QColor(color).isValid():
            color = "#CCCCCC"

        picture = QPixmap(15, 15)
        picture.fill(Qt.GlobalColor.transparent)

        painter = QPainter(picture)
        painter.setRenderHint(
            QPainter.RenderHint.Antialiasing
        )

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(color))
        painter.drawEllipse(1, 1, 13, 13)

        painter.end()
        action.setIcon(QIcon(picture))

    percent = int(done / len(tasks) * 100)

    progress = today_menu.addAction(
        f"Выполнено: {percent}%"
    )
    progress.setEnabled(False)


if QSystemTrayIcon.isSystemTrayAvailable():
    app.setQuitOnLastWindowClosed(False)

    picture = QPixmap(32, 32)
    picture.fill(Qt.GlobalColor.transparent)

    painter = QPainter(picture)
    painter.setRenderHint(
        QPainter.RenderHint.Antialiasing
    )

    painter.setBrush(QColor("#F6C5D6"))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(1, 1, 30, 30)

    painter.setPen(QColor("#30232A"))

    font = QFont()
    font.setPointSize(17)
    font.setBold(True)

    painter.setFont(font)
    painter.drawText(
        picture.rect(),
        Qt.AlignmentFlag.AlignCenter,
        "T"
    )
    painter.end()

    tray = QSystemTrayIcon(QIcon(picture), window)
    tray.setToolTip("Takt — планировщик задач")

    # меню
    menu = QMenu(window)
    menu.setStyleSheet("""
        QMenu {
            background-color: #FFF7FA;
            color: #30232A;
            border: 1px solid #F2B2C9;
            border-radius: 8px;
            padding: 6px;
        }

        QMenu::item {
            padding: 8px 20px;
            margin: 2px;
            border-radius: 6px;
        }

        QMenu::item:selected {
            background-color: #F6C5D6;
            color: #30232A;
        }

        QMenu::separator {
            height: 1px;
            background-color: #F2B2C9;
            margin: 5px 10px;
        }
    """)

    # пункты меню
    open_action = menu.addAction("Открыть Takt")
    today_menu = menu.addMenu("Мой день")
    add_action = menu.addAction("Добавить задачу")
    exit_action = menu.addAction("Выйти")

    open_action.triggered.connect(window.showMaximized)
    today_menu.aboutToShow.connect(load_today_tasks)
    add_action.triggered.connect(add_task)
    exit_action.triggered.connect(app.quit)
    tray.setContextMenu(menu)
    tray.show()

window.tabWidget.setCurrentWidget(window.todayTab)
window.showMaximized()

sys.exit(app.exec())
