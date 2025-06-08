from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List

app = FastAPI()

class Parcel(BaseModel):
    customerName: str
    deliveryAddress: str
    contactNumber: str
    parcelSize: str
    parcelWeight: str
    trackingNumber: str

class ParcelDTO(BaseModel):
    customerName: str
    deliveryAddress: str
    trackingNumber: str

parcel_db: List[Parcel] = []

@app.get("/parcels", response_model=List[ParcelDTO])
def get_all_parcels():
    return [ParcelDTO(**p.dict()) for p in parcel_db]

@app.get("/parcels/{trackingNumber}", response_model=Parcel)
def get_parcel(trackingNumber: str):
    for p in parcel_db:
        if p.trackingNumber == trackingNumber:
            return p
    raise HTTPException(status_code=404, detail="Parcel not found")

@app.post("/parcels")
def create_parcel(parcel: Parcel):
    parcel_db.append(parcel)
    return {"message": "Parcel created"}

@app.put("/parcels/{trackingNumber}")
def update_parcel(trackingNumber: str, updated: Parcel):
    for i, p in enumerate(parcel_db):
        if p.trackingNumber == trackingNumber:
            parcel_db[i] = updated
            return {"message": "Parcel updated"}
    raise HTTPException(status_code=404, detail="Parcel not found")

@app.delete("/parcels/{trackingNumber}")
def delete_parcel(trackingNumber: str):
    for i, p in enumerate(parcel_db):
        if p.trackingNumber == trackingNumber:
            del parcel_db[i]
            return {"message": "Parcel deleted"}
    raise HTTPException(status_code=404, detail="Parcel not found")
