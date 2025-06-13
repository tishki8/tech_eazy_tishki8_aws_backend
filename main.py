from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
from datetime import datetime
from math import radians, cos, sin, asin, sqrt

app = FastAPI()

# Allow CORS
origins = ["http://localhost:3000"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage
orders = []
parcels = {}
tracking_data = {
    "PKG123": {"status": "In Transit", "location": "Hub 2"},
    "PKG456": {"status": "Delivered", "location": "Mumbai"},
}

# Dummy parcel locations (source and destination pin -> lat/lon)
parcel_locations = {
    "PKG123": {"from": "400001", "to": "400076"},
    "PKG456": {"from": "400002", "to": "400076"},
}

# Dummy pincode to lat/lon mapping
pincode_coords = {
    "400001": (18.944, 72.835),  # Fort
    "400076": (19.123, 72.836),  # Powai
    "400002": (18.950, 72.825),
}

# Models
class DeliveryOrderDTO(BaseModel):
    vendor_name: str
    date: str
    total_orders: int
    file_link: Optional[str]

class ParcelSummary(BaseModel):
    pincode: str
    count: int

class TrackingResponse(BaseModel):
    tracking_id: str
    status: str
    location: str

# Helper to get user role from query (for simplicity)
def get_role(role: str = Query(...)):
    valid_roles = ["admin", "vendor", "driver", "customer"]
    if role not in valid_roles:
        raise HTTPException(status_code=400, detail="Invalid role")
    return role

# Public Tracking API
@app.get("/track", response_model=TrackingResponse)
def track_parcel(tracking_id: str):
    if tracking_id not in tracking_data:
        raise HTTPException(status_code=404, detail="Tracking ID not found")
    data = tracking_data[tracking_id]
    return {
        "tracking_id": tracking_id,
        "status": data["status"],
        "location": data["location"]
    }

# Upload Orders - Vendor only
@app.post("/upload-orders")
async def upload_orders(
    vendor_name: str = Form(...),
    file: UploadFile = File(...),
    role: str = Depends(get_role)
):
    if role != "vendor":
        raise HTTPException(status_code=403, detail="Only vendors can upload orders")

    content = await file.read()
    lines = content.decode().strip().split('\n')
    total = len(lines)

    today = datetime.today().strftime('%Y-%m-%d')
    orders.append(DeliveryOrderDTO(
        vendor_name=vendor_name,
        date=today,
        total_orders=total,
        file_link=f"/files/{file.filename}"
    ))

    for line in lines:
        parts = line.split(',')
        if len(parts) >= 2:
            pincode = parts[1].strip()
            parcels[pincode] = parcels.get(pincode, 0) + 1

    return {"message": "File uploaded successfully"}

# Get Orders - Admin & Vendor
@app.get("/delivery-orders", response_model=List[DeliveryOrderDTO])
def get_orders(role: str = Depends(get_role)):
    if role not in ["vendor", "admin"]:
        raise HTTPException(status_code=403, detail="Unauthorized access")
    return orders

# Parcel Summary - Admin only
@app.get("/parcels-summary", response_model=Dict[str, int])
def get_parcel_summary(role: str = Depends(get_role)):
    if role != "admin":
        raise HTTPException(status_code=403, detail="Only admin can access parcel summary")
    return parcels

# Route Finder for Admin and Customer
@app.get("/route")
def get_route(tracking_id: str, role: str = Depends(get_role)):
    if role not in ["admin", "customer"]:
        raise HTTPException(status_code=403, detail="Unauthorized")

    parcel = parcel_locations.get(tracking_id)
    if not parcel:
        raise HTTPException(status_code=404, detail="Tracking ID not found")

    src, dest = parcel["from"], parcel["to"]
    if src not in pincode_coords or dest not in pincode_coords:
        raise HTTPException(status_code=404, detail="Pincode mapping not found")

    lat1, lon1 = pincode_coords[src]
    lat2, lon2 = pincode_coords[dest]
    distance = haversine(lat1, lon1, lat2, lon2)

    return {
        "tracking_id": tracking_id,
        "from": src,
        "to": dest,
        "distance_km": distance
    }

def haversine(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
    c = 2 * asin(sqrt(a))
    km = 6371 * c
    return round(km, 2)
