class RosterAliasAlreadyExists(Exception):
    pass


class RosterDoesNotExist(Exception):
    pass


class PlayerAlreadyInRoster(Exception):
    def __str__(self):
        return "Already in Roster"


class PlayerNotInRoster(Exception):
    pass


class RosterSizeLimit(Exception):
    def __str__(self):
        return "Roster Size Limit Hit"


class ExpiredComponents(Exception):
    pass


class PanelNotFound(Exception):
    pass


class ButtonNotFound(Exception):
    pass


class ButtonAlreadyExists(Exception):
    pass


class PanelAlreadyExists(Exception):
    pass


class FaultyJson(Exception):
    pass


class MissingWebhookPerms(Exception):
    pass


class NoLinkedAccounts(Exception):
    pass


class PlayerNotFound(Exception):
    pass


class InvalidHexCode(Exception):
    pass


class InvalidGuildID(Exception):
    pass


class ExportTemplateAlreadyExists(Exception):
    pass


class NoRosterRoles(Exception):
    pass


class NotValidReminderTime(Exception):
    pass


class NoLegendStatsFound(Exception):
    pass


class PlayerNotInLegends(Exception):
    pass


class APITokenRequired(Exception):
    pass


class InvalidAPIToken(Exception):
    pass


class ThingNotFound(Exception):
    def __init__(self, message):
        super().__init__(message)


class MessageException(Exception):
    def __init__(self, message):
        super().__init__(message)
