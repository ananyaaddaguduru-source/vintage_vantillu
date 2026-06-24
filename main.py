from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import sqlite3

app = FastAPI()
KITCHEN_PASSWORD = "vantillu123"
conn = sqlite3.connect("orders.db", check_same_thread=False)
cursor = conn.cursor()
try:
    cursor.execute(
        "ALTER TABLE orders ADD COLUMN eta TEXT"
    )
    conn.commit()
except:
    pass

cursor.execute("""
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    phone TEXT,
    address TEXT,
    landmark TEXT,
    total TEXT,
    items TEXT,
    status TEXT
)
""")

conn.commit()
app.mount("/static", StaticFiles(directory="static"), name="static")

# Cleaner setup - no strict static folder requirement to cause server errors
templates = Jinja2Templates(directory="templates")

# Live in-memory database storage for active orders
ORDERS_DATABASE = []

@app.get("/", response_class=HTMLResponse)
async def read_index(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html"
    )

@app.post("/submit-order")
async def submit_order(
    customer_name: str = Form(...),
    customer_phone: str = Form(...),
    customer_address: str = Form(...),
    customer_landmark: str = Form(""),
    total_amount: str = Form(...),
    items_ordered: str = Form(...)
):
    cursor.execute(
        """
        INSERT INTO orders
        (name, phone, address, landmark, total, items, status,eta)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            customer_name,
            customer_phone,
            customer_address,
            customer_landmark,
            total_amount,
            items_ordered,
            "Pending Verification",
            ""
        )
    )

    conn.commit()

    order_id = cursor.lastrowid

    return RedirectResponse(
        url=f"/track/{order_id}",
        status_code=303
)
@app.get("/order-success", response_class=HTMLResponse)
async def order_success():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Order Placed!</title>
        <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap" rel="stylesheet">
        <style>
            body { font-family: 'Poppins', sans-serif; background-color: #FDF9F3; text-align: center; padding: 60px 20px; color: #2A2421; }
            .card { background: white; max-width: 450px; margin: 0 auto; padding: 40px 30px; border-radius: 24px; box-shadow: 0 10px 30px rgba(140,29,29,0.05); }
            h1 { color: #8C1D1D; font-size: 2rem; margin-bottom: 10px; }
            p { color: #7F8C8D; font-size: 1rem; line-height: 1.6; }
            .badge { display: inline-block; background-color: #FFF0DB; color: #E67E22; padding: 6px 16px; border-radius: 20px; font-weight: 600; font-size: 0.85rem; margin-top: 15px; }
        </style>
    </head>
    <body>
        <div class="card">
            <h1>Order Sent to Kitchen! 👩🏽‍🍳</h1>
            <p>Your order details have been securely sent straight to our cooking team.</p>
            <span class="badge">Status: Sent to Kitchen</span>
        </div>
    </body>
    </html>
    """
@app.post("/update-status/{order_id}")
async def update_status(order_id: int, status: str = Form(...)):

    cursor.execute(
        """
        UPDATE orders
        SET status = ?
        WHERE id = ?
        """,
        (status, order_id)
    )

    conn.commit()

    return RedirectResponse(
        url="/kitchen-line",
        status_code=303
    )
@app.post("/update-eta/{order_id}")
async def update_eta(
    order_id: int,
    eta: str = Form(...)
):

    cursor.execute(
        """
        UPDATE orders
        SET eta = ?
        WHERE id = ?
        """,
        (eta, order_id)
    )

    conn.commit()

    return RedirectResponse(
        url="/kitchen-line",
        status_code=303
    )
@app.get("/track/{order_id}", response_class=HTMLResponse)
async def track_order(order_id: int):

    cursor.execute(
        """
        SELECT status, eta
        FROM orders
        WHERE id = ?
        """,
        (order_id,)
    )

    order = cursor.fetchone()

    if not order:
        return HTMLResponse(
            "<h2>Order not found</h2>",
            status_code=404
        )

    status = order[0]
    eta = order[1] or "Not assigned yet"

    return f"""
    <html>
    <body style="font-family:Poppins;text-align:center;padding-top:80px;">
        <h1>Order #{order_id}</h1>

        <h2>Status: {status}</h2>

        <h3>ETA: {eta}</h3>

        <p>Refresh this page for latest updates.</p>
    </body>
    </html>
    """
@app.get("/kitchen-login", response_class=HTMLResponse)
async def kitchen_login():
    return """
    <html>
    <body style="font-family:Arial;text-align:center;padding-top:100px;">
        <h2>Vintage Vantillu Kitchen Login</h2>

        <form action="/kitchen-auth" method="post">
            <input type="password"
                   name="password"
                   placeholder="Enter Password">

            <br><br>

            <button type="submit">
                Login
            </button>
        </form>
    </body>
    </html>
    """


@app.post("/kitchen-auth")
async def kitchen_auth(password: str = Form(...)):

    if password == KITCHEN_PASSWORD:
        return RedirectResponse(
            url="/kitchen-line",
            status_code=303
        )

    return HTMLResponse(
        "<h2>Wrong Password</h2>",
        status_code=401
    )

@app.get("/kitchen-line", response_class=HTMLResponse)
async def kitchen_dashboard(request: Request):

    cursor.execute("""
        SELECT id, name, phone, address, landmark,
               total, items, status, eta
        FROM orders
        WHERE status != 'Archived'
        ORDER BY id DESC
    """)

    rows = cursor.fetchall()

    orders = []

    for row in rows:
        orders.append({
            "id": row[0],
            "name": row[1],
            "phone": row[2],
            "address": row[3],
            "landmark": row[4],
            "total": row[5],
            "items": row[6],
            "status": row[7],
            "eta": row[8]
        })

    return templates.TemplateResponse(
        request=request,
        name="kitchen.html",
        context={
            "orders": orders
        }
    )


