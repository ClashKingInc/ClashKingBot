package api

// ─── Shared primitives ────────────────────────────────────────────────────────

type BadgeURLs struct {
	Large  string `json:"large"`
	Medium string `json:"medium"`
	Small  string `json:"small"`
}

type IconURLs struct {
	Small  string `json:"small"`
	Medium string `json:"medium"`
	Tiny   string `json:"tiny"`
}

type League struct {
	ID       int      `json:"id"`
	Name     string   `json:"name"`
	IconURLs IconURLs `json:"iconUrls"`
}

type ClanLocation struct {
	ID          int    `json:"id"`
	Name        string `json:"name"`
	IsCountry   bool   `json:"isCountry"`
	CountryCode string `json:"countryCode"`
}

type ClanMember struct {
	Tag                 string `json:"tag"`
	Name                string `json:"name"`
	Role                string `json:"role"`
	TownHallLevel       int    `json:"townHallLevel"`
	ExpLevel            int    `json:"expLevel"`
	League              League `json:"league"`
	Trophies            int    `json:"trophies"`
	BuilderBaseTrophies int    `json:"builderBaseTrophies"`
	Donations           int    `json:"donations"`
	DonationsReceived   int    `json:"donationsReceived"`
	ClanRank            int    `json:"clanRank"`
	PreviousClanRank    int    `json:"previousClanRank"`
}

type District struct {
	ID                int    `json:"id"`
	Name              string `json:"name"`
	DistrictHallLevel int    `json:"districtHallLevel"`
}

type ClanCapital struct {
	CapitalHallLevel int        `json:"capitalHallLevel"`
	Districts        []District `json:"districts"`
}

type Label struct {
	ID       int      `json:"id"`
	Name     string   `json:"name"`
	IconURLs IconURLs `json:"iconUrls"`
}

// ─── ClanDetails ─────────────────────────────────────────────────────────────

// ClanDetails is the response from GET /v2/clan/:tag/details (live CoC API data).
type ClanDetails struct {
	Tag                         string       `json:"tag"`
	Name                        string       `json:"name"`
	Type                        string       `json:"type"`
	Description                 string       `json:"description"`
	BadgeURLs                   BadgeURLs    `json:"badgeUrls"`
	ClanLevel                   int          `json:"clanLevel"`
	ClanPoints                  int          `json:"clanPoints"`
	ClanBuilderBasePoints       int          `json:"clanBuilderBasePoints"`
	ClanCapitalPoints           int          `json:"clanCapitalPoints"`
	CapitalLeague               League       `json:"capitalLeague"`
	Location                    ClanLocation `json:"location"`
	RequiredTrophies            int          `json:"requiredTrophies"`
	RequiredBuilderBaseTrophies int          `json:"requiredBuilderBaseTrophies"`
	RequiredTownhallLevel       int          `json:"requiredTownhallLevel"`
	WarFrequency                string       `json:"warFrequency"`
	WarWinStreak                int          `json:"warWinStreak"`
	WarWins                     int          `json:"warWins"`
	WarTies                     *int         `json:"warTies"`
	WarLosses                   *int         `json:"warLosses"`
	IsWarLogPublic              bool         `json:"isWarLogPublic"`
	WarLeague                   League       `json:"warLeague"`
	Members                     int          `json:"members"`
	MemberList                  []ClanMember `json:"memberList"`
	ClanCapital                 ClanCapital  `json:"clanCapital"`
	Labels                      []Label      `json:"labels"`
}

// ─── Compositions ─────────────────────────────────────────────────────────────

// ClanComposition is the response from GET /v2/clan/compo.
type ClanComposition struct {
	Townhall     map[string]int `json:"townhall"`
	Role         map[string]int `json:"role"`
	League       map[string]int `json:"league"`
	TotalMembers int            `json:"total_members"`
	ClanCount    int            `json:"clan_count"`
}

// ─── Donations ────────────────────────────────────────────────────────────────

type DonationItem struct {
	Tag      string `json:"tag"`
	Donated  any    `json:"donated"`
	Received any    `json:"received"`
}

type DonationResponse struct {
	Items []DonationItem `json:"items"`
}

// ─── Legacy structs (kept for existing code compatibility) ────────────────────

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
