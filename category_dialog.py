import sqlite3

from PyQt6 import uic
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QDialog, QMessageBox, QInputDialog,
    QColorDialog, QListWidgetItem
)


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
