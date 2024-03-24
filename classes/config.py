from os import getenv
from dotenv import load_dotenv
from dataclasses import dataclass
load_dotenv()

@dataclass(frozen=True, slots=True)
class Config:
    coc_email = getenv("COC_EMAIL")
    coc_password = getenv("COC_PASSWORD")

    min_coc_email = 49
    max_coc_email = 49

    static_mongodb = getenv("STATIC_MONGODB")
    stats_mongodb = getenv("STATS_MONGODB")
    link_api_username = getenv("LINK_API_USER")
    link_api_password = getenv("LINK_API_PW")
    bot_token = getenv("BOT_TOKEN")
    sentry_dsn = getenv("SENTRY_DSN")
    redis_ip = getenv("REDIS_IP")
    redis_pw = getenv("REDIS_PW")
    bunny_api_token = getenv("BUNNY_ACCESS_KEY")
    portainer_ip = getenv("PORTAINER_IP")
    portainer_api_token = getenv("PORTAINER_API_TOKEN")
    reddit_user_secret = getenv("REDDIT_SECRET")
    reddit_user_password = getenv("REDDIT_PW")
    open_ai_api_token = getenv("OPENAI_API_KEY")

    is_beta = (getenv("IS_BETA") == "TRUE")
    is_custom = (getenv("IS_CUSTOM") == "TRUE")
    is_main = (getenv("IS_MAIN") == "TRUE")
    cluster_id = 0

    portainer_user = getenv("PORTAINER_USER")
    portainer_pw = getenv("PORTAINER_PASSWORD")