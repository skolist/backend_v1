'''
Module Exposes a function to test if all API and SECURE KEYs are work
'''

def check_gemini_api_key(str : gemini_key):
    import google.genai as genai

# Replace with your actual API key

    try:
        genai.configure(api_key=gemini_key)

        # We use 'gemini-1.5-flash' as it is fast and cheap for testing
        model = genai.GenerativeModel('gemini-1.5-flash')

        response = model.generate_content("Are you working?")
        print(f"✅ Success! Response: {response.text}") 

    except Exception as e:
        print(f"❌ Error: {e}")

def check_openai_api_key() -> bool:
    try:
        from openai import OpenAI

        client = OpenAI()  # picks OPENAI_API_KEY from env

        resp = client.responses.create(
            model="gpt-4.1-mini",
            input="Say OK"
        )

        return bool(resp.output_text)

    except Exception as e:
        print("OpenAI key check failed:", e)
        return False

