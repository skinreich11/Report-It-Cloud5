from flask import current_app


class ServiceConfigError(RuntimeError):
    pass


def create_openai_client():
    api_key = current_app.config.get("OPENAI_API_KEY")
    if not api_key:
        raise ServiceConfigError("OPENAI_API_KEY is not configured")

    try:
        from openai import OpenAI
    except ImportError as error:
        raise ServiceConfigError("The openai package is not installed") from error

    return OpenAI(api_key=api_key)
