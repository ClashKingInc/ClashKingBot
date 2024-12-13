import secrets
import base64
import uuid

def generate_token() -> str:
    """
    Generate a secure and unique token for use in the database.
    Combines UUID and secrets for added randomness.

    Returns:
        str: A URL-safe base64-encoded token.
    """
    # Generate a UUID and its bytes representation
    random_uuid = uuid.uuid4()
    uuid_bytes = random_uuid.bytes

    # Add extra randomness with secrets
    random_bytes = secrets.token_bytes(16)  # Generate 16 random bytes

    # Combine UUID bytes with additional random bytes
    combined_bytes = uuid_bytes + random_bytes

    # Encode to URL-safe base64
    token = base64.urlsafe_b64encode(combined_bytes).rstrip(b"=").decode("utf-8")

    return token
