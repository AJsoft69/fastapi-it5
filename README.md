Store Inventory & Sales System
A FastAPI + SQLite backend that helps a small store track its products, record sales, and see which items are running low.
Problem: small stores that track stock in notebooks or spreadsheets sell items that are already out of stock and forget to reorder.
Solution: every sale automatically deducts stock, and a report lists products at or below their reorder level.
Intended users: cashiers (record sales), inventory staff (manage products), store owner (monitor stock).
Run it on Windows
```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn main:app --reload
```
Then open http://127.0.0.1:8000/docs to try the API. The database file `store.db` is created automatically on the first run.
Database (SQLite)
Table	Purpose	Key relationships
`categories`	Product categories (unique name)	-
`products`	Items for sale: name, price, stock, reorder level	`category_id` -> `categories.id`
`sales`	One row per sale: date and total	-
`sale_items`	Products inside a sale: quantity and price at time of sale	`sale_id` -> `sales.id`, `product_id` -> `products.id`
Foreign keys are enforced, and CHECK constraints prevent negative prices, negative stock, and zero quantities.
Project structure
`main.py` creates the FastAPI app and defines the routes.
`app/database.py` opens SQLite connections (commit on success, rollback on error) and creates the tables.
`app/models.py` holds the Pydantic model classes (`Category`, `Product`, `Sale`). Each class has its own database methods, so the routes only call them.
Transaction: making a sale
`POST /sale` runs as one database transaction. For each item it checks the stock, deducts it, and then saves the sale and its items with the total. If any item is missing or out of stock, everything is rolled back and nothing is saved.
Endpoints
Endpoint	Parameters	Purpose
`GET /`	None	Welcome message
`POST /category`	`category: CategoryInput`	Create a category
`GET /categories`	None	List categories
`POST /product`	`product: ProductInput`	Create a product
`GET /products`	`search` (optional)	List or search products by name
`GET /products/{product_id}`	`product_id: int`	Get one product
`PUT /product/{product_id}`	`product_id`, `product: ProductInput`	Update a product
`DELETE /product/{product_id}`	`product_id: int`	Delete a product (blocked if used in a sale)
`POST /sale`	`sale: SaleInput`	Record a sale and deduct stock
`GET /sales`	None	List sales with their items
`GET /sales/{sale_id}`	`sale_id: int`	Get one sale
`GET /reports/low-stock`	None	Products at or below their reorder level
Example sale request
```json
POST /sale
{ "items": [ { "product_id": 1, "quantity": 2 } ] }
```
