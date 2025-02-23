import disnake
from classes.cocpy.clan import CustomClan
from disnake.ext import commands

from discord import autocomplete, convert


optional_clan = commands.Param(
    default=None,
    converter=convert.clan,
    autocomplete=autocomplete.clan,
    name=disnake.Localized(key='clan-autocomplete-name'),
    description=disnake.Localized(key='clan-autocomplete-description'),
)
clan: CustomClan = commands.Param(
    converter=convert.clan,
    autocomplete=autocomplete.clan,
    name=disnake.Localized(key='clan-autocomplete-name'),
    description=disnake.Localized(key='clan-autocomplete-description'),
)

family_player = commands.Param(
    name=disnake.Localized(key='player-autocomplete-name'),
    converter=convert.player,
    autocomplete=autocomplete.family_players,
    description=disnake.Localized(key='player-autocomplete-description'),
)

banned_player = commands.Param(
    name=disnake.Localized(key='player-autocomplete-name'),
    converter=convert.player,
    autocomplete=autocomplete.banned_players,
    description=disnake.Localized(key='player-autocomplete-description'),
)

optional_season = commands.Param(
    name=disnake.Localized(key='season-autocomplete-name'),
    description=disnake.Localized(key='season-autocomplete-description'),
    default=None,
    converter=convert.season,
    autocomplete=autocomplete.season
)
season = commands.Param(
    name=disnake.Localized(key='season-autocomplete-name'),
    description=disnake.Localized(key='season-autocomplete-description'),
    converter=convert.season,
    autocomplete=autocomplete.season
)

optional_family = commands.Param(converter=convert.server, default=None, autocomplete=autocomplete.server)
