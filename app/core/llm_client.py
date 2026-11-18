
from groq import Groq
from groq import AuthenticationError
from groq import APIConnectionError
from groq import RateLimitError
from groq import APIStatusError

from app.core.config import get_settings


# STEP 1: Send a request to Groq

def generate_completion(
    messages,
    tools=None,
    tool_choice=None,
    response_format=None
):

    settings = get_settings()

    client = Groq(
        api_key=settings["api_key"],
        timeout=30.0,
        max_retries=2
    )

    request_options = {
        "model": settings["model"],
        "messages": messages,
        "max_completion_tokens": 1000
    }

    if tools is not None:
        request_options["tools"] = tools

    if tool_choice is not None:
        request_options["tool_choice"] = tool_choice

    if response_format is not None:
        request_options["response_format"] = response_format

    try:

        response = client.chat.completions.create(**request_options)

        return response.choices[0].message

    except AuthenticationError as error:
        raise RuntimeError(
            "Groq authentication failed. Check your API key."
        ) from error

    except RateLimitError as error:
        raise RuntimeError(
            "Groq rate limit reached. Check your account limits."
        ) from error

    except APIConnectionError as error:
        raise RuntimeError(
            "Could not connect to Groq. Check your internet connection."
        ) from error

    except APIStatusError as error:

        print("\nGroq API Error")
        print("HTTP Status:", error.status_code)
        print("Error Details:", error.body)
        print("Request ID:", getattr(error, "request_id", "Not available"))

        raise RuntimeError(
            "Groq rejected the API request. See error details above."
        ) from error


# STEP 2: Keep the simple text-response interface

def generate_response(messages, response_format=None):

    message = generate_completion(
        messages,
        response_format=response_format
    )

    result = message.content

    if not result:
        raise RuntimeError("The model returned an empty response.")

    return result
