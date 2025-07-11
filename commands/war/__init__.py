import hikari
import lightbulb

from .war_stats import WarStats

loader = lightbulb.Loader()
group = lightbulb.Group(
    name='war',
    description='command-war-description',
    default_member_permissions=hikari.Permissions.MANAGE_GUILD,
    localize=True,
)

group.register(WarStats)

loader.command(group)
