"""Pydantic schema for extracted invoice data (also used as the Ollama
structured-output schema, and later as FastAPI request/response models)."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class InvoiceHeader(BaseModel):
    invoice_number: str = ""
    invoice_date: str = ""
    due_date: Optional[str] = None
    payment_terms: Optional[str] = None
    company_code: Optional[str] = None
    vendor_name: str = ""
    vendor_address: Optional[str] = None
    vendor_tax_id: Optional[str] = None
    vendor_bank_name: Optional[str] = None
    vendor_account_no: Optional[str] = None
    vendor_sort_code: Optional[str] = None
    vendor_iban: Optional[str] = None
    customer_name: str = ""
    customer_address: Optional[str] = None
    po_number: Optional[str] = None
    reference_number: Optional[str] = None
    currency: str = ""
    subtotal: float = 0.0
    tax_amount: float = 0.0
    tax_percent: Optional[float] = None
    total_amount: float = 0.0


class LineItem(BaseModel):
    line_no: Optional[str] = None
    description: str
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    amount: float
    tax_percent: Optional[float] = None
    gl_account: Optional[str] = None
    cost_center: Optional[str] = None
    profit_center: Optional[str] = None
    reference_code: Optional[str] = None


class AdditionalField(BaseModel):
    field_name: str
    field_value: str


class Invoice(BaseModel):
    invoice_header: InvoiceHeader
    line_items: list[LineItem] = Field(min_length=1)
    additional_fields: list[AdditionalField] = []
