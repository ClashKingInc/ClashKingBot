package api

// PlayerLeague represents the player's current league.
type PlayerLeague struct {
	ID       int      `json:"id"`
	Name     string   `json:"name"`
	IconURLs IconURLs `json:"iconUrls"`
}

// PlayerClan is the slim clan reference embedded in a player document.
type PlayerClan struct {
	Tag      string    `json:"tag"`
	Name     string    `json:"name"`
	BadgeURLs BadgeURLs `json:"badgeUrls"`
}

// PlayerExtended is the response from GET /v2/player/:tag/extended.
// It merges the live CoC API player object with tracked stats from MongoDB.
type PlayerExtended struct {
	// CoC API fields
	Tag                     string        `json:"tag"`
	Name                    string        `json:"name"`
	TownHallLevel           int           `json:"townHallLevel"`
	TownHallWeaponLevel     *int          `json:"townHallWeaponLevel"`
	ExpLevel                int           `json:"expLevel"`
	Trophies                int           `json:"trophies"`
	BestTrophies            int           `json:"bestTrophies"`
	WarStars                int           `json:"warStars"`
	AttackWins              int           `json:"attackWins"`
	DefenseWins             int           `json:"defenseWins"`
	BuilderHallLevel        *int          `json:"builderHallLevel"`
	BuilderBaseTrophies     *int          `json:"builderBaseTrophies"`
	BestBuilderBaseTrophies *int          `json:"bestBuilderBaseTrophies"`
	Role                    string        `json:"role"`
	WarPreference           string        `json:"warPreference"`
	Donations               int           `json:"donations"`
	DonationsReceived       int           `json:"donationsReceived"`
	League                  PlayerLeague  `json:"league"`
	Clan                    *PlayerClan   `json:"clan"`

	// Tracked stats (snake_case from MongoDB merge)
	Activity   *int   `json:"activity"`
	LastOnline *int64 `json:"last_online"`
}

// PlayerSortedItem is a single row from POST /v2/players/sorted/:attribute.
type PlayerSortedItem struct {
	Name  string         `json:"name"`
	Tag   string         `json:"tag"`
	Value any            `json:"value"`
	Clan  map[string]any `json:"clan"`
}

// PlayerSortedResponse is the envelope returned by POST /v2/players/sorted/:attribute.
type PlayerSortedResponse struct {
	Items []PlayerSortedItem `json:"items"`
}
