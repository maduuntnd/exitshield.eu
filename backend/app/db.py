import os
from motor.motor_asyncio import AsyncIOMotorClient

_client = AsyncIOMotorClient(os.environ["MONGO_URL"])
db = _client[os.environ["DB_NAME"]]


async def create_indexes():
    await db.users.create_index("email", unique=True)
    await db.users.create_index("user_id", unique=True)
    await db.user_sessions.create_index("session_token")
    await db.password_reset_tokens.create_index("expires_at", expireAfterSeconds=0)
    await db.login_attempts.create_index("identifier")
    await db.organizations.create_index("api_key", unique=True)
    await db.customers.create_index("id", unique=True)
    await db.cancel_sessions.create_index("token", unique=True)
    await db.payment_transactions.create_index("session_id")


def close_client():
    _client.close()
