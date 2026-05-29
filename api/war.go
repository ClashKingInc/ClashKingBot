package api

// WarAttack is a single attack in a war.
type WarAttack struct {
	AttackerTag          string  `json:"attackerTag"`
	DefenderTag          string  `json:"defenderTag"`
	Stars                int     `json:"stars"`
	DestructionPercentage float64 `json:"destructionPercentage"`
	Order                int     `json:"order"`
	Duration             int     `json:"duration"`
}

// WarMember is a participating member in a clan war.
type WarMember struct {
	Tag              string      `json:"tag"`
	Name             string      `json:"name"`
	TownhallLevel    int         `json:"townhallLevel"`
	MapPosition      int         `json:"mapPosition"`
	Attacks          []WarAttack `json:"attacks"`
}

// WarClan is one side (clan or opponent) in a war.
type WarClan struct {
	Tag                   string      `json:"tag"`
	Name                  string      `json:"name"`
	BadgeURLs             BadgeURLs   `json:"badgeUrls"`
	ClanLevel             int         `json:"clanLevel"`
	Attacks               int         `json:"attacks"`
	Stars                 int         `json:"stars"`
	DestructionPercentage float64     `json:"destructionPercentage"`
	Members               []WarMember `json:"members"`
}

// War is a single war record as stored in MongoDB / returned by the CoC API.
type War struct {
	State                string  `json:"state"`
	TeamSize             int     `json:"teamSize"`
	AttacksPerMember     int     `json:"attacksPerMember"`
	PreparationStartTime string  `json:"preparationStartTime"`
	StartTime            string  `json:"startTime"`
	EndTime              string  `json:"endTime"`
	Clan                 WarClan `json:"clan"`
	Opponent             WarClan `json:"opponent"`
	Season               *string `json:"season"` // set for CWL wars
}

// WarPreviousResponse is the envelope from GET /v2/war/:tag/previous.
type WarPreviousResponse struct {
	Items []War `json:"items"`
}
