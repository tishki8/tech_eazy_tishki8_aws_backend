from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from typing import Optional, List
from pydantic import BaseModel
from jose import JWTError, jwt  # make sure python-jose is installed
from datetime import datetime, timedelta

app = FastAPI()

# CORS setup
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Secret key and algorithm for JWT
SECRET_KEY = "your_secret_key_here"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Dummy user store (replace with real DB)
fake_users_db = {
    "vendor1": {
        "username": "vendor1",
        "password": "password123",
        "role": "vendor"
    }
}

# Pydantic models
class Token(BaseModel):
    access_token: str
    token_type: str

class Parcel(BaseModel):
    customerName: str
    deliveryAddress: str
    contactNumber: str
    parcelSize: str
    parcelWeight: str
    trackingNumber: str

# In-memory parcels list
parcels = []

def authenticate_user(username: str, password: str):
    user = fake_users_db.get(username)
    if not user or user["password"] != password:
        return False
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta if expires_delta else timedelta(minutes=15))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: Optional[str] = payload.get("sub")
        role: Optional[str] = payload.get("role")
        if username is None or role is None:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        return {"username": username, "role": role}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.post("/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["username"], "role": user["role"]},
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/parcels")
async def create_parcel(parcel: Parcel, current_user: dict = Depends(get_current_user)):
    parcels.append(parcel)
    return {"message": "Parcel created successfully"}

@app.get("/parcels", response_model=List[Parcel])
async def list_parcels(current_user: dict = Depends(get_current_user)):
    return parcels

@app.get("/parcels/{trackingNumber}", response_model=Parcel)
async def get_parcel(trackingNumber: str, current_user: dict = Depends(get_current_user)):
    for parcel in parcels:
        if parcel.trackingNumber == trackingNumber:
            return parcel
    raise HTTPException(status_code=404, detail="Parcel not found")

@app.delete("/parcels/{trackingNumber}")
async def delete_parcel(trackingNumber: str, current_user: dict = Depends(get_current_user)):
    global parcels
    parcels = [p for p in parcels if p.trackingNumber != trackingNumber]
    return {"message": "Parcel deleted"}

