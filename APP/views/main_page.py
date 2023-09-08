import flet as ft
from flet_route import Params,Basket
from .clients import player_search
SUPER_SCRIPTS=["⁰","¹","²","³","⁴","⁵","⁶", "⁷","⁸", "⁹"]
from Assets.thPicDictionary import thDictionary

def create_superscript(num):
    digits = [int(num) for num in str(num)]
    new_num = ""
    for d in digits:
        new_num += SUPER_SCRIPTS[d]

    return new_num

async def search_name_with_tag(query):
    names = []
    if query == "":
        pipeline = [
            {"$limit": 25}]
    else:
        pipeline= [
            {
            "$search": {
                "index": "player_search",
                "autocomplete": {
                    "query": query,
                    "path": "name",
                },
            }
            },
            {"$limit": 25}
        ]
    results = await player_search.aggregate(pipeline=pipeline).to_list(length=None)
    for document in results:
        league = document.get("league")
        if league == "Unknown":
            league = "Unranked"
        league = league.replace(" League", "")
        names.append((f'{create_superscript(document.get("th"))}{document.get("name")} ({league})' + " | " + document.get("tag"), document.get("th")))
    return names



class SearchBar(ft.UserControl):
    def __init__(self, page):
        super().__init__()
        self.page = page

    def printer(self, tag):
        self.page.go(f"/players/{tag}")

    async def textbox_changed(self, string):
        NAMES = await search_name_with_tag(query=string.control.value)
        list_items = {
            name: ft.ListTile(
                height=45,
                title=ft.Text(name, size=14),
                leading=ft.Image(
                    src=thDictionary(th),
                    fit=ft.ImageFit.CONTAIN),
                on_click=self.printer(name.split("| ")[-1]),
                expand=True
            )
            for name, th in NAMES
        }
        self.list_view.controls = [list_items.get(n) for n, th in NAMES][:10]
        await self.update_async()


    def build(self):
        self.list_view = ft.ListView(expand=1, spacing=5, padding=5)
        row = ft.Column(
            [
                ft.Container(
                    content=ft.TextField(label="Search:", on_change=self.textbox_changed, expand=True),
                    padding=3,
                    border_radius=2,
                ),
                ft.Container(
                    content=self.list_view,
                    padding=10,
                )
            ],
            alignment=ft.MainAxisAlignment.CENTER,
        )
        return row

async def MainView(page:ft.Page):
    page.title = "Main"

    async def open_settings(e):
        await page.go_async("/players/#2PP")

    padding = SearchBar(page)
    button = ft.ElevatedButton("Go to settings", on_click=open_settings)

    return ft.View(
        "/main",
        controls=[padding, button]
    )

