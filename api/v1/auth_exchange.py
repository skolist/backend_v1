import asyncio
import logging

import firebase_admin
from fastapi import APIRouter, HTTPException
from firebase_admin import auth, credentials
from pydantic import BaseModel

from config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize Firebase Admin if not already initialized
# This is a bit of a singleton pattern within the module scope
# Ideally this should be done in a dedicated startup event or module
try:
    if not firebase_admin._apps:
        if settings.FIREBASE_CREDENTIALS:
            import json

            # Check if it's a JSON string or a file path
            creds_data = settings.FIREBASE_CREDENTIALS.strip()
            if creds_data.startswith("{"):
                try:
                    cred_dict = json.loads(creds_data)
                    cred = credentials.Certificate(cred_dict)
                    logger.info("Initializing Firebase Admin with JSON data from environment.")
                except json.JSONDecodeError:
                    logger.error("FIREBASE_CREDENTIALS looks like JSON but is invalid.")
                    cred = None
            else:
                # Treat as file path
                cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS)
                logger.info(
                    f"Initializing Firebase Admin with certificate file: {settings.FIREBASE_CREDENTIALS}"
                )

            if cred:
                firebase_admin.initialize_app(cred)
        else:
            logger.warning("FIREBASE_CREDENTIALS not set. Firebase Admin not initialized.")
except Exception as e:
    logger.error(f"Failed to initialize Firebase Admin: {e}", exc_info=True)


class ExchangeRequest(BaseModel):
    firebase_token: str


@router.post("/auth/exchange-firebase-token")
async def exchange_firebase_token(req: ExchangeRequest):
    """
    Exchanges a Firebase ID Token for the Supabase OTP stored in the database.
    This handles the race condition by retrying if the OTP is not immediately found.
    """
    token = req.firebase_token

    # 1. Verify Firebase Token
    try:
        decoded_token = auth.verify_id_token(token)
        phone_number = decoded_token.get("phone_number")
        if not phone_number:
            raise HTTPException(status_code=400, detail="Token does not contain a phone number")
    except Exception as e:
        logger.error(f"Firebase token verification failed: {e}")
        raise HTTPException(status_code=401, detail="Invalid Firebase token") from e

    logger.info(f"Exchange request for {phone_number}")

    # 2. Normalize Phone Number
    # Firebase usually returns E.164 (e.g. +919876543210).
    # Supabase also typically sends E.164.
    # We assume they match. If needed, insert normalization logic here.

    # 3. Retrieve OTP from Supabase Table with Retry Logic
    from supabase import Client, create_client

    url: str = settings.SUPABASE_URL
    key: str = settings.SUPABASE_SERVICE_KEY
    supabase: Client = create_client(url, key)

    max_retries = 6
    retry_delay = 0.5  # seconds

    found_otp = None
    phone_number = phone_number.replace("+", "")
    for attempt in range(max_retries):
        try:
            # Query the table
            res = (
                supabase.table("phonenum_otps")
                .select("otp")
                .eq("phone_number", phone_number)
                .execute()
            )

            if res.data and len(res.data) > 0:
                found_otp = res.data[0]["otp"]
                break

            # If not found, wait and retry
            logger.info(f"OTP not found for {phone_number}, attempt {attempt + 1}/{max_retries}")
            await asyncio.sleep(retry_delay)

        except Exception as e:
            logger.error(f"Supabase query failed: {e}")
            # If query actually fails (network/auth), we might want to break or continue.
            # For now, let's continue to be safe.
            await asyncio.sleep(retry_delay)

    if not found_otp:
        raise HTTPException(
            status_code=404, detail="OTP not found temporarily. Please try again or resend."
        )

    # 4. Return the OTP
    return {"otp": found_otp}
