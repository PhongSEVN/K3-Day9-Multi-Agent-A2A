"""Loads and indexes the Olist CSVs used by the dispute-resolution agents.

Only the four datasets referenced by the business rules in README.md
section 4 are loaded (orders, order_items, order_payments, sellers).
Everything is read once per process and cached at module scope, since
run_pipeline.py processes 50 cases against the same tables.
"""

import os
import threading
import pandas as pd

_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

_orders_df = None
_items_df = None
_payments_df = None
_sellers_df = None
_load_lock = threading.Lock()


def _load():
    global _orders_df, _items_df, _payments_df, _sellers_df
    if _orders_df is not None:
        return
    # run_pipeline.py fans out across a thread pool; without this lock, two
    # threads racing the check-then-load above would both parse the CSVs
    # (wasted work) or, worse, one could read a partially-assigned module
    # global while the other is still mid-load.
    with _load_lock:
        if _orders_df is not None:
            return
        _load_impl()


def _load_impl():
    global _orders_df, _items_df, _payments_df, _sellers_df
    _orders_df = pd.read_csv(
        os.path.join(_DATA_DIR, "olist_orders_dataset.csv"),
        dtype=str,
    )
    _orders_df = _orders_df.set_index("order_id", drop=False)

    _items_df = pd.read_csv(
        os.path.join(_DATA_DIR, "olist_order_items_dataset.csv"),
        dtype={"order_id": str, "product_id": str, "seller_id": str},
    )
    _items_df["order_item_id"] = _items_df["order_item_id"].astype(int)
    _items_df["price"] = _items_df["price"].astype(float)
    _items_df["freight_value"] = _items_df["freight_value"].astype(float)

    _payments_df = pd.read_csv(
        os.path.join(_DATA_DIR, "olist_order_payments_dataset.csv"),
        dtype={"order_id": str, "payment_type": str},
    )
    _payments_df["payment_sequential"] = _payments_df["payment_sequential"].astype(int)
    _payments_df["payment_installments"] = _payments_df["payment_installments"].astype(int)
    _payments_df["payment_value"] = _payments_df["payment_value"].astype(float)

    _sellers_df = pd.read_csv(
        os.path.join(_DATA_DIR, "olist_sellers_dataset.csv"),
        dtype=str,
    )
    _sellers_df = _sellers_df.set_index("seller_id", drop=False)


def get_order(order_id: str):
    _load()
    if order_id not in _orders_df.index:
        return None
    row = _orders_df.loc[order_id]
    return row.to_dict()


def get_items(order_id: str):
    _load()
    rows = _items_df[_items_df["order_id"] == order_id].sort_values("order_item_id")
    return rows.to_dict(orient="records")


def get_payments(order_id: str):
    _load()
    rows = _payments_df[_payments_df["order_id"] == order_id].sort_values("payment_sequential")
    return rows.to_dict(orient="records")


def get_seller(seller_id: str):
    _load()
    if seller_id not in _sellers_df.index:
        return None
    row = _sellers_df.loc[seller_id]
    return row.to_dict()


def order_exists(order_id: str) -> bool:
    _load()
    return order_id in _orders_df.index


def item_exists(order_id: str, order_item_id: int) -> bool:
    _load()
    match = _items_df[
        (_items_df["order_id"] == order_id) & (_items_df["order_item_id"] == order_item_id)
    ]
    return not match.empty


def payment_exists(order_id: str, payment_sequential: int) -> bool:
    _load()
    match = _payments_df[
        (_payments_df["order_id"] == order_id)
        & (_payments_df["payment_sequential"] == payment_sequential)
    ]
    return not match.empty


def seller_exists(seller_id: str) -> bool:
    _load()
    return seller_id in _sellers_df.index
