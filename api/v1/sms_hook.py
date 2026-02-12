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

# async def send_msg91_sms(phone: str, otp: str):
#     """
#     Helper function to call MSG91 Flow API.
#     """
#     # MSG91 wants international format without the '+'
#     clean_phone = phone.replace("+", "")

#     url = "https://control.msg91.com/api/v5/flow/"

#     headers = {
#         "authkey": settings.MSG91_AUTH_KEY,
#         "content-type": "application/json"
#     }

#     # IMPORTANT: The key "otp" here must match the variable
#     # you used in your MSG91 template (e.g. ##otp##)
#     payload = {
#         "template_id": settings.MSG91_TEMPLATE_ID,
#         "short_url": "0",
#         "recipients": [
#             {
#                 "mobiles": clean_phone,
#                 "otp": otp
#             }
#         ]
#     }

#     async with httpx.AsyncClient() as client:
#         try:
#             response = await client.post(url, json=payload, headers=headers)
#             response.raise_for_status()
#             logger.info(f"MSG91 success: {response.json()}")
#             return True
#         except Exception as e:
#             logger.error(f"MSG91 API failure: {e}")
#             return False


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
    # This assumes we have a service_role client or similar that can write to this table
    # Since we are in the backend, we should use the service key
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
        # Validate if we should return 500 or just log it.
        # If we return 500, Supabase might retry or show error to user.
        # It is safer to return 500 so we know something went wrong.
        raise HTTPException(status_code=500, detail="Failed to store OTP") from e

    # 4. Return clean 200 OK so Supabase thinks "SMS Sent"
    return {"status": "success"}
