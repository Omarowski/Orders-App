from email.mime import image
import uuid
from datetime import datetime

import gspread
import streamlit as st

# ---- Settings ----
START_STOCK = ""
PRICE = ""
SHEET_ID = "1-h_0z9QFpHA3Aw9heRS9S_9HZTY5kfxqk_zWF0k21nQ"
# ------------------

st.set_page_config(page_title="Olive oil, 5 L can", page_icon="🫒")


@st.cache_resource
def get_tabs():
    gc = gspread.service_account_from_dict(dict(st.secrets["gcp_service_account"]))
    book = gc.open_by_key(SHEET_ID)
    try:
        stock_ws = book.worksheet("Stock")
    except gspread.WorksheetNotFound:
        stock_ws = book.add_worksheet("Stock", rows=5, cols=3)
        stock_ws.update("A1:B1", [["Cans left", START_STOCK]])
        stock_ws.update("A2:B2", [["Price per can", PRICE]])
    try:
        orders_ws = book.worksheet("Orders")
    except gspread.WorksheetNotFound:
        orders_ws = book.add_worksheet("Orders", rows=1000, cols=10)
        orders_ws.append_row(
            ["Time", "Order ID", "Name", "Phone", "Email", "Address",
             "Cans", "Litres", "Total zł", "Cans left"]
        )
    return stock_ws, orders_ws


def read_stock(stock_ws):
    return int(float(stock_ws.acell("B1").value or 0))
def read_price(price_ws):
    return int(float(price_ws.acell("B2").value or 0))


def place_order(stock_ws, orders_ws, name, phone, email, address, qty):
    left = read_stock(stock_ws)  # fresh read right before writing
    if qty > left:
        return False, left, None
    remaining = left - qty
    stock_ws.update_acell("B1", remaining)
    order_id = "O" + uuid.uuid4().hex[:8].upper()
    orders_ws.append_row(
        [datetime.now().strftime("%Y-%m-%d %H:%M:%S"), order_id, name, phone,
         email, address, qty, qty * 5, qty * PRICE, remaining]
    )
    return True, remaining, order_id


stock_ws, orders_ws = get_tabs()
stock = read_stock(stock_ws)
PRICE = read_price(stock_ws)


st.title("Olive oil in a 5-litre can")
st.write("One oil, one size. Choose how many cans you need and send your order. ")

# col1, col2, col3 = st.columns(3)
# col1.metric("Price per 5 L can", f"{PRICE} zł")
# col2.metric("Stock", "Sold out" if stock <= 0 else f"{stock} cans left")
img_col, info_col = st.columns([1, 2])
img_col.image("oil.jpeg", use_container_width=True)
with info_col:
    st.metric("Price per 5 L can", f"{PRICE} zł")
    st.metric("Stock", "Sold out" if stock <= 0 else f"{stock} cans left")

if "done" in st.session_state:
    d = st.session_state["done"]
    st.success(
        f"Order {d['id']} received: {d['qty']} can(s), {d['qty'] * 5} L, "
        f"{d['qty'] * PRICE} zł. "
    )
    if st.button("Place another order"):
        del st.session_state["done"]
        st.rerun()
elif stock <= 0:
    st.warning("Sold out. Check back later.")
else:
    with st.form("order"):
        qty = st.number_input("Number of cans", min_value=1, max_value=stock, value=1, step=1)
        # st.write(f"**Total: {int(qty) * PRICE} zł**")
        name = st.text_input("Full name")
        phone = st.text_input("Phone number")
        email = st.text_input("Email (optional)")
        address = st.text_area("Delivery address")
        send = st.form_submit_button("Send order")

    if send:
        if not (name.strip() and phone.strip() and address.strip()):
            st.error("Enter your name, phone number and delivery address to send the order.")
        else:
            ok, left, oid = place_order(
                stock_ws, orders_ws, name.strip(), phone.strip(),
                email.strip(), address.strip(), int(qty),
            )
            if ok:
                st.session_state["done"] = {"id": oid, "qty": int(qty), "phone": phone.strip()}
                st.rerun()
            else:
                st.error(f"Only {left} cans are left. Lower the number and try again.")