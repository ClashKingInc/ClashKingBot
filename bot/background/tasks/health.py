import uvicorn
from fastapi import FastAPI
from classes.bot import CustomClient


def create_health_app(bot: 'CustomClient') -> FastAPI:
    """
    Creates a FastAPI health check app with access to the bot instance.

    :param bot: The bot instance to check readiness.
    :return: A FastAPI application instance.
    """
    health_app = FastAPI()

    @health_app.get('/health')
    async def health_check():
        if bot.is_ready():
            return {'status': 'ok', 'details': 'Bot is running and ready'}
        else:
            return {'status': 'error', 'details': 'Bot is not ready'}

    return health_app


def run_health_check_server(bot: 'CustomClient') -> None:
    """
    Starts the health check FastAPI server.

    :param bot: The bot instance to check readiness.
    """
    app = create_health_app(bot)
    uvicorn.run(app, host='127.0.0.1', port=8027)
