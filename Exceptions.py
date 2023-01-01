class RosterAliasAlreadyExists(Exception):
    pass

class RosterDoesNotExist(Exception):
    pass

class PlayerAlreadyInRoster(Exception):
    pass

class PlayerNotInRoster(Exception):
    pass

class RosterSizeLimit(Exception):
    pass

class ExpiredComponents(Exception):
    pass