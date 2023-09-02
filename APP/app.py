import asyncio
import flet as ft

from views.player_profile import PlayerView
from views.main_page import MainView


async def main(page: ft.Page):

    print("Initial route:", page.route)

    async def check_item_clicked(e):
        e.control.checked = not e.control.checked
        await page.update_async()

    async def route_change(e):
        print("Route change:", e.route)
        page.views.clear()
        appbar = ft.AppBar(
            leading=ft.Icon(ft.icons.MENU),
            leading_width=40,
            center_title=False,
            actions=[
                ft.PopupMenuButton(
                    items=[
                        ft.PopupMenuItem(text="Item 1"),
                        ft.PopupMenuItem(),  # divider
                        ft.PopupMenuItem(
                            text="Checked item", checked=False, on_click=check_item_clicked
                        ),
                    ]
                ),
            ],
        )

        if page.route == "/":
            v = await MainView(page)
        elif str(page.route).startswith("/players"):
            v = await PlayerView(page)

        v.controls.insert(0, appbar)
        page.views.append(v)


        await page.update_async()



    page.on_route_change = route_change
    await page.go_async("/")

ft.app(main, view=ft.AppView.WEB_BROWSER, port=8090, web_renderer=ft.WebRenderer.HTML)