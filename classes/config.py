from dotenv import load_dotenv

load_dotenv()


class Config:
    def __init__(self, remote_settings: dict):
        self.discord_proxy_url: str = remote_settings.get('discord_proxy_url')

        self.link_api_username: str = remote_settings.get('link_api_user')
        self.link_api_password: str = remote_settings.get('link_api_pw')

        self.static_mongodb: str = remote_settings.get('static_db')
        self.stats_mongodb: str = remote_settings.get('stats_db')

        self.bot_token: str = ''

        self.sentry_dsn: str = remote_settings.get('sentry_dsn')

        self.redis_ip = remote_settings.get('redis_ip')
        self.redis_pw = remote_settings.get('redis_pw')

        self.bunny_api_token = remote_settings.get('bunny_api_token')

        self.portainer_ip = remote_settings.get('portainer_ip')
        self.portainer_api_token = remote_settings.get('portainer_api_token')
        self.portainer_user = remote_settings.get('portainer_user')
        self.portainer_pw = remote_settings.get('portainer_password')

        self.reddit_user_secret = remote_settings.get('reddit_secret')
        self.reddit_user_password = remote_settings.get('reddit_pw')

        self.is_beta = remote_settings.get('is_beta')
        self.is_custom = remote_settings.get('is_custom')
        self.is_main = remote_settings.get('is_main')

        self.cluster_id = 0
        self.total_clusters = remote_settings.get('total_clusters')

        self.emoji_url = 'https://assets.clashk.ing/bot/emojis.json'

        self.clashofstats_user_agent = remote_settings.get('clashofstats_user_agent')

        self.gitbook_token = remote_settings.get('gitbook_token')
        self.open_ai_key = remote_settings.get('open_ai_key')

        self.emoji_asset_version = remote_settings.get('emoji_version')

        self.github_token = remote_settings.get('github_token')
        self.clash_event_ws = remote_settings.get('clash_event_ws')

        self.clashking_api_token = remote_settings.get('clashking_api_token')
