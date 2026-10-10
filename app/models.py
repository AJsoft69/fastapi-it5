import sqlite3
from datetime import datetime
from typing import ClassVar

from fastapi import HTTPException
from pydantic import BaseModel, Field


# ---------------------------------------------------------------- Category
class CategoryInput(BaseModel):
    name: str = Field(min_length=1)


class Category(CategoryInput):
    id: int

    @classmethod
    def create_category(cls, category_input: CategoryInput, database_connection):
        try:
            with database_connection() as connection:
                cursor = connection.execute(
                    "INSERT INTO categories (name) VALUES (?)",
                    (category_input.name,),
                )
                return cls(id=cursor.lastrowid, name=category_input.name)
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=409, detail="Category name already exists")

    @classmethod
    def list_categories(cls, database_connection):
        with database_connection() as connection:
            rows = connection.execute("SELECT id, name FROM categories").fetchall()
        return [cls(**dict(row)) for row in rows]


# ----------------------------------------------------------------- Product
class ProductInput(BaseModel):
    name: str = Field(min_length=1)
    price: float = Field(ge=0)
    stock: int = Field(default=0, ge=0)
    reorder_level: int = Field(default=10, ge=0)
    category_id: int


class Product(ProductInput):
    id: int

    COLUMNS: ClassVar[str] = "id, name, price, stock, reorder_level, category_id"

    @classmethod
    def create_product(cls, product_input: ProductInput, database_connection):
        try:
            with database_connection() as connection:
                cursor = connection.execute(
                    "INSERT INTO products (name, price, stock, reorder_level, category_id) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (product_input.name, product_input.price, product_input.stock,
                     product_input.reorder_level, product_input.category_id),
                )
                return cls(id=cursor.lastrowid, **product_input.model_dump())
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=400, detail="Category does not exist")

    @classmethod
    def list_products(cls, database_connection, search: str = ""):
        with database_connection() as connection:
            rows = connection.execute(
                f"SELECT {cls.COLUMNS} FROM products WHERE name LIKE ? ORDER BY id",
                (f"%{search}%",),
            ).fetchall()
        return [cls(**dict(row)) for row in rows]

    @classmethod
    def get_product(cls, product_id: int, database_connection):
        with database_connection() as connection:
            row = connection.execute(
                f"SELECT {cls.COLUMNS} FROM products WHERE id = ?", (product_id,)
            ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Product not found")
        return cls(**dict(row))

    @classmethod
    def update_product(cls, product_id: int, product_input: ProductInput, database_connection):
        try:
            with database_connection() as connection:
                cursor = connection.execute(
                    "UPDATE products SET name = ?, price = ?, stock = ?, "
                    "reorder_level = ?, category_id = ? WHERE id = ?",
                    (product_input.name, product_input.price, product_input.stock,
                     product_input.reorder_level, product_input.category_id, product_id),
                )
                if cursor.rowcount == 0:
                    raise HTTPException(status_code=404, detail="Product not found")
                return cls(id=product_id, **product_input.model_dump())
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=400, detail="Category does not exist")

    @classmethod
    def delete_product(cls, product_id: int, database_connection):
        try:
            with database_connection() as connection:
                cursor = connection.execute("DELETE FROM products WHERE id = ?", (product_id,))
                if cursor.rowcount == 0:
                    raise HTTPException(status_code=404, detail="Product not found")
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=409, detail="Product is used in a sale and cannot be deleted")

    @classmethod
    def list_low_stock(cls, database_connection):
        with database_connection() as connection:
            rows = connection.execute(
                f"SELECT {cls.COLUMNS} FROM products WHERE stock <= reorder_level ORDER BY stock"
            ).fetchall()
        return [cls(**dict(row)) for row in rows]


# -------------------------------------------------------------------- Sale
class SaleLine(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)


class SaleInput(BaseModel):
    items: list[SaleLine] = Field(min_length=1)


class SaleItem(BaseModel):
    product_id: int
    quantity: int
    unit_price: float


class Sale(BaseModel):
    id: int
    sale_date: str
    total: float
    items: list[SaleItem]

    @classmethod
    def create_sale(cls, sale_input: SaleInput, database_connection):
        """TRANSACTION: check stock -> reduce stock -> save sale and its items.
        If any step fails, database_connection() rolls everything back."""
        with database_connection() as connection:
            total = 0.0
            lines = []
            for line in sale_input.items:
                row = connection.execute(
                    "SELECT name, price, stock FROM products WHERE id = ?", (line.product_id,)
                ).fetchone()
                if row is None:
                    raise HTTPException(status_code=404, detail=f"Product {line.product_id} not found")
                if row["stock"] < line.quantity:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Not enough stock for {row['name']} (available: {row['stock']})",
                    )
                connection.execute(
                    "UPDATE products SET stock = stock - ? WHERE id = ?",
                    (line.quantity, line.product_id),
                )
                total += row["price"] * line.quantity
                lines.append(SaleItem(product_id=line.product_id, quantity=line.quantity,
                                      unit_price=row["price"]))

            sale_date = datetime.now().isoformat(timespec="seconds")
            cursor = connection.execute(
                "INSERT INTO sales (sale_date, total) VALUES (?, ?)", (sale_date, total)
            )
            sale_id = cursor.lastrowid
            for item in lines:
                connection.execute(
                    "INSERT INTO sale_items (sale_id, product_id, quantity, unit_price) "
                    "VALUES (?, ?, ?, ?)",
                    (sale_id, item.product_id, item.quantity, item.unit_price),
                )
            return cls(id=sale_id, sale_date=sale_date, total=total, items=lines)

    @classmethod
    def _load(cls, connection, sale_row):
        item_rows = connection.execute(
            "SELECT product_id, quantity, unit_price FROM sale_items WHERE sale_id = ?",
            (sale_row["id"],),
        ).fetchall()
        return cls(**dict(sale_row), items=[SaleItem(**dict(r)) for r in item_rows])

    @classmethod
    def list_sales(cls, database_connection):
        with database_connection() as connection:
            rows = connection.execute("SELECT id, sale_date, total FROM sales ORDER BY id DESC").fetchall()
            return [cls._load(connection, row) for row in rows]

    @classmethod
    def get_sale(cls, sale_id: int, database_connection):
        with database_connection() as connection:
            row = connection.execute(
                "SELECT id, sale_date, total FROM sales WHERE id = ?", (sale_id,)
            ).fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="Sale not found")
            return cls._load(connection, row)
