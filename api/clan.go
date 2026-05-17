package api

type Location struct {
	Emoji string `json:"emoji"`
	Name  string `json:"name"`
}

type Ranking struct {
	World   int `json:"world"`
	Country int `json:"country"`
}

type ClanBoardSeasonStats struct {
	Month       string `json:"month"`
	Tracked     bool   `json:"tracked"`
	ClanGames   int    `json:"clan_games"`
	AttackWins  int    `json:"attack_wins"`
	Donations   int    `json:"donations"`
	Received    int    `json:"received"`
	ActiveDaily int    `json:"active_daily"`
}

type TownhallComp struct {
	Level int `json:"level"`
	Count int `json:"count"`
}

type ClanBoard struct {
	Name                string               `json:"name"`
	Tag                 string               `json:"tag"`
	Link                string               `json:"link"`
	Badge               string               `json:"badge"`
	Trophies            int                  `json:"trophies"`
	BuilderTrophies     int                  `json:"builder_trophies"`
	RequiredTownhall    int                  `json:"required_townhall"`
	Type                string               `json:"type"`
	Location            Location             `json:"location"`
	Ranking             Ranking              `json:"ranking"`
	Leader              string               `json:"leader"`
	Level               int                  `json:"level"`
	MemberCount         int                  `json:"member_count"`
	CWLLeague           string               `json:"cwl_league"`
	WarWins             int                  `json:"war_wins"`
	WarsLost            *int                 `json:"wars_lost"`
	WinStreak           *int                 `json:"win_streak"`
	WinRatio            *float64             `json:"win_ratio"`
	CapitalLeague       string               `json:"capital_league"`
	CapitalPoints       int                  `json:"capital_points"`
	CapitalHall         int                  `json:"capital_hall"`
	Description         string               `json:"description"`
	Season              ClanBoardSeasonStats `json:"season"`
	TownhallComposition []TownhallComp       `json:"townhall_composition"`
}
