from fastapi import FastAPI
from app.database.database import engine, Base
from app.core.razorpay_client import client
from app.api.webhooks import router as webhook_router
from app.api.customer import router as customer_router
from app.api.metrics import router as metrics_router
from app.api.demo import router as demo_router
from fastapi.middleware.cors import CORSMiddleware
import os

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Razorpay Revenue Recovery Engine")

cors_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:3000",
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(webhook_router)
app.include_router(customer_router)
app.include_router(metrics_router)
app.include_router(demo_router)


@app.get("/")
def root():
    return {
        "status": "ok",
        "message": "Revenue Recovery Engine is running"
    }


@app.get("/razorpay-test")
def razorpay_test():
    if os.getenv("ENABLE_RAZORPAY_TEST", "false").strip().lower() not in {
        "1",
        "true",
        "yes",
        "on",
    }:
        return {
            "status": "disabled",
            "message": "Set ENABLE_RAZORPAY_TEST=true to enable this probe",
        }

    try:
        payments = client.payment.all({"count": 1})

        return {
            "status": "success",
            "message": "Razorpay connection successful",
            "data": payments
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }