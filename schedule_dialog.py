import sqlite3
from datetime import datetime, timedelta, time

from PyQt6 import uic
from PyQt6.QtWidgets import QDialog, QMessageBox, QFileDialog


class ScheduleDialog(QDialog):
    def __init__(self, date):
        super().__init__()
        uic.loadUi("app/design_ui/schedule_dialog.ui", self)

        self.date = date
        self.scheduleDateLabel.setText(date.toString("dd.MM.yyyy"))

        self.planDayButton.clicked.connect(self.plan_day)
        self.exportScheduleButton.clicked.connect(self.export_schedule)

    def plan_day(self):
        date = self.date.toString("yyyy-MM-dd")
        day = self.date.toPyDate()

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
                "На выбранный день нет невыполненных задач")
            return

        fixed = []
        free = []

        for title, duration, start_time in tasks:
            if duration <= 0:
                QMessageBox.warning(
                    self, "Ошибка",
                    f"У задачи «{title}» некорректная длительность")
                return

            if start_time:
                start = datetime.strptime(
                    date + " " + start_time, "%Y-%m-%d %H:%M")
                end = start + timedelta(minutes=duration)
                fixed.append((start, end, title))
            else:
                free.append((title, duration))
        fixed.sort()
        schedule = fixed.copy()
        if day == datetime.now().date():
            current = datetime.now()
        else:
            current = datetime.strptime(date + " 00:00", "%Y-%m-%d %H:%M")

        for title, duration in free:
            end = current + timedelta(minutes=duration)
            for task in fixed:
                start_fixed = task[0]
                end_fixed = task[1]
                if current < end_fixed and end > start_fixed:
                    current = end_fixed
                    end = current + timedelta(minutes=duration)

            schedule.append((current, end, title))
            current = end
        schedule.sort()

        lines = [
            "Расписание на день",
            self.date.toString("dd.MM.yyyy"),
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

        if not text.strip():
            QMessageBox.warning(
                self, "Ошибка", "Сначала составьте расписание"
            )
            return

        path, ok = QFileDialog.getSaveFileName(
            self,
            "Сохранить расписание",
            "raspisanie.txt",
            "Текстовые файлы (*.txt)"
        )

        if not path:
            return

        try:
            with open(path, "w", encoding="utf-8") as file:
                file.write(text)
        except OSError as error:
            QMessageBox.warning(
                self, "Ошибка сохранения", str(error)
            )
            return

        QMessageBox.information(
            self, "Готово", "Расписание успешно сохранено"
        )
