import flet as ft
from .clients import coc_client
from Assets.thPicDictionary import thDictionary

async def PlayerView(page:ft.Page):
    page.title = "player"
    tag = page.route.split("/")[-1]
    player = await coc_client.get_player(player_tag=tag)


    def generate_chart():
        data_1 = [
            ft.LineChartData(
                data_points=[
                    ft.LineChartDataPoint(1, 1),
                    ft.LineChartDataPoint(3, 1.5),
                    ft.LineChartDataPoint(5, 1.4),
                    ft.LineChartDataPoint(7, 3.4),
                    ft.LineChartDataPoint(10, 2),
                    ft.LineChartDataPoint(12, 2.2),
                    ft.LineChartDataPoint(13, 1.8),
                ],
                stroke_width=8,
                color=ft.colors.LIGHT_GREEN,
                curved=True,
                stroke_cap_round=True,
            )]
        return data_1


    return ft.View(
        "/players",
        controls=[
            ft.Column([
                ft.Row([ft.Image(src=thDictionary(player.town_hall)), ft.Text(f"{player.name} | {player.tag}")]),
                ft.Row([ft.Text(f"Donations: {player.donations}")]),
                ft.LineChart(data_series=[
                    ft.LineChartData(
                        data_points=[
                            ft.LineChartDataPoint(1, 1),
                            ft.LineChartDataPoint(3, 1.5),
                            ft.LineChartDataPoint(5, 1.4),
                            ft.LineChartDataPoint(7, 3.4),
                            ft.LineChartDataPoint(10, 2),
                            ft.LineChartDataPoint(12, 2.2),
                            ft.LineChartDataPoint(13, 1.8),
                        ],
                        stroke_width=8,
                        color=ft.colors.LIGHT_GREEN,
                        curved=True,
                        stroke_cap_round=True,
                    )])
            ])
        ]
    )
