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
        self.renameCategoryButton.clicked.connect(self.rename_category)
        self.deleteCategoryButton.clicked.connect(self.delete_category)

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

    def rename_category(self):
        items = self.categoriesList.selectedItems()

        if not items:
            QMessageBox.warning(
                self, "Ошибка", "Сначала выберите категорию"
            )
            return

        old_name = items[0].text()

        new_name, ok = QInputDialog.getText(
            self,
            "Переименование категории",
            "Введите новое название:",
            text=old_name
        )

        if not ok:
            return

        new_name = new_name.strip()

        if not new_name:
            QMessageBox.warning(
                self, "Ошибка", "Название не может быть пустым"
            )
            return

        if new_name == old_name:
            return

        connection = sqlite3.connect("takt.db")
        cursor = connection.cursor()

        existing = cursor.execute(
            "SELECT id FROM categories WHERE name = ?",
            (new_name,)
        ).fetchone()

        if existing:
            QMessageBox.warning(
                self, "Ошибка", "Такая категория уже существует"
            )
            connection.close()
            return

        cursor.execute(
            "UPDATE categories SET name = ? WHERE name = ?",
            (new_name, old_name)
        )

        connection.commit()
        connection.close()

        self.load_categories()

    def delete_category(self):
        items = self.categoriesList.selectedItems()

        if not items:
            QMessageBox.warning(
                self, "Ошибка", "Сначала выберите категорию"
            )
            return

        name = items[0].text()

        answer = QMessageBox.question(
            self,
            "Удаление категории",
            f"Вы уверены, что хотите удалить категорию «{name}»?",
            QMessageBox.StandardButton.Yes |
            QMessageBox.StandardButton.No
        )

        if answer != QMessageBox.StandardButton.Yes:
            return

        connection = sqlite3.connect("takt.db")
        cursor = connection.cursor()

        category = cursor.execute(
            "SELECT id FROM categories WHERE name = ?",
            (name,)
        ).fetchone()

        if category is None:
            connection.close()
            return

        category_id = category[0]

        cursor.execute(
            "UPDATE tasks SET category_id = NULL WHERE category_id = ?",
            (category_id,)
        )

        cursor.execute(
            "DELETE FROM categories WHERE id = ?",
            (category_id,)
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
