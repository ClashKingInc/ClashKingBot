from ..Clan.utils import clan_composition, basic_clan_board, detailed_clan_board, hero_progress
from ..Family.utils import family_composition


def get_function(name: str):
    table = {
        "clan compo" : clan_composition,
        "clan board basic" : basic_clan_board,
        "clan board detailed" : detailed_clan_board,
        "clan progress hero" : hero_progress,

        "family compo" : family_composition
    }
    return table.get(name)