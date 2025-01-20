class ClashKingException(Exception):
    pass


class RosterAliasAlreadyExists(ClashKingException):
    pass


class RosterDoesNotExist(ClashKingException):
    pass


class PlayerAlreadyInRoster(ClashKingException):
    def __str__(self):
        return 'Already in Roster'


class PlayerNotInRoster(ClashKingException):
    pass


class RosterSizeLimit(ClashKingException):
    def __str__(self):
        return 'Roster Size Limit Hit'


class ExpiredComponents(ClashKingException):
    pass


class PanelNotFound(ClashKingException):
    pass


class ButtonNotFound(ClashKingException):
    pass


class ButtonAlreadyExists(ClashKingException):
    pass


class PanelAlreadyExists(ClashKingException):
    pass


class FaultyJson(ClashKingException):
    pass


class MissingWebhookPerms(ClashKingException):
    pass


class NoLinkedAccounts(ClashKingException):
    pass


class PlayerNotFound(ClashKingException):
    pass


class InvalidHexCode(ClashKingException):
    pass


class InvalidGuildID(ClashKingException):
    pass


class ExportTemplateAlreadyExists(ClashKingException):
    pass


class NoRosterRoles(ClashKingException):
    pass


class NotValidReminderTime(ClashKingException):
    pass


class NoLegendStatsFound(ClashKingException):
    pass


class PlayerNotInLegends(ClashKingException):
    pass


class APITokenRequired(ClashKingException):
    pass


class InvalidAPIToken(ClashKingException):
    pass


class ThingNotFound(ClashKingException):
    def __init__(self, message):
        super().__init__(message)


class MessageException(ClashKingException):
    def __init__(self, message):
        super().__init__(message)
