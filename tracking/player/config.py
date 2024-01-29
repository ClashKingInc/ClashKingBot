from os import getenv
from dotenv import load_dotenv
from dataclasses import dataclass
load_dotenv()


@dataclass(frozen=True, slots=True)
class Config:
    min_coc_email = 1
    max_coc_email = 12
    coc_password = getenv("COC_PASSWORD")

    secondary_loop_change = 15
    tertiary_loop_change = 150
    max_tag_split = 50_000

    static_mongodb = getenv("STATIC_MONGODB")
    stats_mongodb = getenv("STATS_MONGODB")
    redis_ip = getenv("REDIS_IP")
    redis_pw = getenv("REDIS_PW")
