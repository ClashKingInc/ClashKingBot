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