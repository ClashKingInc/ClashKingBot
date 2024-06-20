import disnake
from disnake.ext import commands

from discord import autocomplete, convert


optional_clan = commands.Param(
    default=None,
    converter=convert.clan,
    autocomplete=autocomplete.clan,
    description=disnake.Localized(key='clan-autocomplete-description'),
)
clan = commands.Param(
    converter=convert.clan,
    autocomplete=autocomplete.clan,
    description=disnake.Localized(key='clan-autocomplete-description'),
)

optional_season = commands.Param(default=None, converter=convert.season, autocomplete=autocomplete.season)
season = commands.Param(converter=convert.season, autocomplete=autocomplete.season)

optional_family = commands.Param(converter=convert.server, default=None, autocomplete=autocomplete.server)
