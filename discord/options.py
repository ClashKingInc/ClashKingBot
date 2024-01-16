from disnake.ext import commands

from discord import autocomplete, convert

optional_clan = commands.Param(default=None, converter=convert.clan, autocomplete=autocomplete.clan, description="Input a clan tag or choose an option from the autocomplete")
clan = commands.Param(converter=convert.clan, autocomplete=autocomplete.clan, description="Input a clan tag or choose an option from the autocomplete")

optional_season = commands.Param(default=None, converter=convert.season, autocomplete=autocomplete.season)
season = commands.Param(converter=convert.season, autocomplete=autocomplete.season)

