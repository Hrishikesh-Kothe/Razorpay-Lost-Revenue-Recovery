import os
import razorpay
from dotenv import load_dotenv

load_dotenv()

RZP_KEY_ID = os.getenv("RZP_KEY_ID")
RZP_KEY_SECRET = os.getenv("RZP_KEY_SECRET")

if not RZP_KEY_ID or not RZP_KEY_SECRET:
    raise RuntimeError("Razorpay API keys are missing from .env")

client = razorpay.Client(
    auth=(RZP_KEY_ID, RZP_KEY_SECRET)
)