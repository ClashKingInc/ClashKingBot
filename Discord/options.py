from disnake.ext import commands

from Discord import autocomplete, convert

optional_clan = commands.Param(default=None, converter=convert.clan, autocomplete=autocomplete.clan, description="An in-game clan")
clan = commands.Param(converter=convert.clan, autocomplete=autocomplete.clan, description="An in-game clan")

optional_season = commands.Param(default=None, converter=convert.season, autocomplete=autocomplete.season)
season = commands.Param(converter=convert.season, autocomplete=autocomplete.season)

