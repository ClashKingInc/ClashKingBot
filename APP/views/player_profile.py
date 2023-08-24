import flet as ft
from .clients import coc_client

async def PlayerView(page:ft.Page):
    page.title = "player"
    tag = page.route.split("/")[-1]
    player = await coc_client.get_player(player_tag=tag)


    async def open_settings(e):
        await page.go_async("/")

    return ft.View(
        "/players",
        controls=[
            ft.Text(f"This Is {player.name}"),
            ft.ElevatedButton("Go Main", on_click=open_settings),
        ]
    )
