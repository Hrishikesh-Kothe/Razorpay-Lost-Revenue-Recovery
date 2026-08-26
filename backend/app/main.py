from fastapi import FastAPI
from app.database.database import engine, Base
from app.core.razorpay_client import client
from app.api.webhooks import router as webhook_router
from app.api.customer import router as customer_router
from app.api.metrics import router as metrics_router
from fastapi.middleware.cors import CORSMiddleware

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Razorpay Revenue Recovery Engine")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(webhook_router)
app.include_router(customer_router)
app.include_router(metrics_router)


@app.get("/")
def root():
    return {
        "status": "ok",
        "message": "Revenue Recovery Engine is running"
    }


@app.get("/razorpay-test")
def razorpay_test():
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