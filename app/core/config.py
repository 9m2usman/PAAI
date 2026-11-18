import os
from dotenv import load_dotenv


# STEP 1: Load environment variables
load_dotenv()


# STEP 2: Read application configuration
def get_settings():

    api_key = os.getenv("GROQ_API_KEY", "").strip()
    model = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b").strip()

    # STEP 3: Validate required configuration
    if not api_key or api_key == "your_groq_api_key_here":
        raise ValueError(
            "GROQ_API_KEY is missing. Configure it in your .env file."
        )

    if not model:
        raise ValueError("GROQ_MODEL cannot be empty.")

    # STEP 4: Return configuration
    return {
        "api_key": api_key,
        "model": model
    }
