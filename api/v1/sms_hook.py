import logging

from fastapi import APIRouter, HTTPException, Request
from standardwebhooks.webhooks import Webhook

from config import settings

logger = logging.getLogger(__name__)

# Settings from your dashboard
HOOK_SECRET = settings.SMS_HOOK_SECRET

if HOOK_SECRET and HOOK_SECRET.startswith("v1,"):
    HOOK_SECRET = HOOK_SECRET.split(",", 1)[1]

router = APIRouter()


@router.post("/auth/sms-hook")
async def handle_supabase_sms(request: Request):
    payload = await request.body()
    headers = request.headers

    # 1. Verify the Signature
    try:
        wh = Webhook(HOOK_SECRET)
        data = wh.verify(payload.decode("utf-8"), headers)
    except Exception as e:
        logger.error(f"Verification failed: {e}")
        raise HTTPException(status_code=401, detail="Invalid signature") from e

    # 2. Extract data
    user_phone = data.get("user", {}).get("phone")
    otp_code = data.get("sms", {}).get("otp")

    if not user_phone or not otp_code:
        raise HTTPException(status_code=400, detail="Missing phone or OTP")

    # 3. Store in Supabase table
    logger.info(f"Storing OTP for {user_phone}")

    # We need a direct Supabase client to write to the table
    # This assumes we have a service_role client
    try:
        from supabase import Client, create_client

        url: str = settings.SUPABASE_URL
        key: str = settings.SUPABASE_SERVICE_KEY
        supabase: Client = create_client(url, key)

        # Upsert: if phone exists, update the otp
        data = {
            "phone_number": user_phone,
            "otp": otp_code,
            # created_at will default to now()
        }
        res = supabase.table("phonenum_otps").upsert(data).execute()

        logger.info(f"Supabase upsert result for {user_phone}: {res}")

    except Exception as e:
        logger.error(f"Failed to store OTP in phonenum_otps: {e}")
        raise HTTPException(status_code=500, detail="Failed to store OTP") from e

    # 4. Return clean 200 OK so Supabase thinks "SMS Sent"
    return {"status": "success"}
