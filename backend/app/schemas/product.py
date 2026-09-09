from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ProductBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    brand: str = Field(..., min_length=1, max_length=255)
    category: str = Field(..., min_length=1, max_length=100)
    manufacturer_name: Optional[str] = None
    manufacturer_address: Optional[str] = None
    country_of_origin: Optional[str] = "India"
    barcode: Optional[str] = None


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    brand: Optional[str] = None
    category: Optional[str] = None
    manufacturer_name: Optional[str] = None
    manufacturer_address: Optional[str] = None
    country_of_origin: Optional[str] = None
    barcode: Optional[str] = None


class ProductResponse(ProductBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    known_batches: List[str] = Field(default_factory=list)
    batches_count: int = 0
    created_at: datetime
    updated_at: datetime
