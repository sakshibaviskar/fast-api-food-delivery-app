from fastapi import FastAPI, Query, HTTPException, Response, status
from pydantic import BaseModel, Field
from typing import Optional

app = FastAPI()

# Q1 — HOME
@app.get("/")
def home():
    return {"message": "Welcome to QuickBite Food Delivery"}

# Q2 — MENU
menu = [
    {"id": 1, "name": "Margherita Pizza", "price": 299, "category": "Pizza", "is_available": True},
    {"id": 2, "name": "Veg Burger", "price": 149, "category": "Burger", "is_available": True},
    {"id": 3, "name": "Coke", "price": 59, "category": "Drink", "is_available": True},
    {"id": 4, "name": "Chocolate Cake", "price": 199, "category": "Dessert", "is_available": False},
    {"id": 5, "name": "Paneer Pizza", "price": 349, "category": "Pizza", "is_available": True},
    {"id": 6, "name": "Fries", "price": 99, "category": "Burger", "is_available": True},
]

orders = []
order_counter = 1
cart = []

# HELPERS (Q7)
def find_menu_item(item_id):
    for item in menu:
        if item["id"] == item_id:
            return item
    return None


def calculate_bill(price, quantity, order_type="delivery"):
    total = price * quantity
    if order_type == "delivery":
        total += 30
    return total


def filter_menu_logic(category, max_price, is_available):
    result = menu

    if category is not None:
        result = [i for i in result if i["category"] == category]

    if max_price is not None:
        result = [i for i in result if i["price"] <= max_price]

    if is_available is not None:
        result = [i for i in result if i["is_available"] == is_available]

    return result


# Q5 — SUMMARY (IMPORTANT ABOVE ID)
@app.get("/menu/summary")
def summary():
    available = [i for i in menu if i["is_available"]]
    categories = list(set(i["category"] for i in menu))

    return {
        "total": len(menu),
        "available": len(available),
        "unavailable": len(menu) - len(available),
        "categories": categories
    }


# Q2 GET MENU
@app.get("/menu")
def get_menu():
    return {"menu": menu, "total": len(menu)}



# Q4 GET ORDERS
@app.get("/orders")
def get_orders():
    return {"orders": orders, "total_orders": len(orders)}


# Q6 + Q9 — PYDANTIC
class OrderRequest(BaseModel):
    customer_name: str = Field(..., min_length=2)
    item_id: int = Field(..., gt=0)
    quantity: int = Field(..., gt=0, le=20)
    delivery_address: str = Field(..., min_length=10)
    order_type: str = "delivery"


# Q8 POST ORDER
@app.post("/orders")
def place_order(data: OrderRequest):
    global order_counter

    item = find_menu_item(data.item_id)

    if not item:
        return {"error": "Item not found"}

    if not item["is_available"]:
        return {"error": "Item not available"}

    total = calculate_bill(item["price"], data.quantity, data.order_type)

    order = {
        "order_id": order_counter,
        "customer": data.customer_name,
        "item": item["name"],
        "quantity": data.quantity,
        "total_price": total
    }

    orders.append(order)
    order_counter += 1

    return {"message": "Order placed", "order": order}


# Q10 FILTER
@app.get("/menu/filter")
def filter_menu(
    category: Optional[str] = None,
    max_price: Optional[int] = None,
    is_available: Optional[bool] = None
):
    result = filter_menu_logic(category, max_price, is_available)
    return {"items": result, "count": len(result)}


# Q11 CREATE MENU ITEM
class NewItem(BaseModel):
    name: str = Field(..., min_length=2)
    price: int = Field(..., gt=0)
    category: str
    is_available: bool = True


@app.post("/menu", status_code=201)
def add_item(data: NewItem, response: Response):
    for i in menu:
        if i["name"].lower() == data.name.lower():
            response.status_code = 400
            return {"error": "Duplicate item"}

    new_id = max(i["id"] for i in menu) + 1

    item = {
        "id": new_id,
        **data.dict()
    }

    menu.append(item)
    return item


# Q12 UPDATE
@app.put("/menu/{item_id}")
def update_item(
    item_id: int,
    price: Optional[int] = None,
    is_available: Optional[bool] = None
):
    item = find_menu_item(item_id)

    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    if price is not None:
        item["price"] = price

    if is_available is not None:
        item["is_available"] = is_available

    return item


# Q13 DELETE
@app.delete("/menu/{item_id}")
def delete_item(item_id: int):
    item = find_menu_item(item_id)

    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    menu.remove(item)
    return {"message": f"{item['name']} deleted"}


# Q14 CART
@app.post("/cart/add")
def add_to_cart(item_id: int, quantity: int = 1):

    item = find_menu_item(item_id)

    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    if not item["is_available"]:
        raise HTTPException(status_code=400, detail="Item not available")

    for c in cart:
        if c["item_id"] == item_id:
            c["quantity"] += quantity
            c["subtotal"] = item["price"] * c["quantity"]
            return {"message": "Cart updated", "item": c}

    subtotal = item["price"] * quantity

    cart_item = {
        "item_id": item_id,
        "name": item["name"],
        "quantity": quantity,
        "subtotal": subtotal
    }

    cart.append(cart_item)

    return {"message": "Added to cart", "item": cart_item}


@app.get("/cart")
def view_cart():
    total = sum(i["subtotal"] for i in cart)
    return {"cart": cart, "grand_total": total}


# Q15 CHECKOUT
class CheckoutRequest(BaseModel):
    customer_name: str
    delivery_address: str


@app.delete("/cart/{item_id}")
def remove_cart(item_id: int):
    for c in cart:
        if c["item_id"] == item_id:
            cart.remove(c)
            return {"message": "Removed"}
    raise HTTPException(status_code=404, detail="Not found")


@app.post("/cart/checkout", status_code=201)
def checkout(data: CheckoutRequest):
    global order_counter

    if not cart:
        raise HTTPException(status_code=400, detail="Cart empty")

    created = []
    total = 0

    for c in cart:
        order = {
            "order_id": order_counter,
            "customer": data.customer_name,
            "item": c["name"],
            "quantity": c["quantity"],
            "total_price": c["subtotal"]
        }
        orders.append(order)
        created.append(order)
        total += c["subtotal"]
        order_counter += 1

    cart.clear()

    return {"orders": created, "grand_total": total}


# Q16 SEARCH
@app.get("/menu/search")
def search(keyword: str):
    result = [
        i for i in menu
        if keyword.lower() in i["name"].lower() or keyword.lower() in i["category"].lower()
    ]

    if not result:
        return {"message": f"No items found for {keyword}"}

    return {"results": result, "total_found": len(result)}


# Q17 SORT
@app.get("/menu/sort")
def sort_menu(sort_by: str = "price", order: str = "asc"):

    if sort_by not in ["price", "name", "category"]:
        return {"error": "sort_by must be price, name or category"}

    if order not in ["asc", "desc"]:
        return {"error": "order must be asc or desc"}

    reverse = order == "desc"

    result = sorted(menu, key=lambda x: x[sort_by], reverse=reverse)

    return {"sorted": result}


# Q18 PAGINATION
@app.get("/menu/page")
def paginate(page: int = 1, limit: int = 3):
    start = (page - 1) * limit

    return {
        "page": page,
        "limit": limit,
        "total": len(menu),
        "total_pages": -(-len(menu) // limit),
        "items": menu[start:start + limit]
    }


# Q19 ORDER SEARCH + SORT
@app.get("/orders/search")
def search_orders(customer_name: str):
    result = [
        o for o in orders
        if customer_name.lower() in o["customer"].lower()
    ]

    return {"orders": result}


@app.get("/orders/sort")
def sort_orders(order: str = "asc"):
    return {
        "orders": sorted(orders, key=lambda x: x["total_price"], reverse=(order == "desc"))
    }


# Q20 BROWSE (FINAL)
@app.get("/menu/browse")
def browse(
    keyword: Optional[str] = None,
    sort_by: str = "price",
    order: str = "asc",
    page: int = 1,
    limit: int = 4
):
    result = menu

    # search
    if keyword:
        result = [
            i for i in result
            if keyword.lower() in i["name"].lower()
        ]

    # sort
    if sort_by in ["price", "name", "category"]:
        result = sorted(result, key=lambda x: x[sort_by], reverse=(order == "desc"))

    total = len(result)

    # pagination
    start = (page - 1) * limit
    result = result[start:start + limit]

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "results": result
    }



# Q3 GET BY ID
@app.get("/menu/{item_id}")
def get_item(item_id: int):
    item = find_menu_item(item_id)
    if not item:
        return {"error": "Item not found"}
    return item