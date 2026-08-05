"""Loads and indexes the Olist CSV dataset once per pipeline run.

All agents read through this shared, read-only store instead of touching
the CSVs directly, so every "tool call" an agent makes is traceable and
consistent across the run.
"""
from __future__ import annotations

import pandas as pd

from .config import DATA_DIR


class DataStore:
    def __init__(self) -> None:
        self.orders = pd.read_csv(DATA_DIR / "olist_orders_dataset.csv", dtype=str)
        self.items = pd.read_csv(DATA_DIR / "olist_order_items_dataset.csv", dtype=str)
        self.payments = pd.read_csv(DATA_DIR / "olist_order_payments_dataset.csv", dtype=str)
        self.sellers = pd.read_csv(DATA_DIR / "olist_sellers_dataset.csv", dtype=str)
        self.customers = pd.read_csv(DATA_DIR / "olist_customers_dataset.csv", dtype=str)

        date_cols = [
            "order_purchase_timestamp",
            "order_approved_at",
            "order_delivered_carrier_date",
            "order_delivered_customer_date",
            "order_estimated_delivery_date",
        ]
        for col in date_cols:
            self.orders[col] = pd.to_datetime(self.orders[col], errors="coerce")

        self.items["price"] = pd.to_numeric(self.items["price"], errors="coerce")
        self.items["freight_value"] = pd.to_numeric(self.items["freight_value"], errors="coerce")
        self.items["order_item_id"] = pd.to_numeric(
            self.items["order_item_id"], errors="coerce"
        ).astype("Int64")
        self.items["shipping_limit_date"] = pd.to_datetime(
            self.items["shipping_limit_date"], errors="coerce"
        )

        self.payments["payment_value"] = pd.to_numeric(self.payments["payment_value"], errors="coerce")
        self.payments["payment_sequential"] = pd.to_numeric(
            self.payments["payment_sequential"], errors="coerce"
        ).astype("Int64")

    def get_order(self, order_id: str):
        rows = self.orders[self.orders["order_id"] == order_id]
        return rows.iloc[0] if len(rows) else None

    def get_items(self, order_id: str) -> pd.DataFrame:
        return self.items[self.items["order_id"] == order_id].sort_values("order_item_id")

    def get_payments(self, order_id: str) -> pd.DataFrame:
        return self.payments[self.payments["order_id"] == order_id].sort_values(
            "payment_sequential"
        )

    def get_seller(self, seller_id: str):
        rows = self.sellers[self.sellers["seller_id"] == seller_id]
        return rows.iloc[0] if len(rows) else None

    def seller_exists(self, seller_id: str) -> bool:
        return bool(len(self.sellers[self.sellers["seller_id"] == seller_id]))

    def item_exists(self, order_id: str, order_item_id: int) -> bool:
        items = self.get_items(order_id)
        return bool(len(items[items["order_item_id"] == order_item_id]))

    def payment_exists(self, order_id: str, payment_sequential: int) -> bool:
        payments = self.get_payments(order_id)
        return bool(len(payments[payments["payment_sequential"] == payment_sequential]))
