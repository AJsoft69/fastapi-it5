from fastapi import FastAPI

from app.database import create_tables, database_connection
from app.models import (
    Category, CategoryInput,
    Product, ProductInput,
    Sale, SaleInput,
)

app = FastAPI(title="Store Inventory & Sales System")
create_tables()


@app.get("/")
def home():
    return {"message": "Store Inventory & Sales System. Open /docs to try the API."}


# ---------------- Categories ----------------
@app.post("/category")
def create_category(category: CategoryInput):
    return {"category": Category.create_category(category, database_connection)}


@app.get("/categories")
def get_categories():
    return {"categories": Category.list_categories(database_connection)}


# ---------------- Products (full CRUD) ----------------
@app.post("/product")
def create_product(product: ProductInput):
    return {"product": Product.create_product(product, database_connection)}


@app.get("/products")
def get_products(search: str = ""):
    return {"products": Product.list_products(database_connection, search)}


@app.get("/products/{product_id}")
def get_product(product_id: int):
    return {"product": Product.get_product(product_id, database_connection)}


@app.put("/product/{product_id}")
def update_product(product_id: int, product: ProductInput):
    return {"product": Product.update_product(product_id, product, database_connection)}


@app.delete("/product/{product_id}")
def delete_product(product_id: int):
    Product.delete_product(product_id, database_connection)
    return {"message": "Product deleted"}


# ---------------- Sales (transaction) ----------------
@app.post("/sale")
def create_sale(sale: SaleInput):
    return {"sale": Sale.create_sale(sale, database_connection)}


@app.get("/sales")
def get_sales():
    return {"sales": Sale.list_sales(database_connection)}


@app.get("/sales/{sale_id}")
def get_sale(sale_id: int):
    return {"sale": Sale.get_sale(sale_id, database_connection)}


# ---------------- Report ----------------
@app.get("/reports/low-stock")
def low_stock():
    return {"products": Product.list_low_stock(database_connection)}
