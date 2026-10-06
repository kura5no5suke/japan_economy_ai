import os

from dotenv import load_dotenv


load_dotenv()


DB_PATH = os.getenv(
    "ECONOMY_DB_PATH",
    "data/economy.db",
)
