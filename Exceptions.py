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