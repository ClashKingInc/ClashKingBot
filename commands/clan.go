package commands

import (
	"fmt"
	"sort"
	"strconv"
	"strings"
	"time"

	"clashking/api"
	"clashking/utility"

	"github.com/disgoorg/disgo/discord"
	"github.com/disgoorg/disgo/handler"
)

const clanEmbedColor = 0xF0B429 // Gold

var (
	minOne        = 1
	maxFifty      = 50
	maxTwentyFive = 25
	maxFifteen    = 15
)

// ClanCommands handles all /clan subcommands.
type ClanCommands struct{}

// Commands returns the full /clan slash command definition.
func (c *ClanCommands) Commands() []discord.ApplicationCommandCreate {
	return []discord.ApplicationCommandCreate{
		discord.SlashCommandCreate{
			Name:        "clan",
			Description: "Clan commands",
			Options: []discord.ApplicationCommandOption{
				discord.ApplicationCommandOptionSubCommand{
					Name:        "overview",
					Description: "View a clan's profile and key stats",
					Options: []discord.ApplicationCommandOption{
						discord.ApplicationCommandOptionString{
							Name: "tag", Description: "Clan tag (e.g. #2PP)", Required: true,
						},
					},
				},
				discord.ApplicationCommandOptionSubCommand{
					Name:        "compo",
					Description: "View the clan's member composition",
					Options: []discord.ApplicationCommandOption{
						discord.ApplicationCommandOptionString{
							Name: "tag", Description: "Clan tag", Required: true,
						},
						discord.ApplicationCommandOptionString{
							Name:        "type",
							Description: "Breakdown type (default: Town Hall)",
							Choices: []discord.ApplicationCommandOptionChoiceString{
								{Name: "Town Hall (default)", Value: "Townhall"},
								{Name: "Role", Value: "Role"},
								{Name: "League", Value: "League"},
							},
						},
					},
				},
				discord.ApplicationCommandOptionSubCommand{
					Name:        "members",
					Description: "View clan members sorted by a stat",
					Options: []discord.ApplicationCommandOption{
						discord.ApplicationCommandOptionString{
							Name: "tag", Description: "Clan tag", Required: true,
						},
						discord.ApplicationCommandOptionString{
							Name:        "sort_by",
							Description: "Stat to sort by (default: Trophies)",
							Choices: []discord.ApplicationCommandOptionChoiceString{
								{Name: "Trophies (default)", Value: "trophies"},
								{Name: "Town Hall", Value: "townhall"},
								{Name: "Donations", Value: "donations"},
								{Name: "Donations Received", Value: "donations_received"},
							},
						},
						discord.ApplicationCommandOptionInt{
							Name:        "limit",
							Description: "Max members to show (1–50, default 50)",
							MinValue:    &minOne,
							MaxValue:    &maxFifty,
						},
					},
				},
				discord.ApplicationCommandOptionSubCommand{
					Name:        "donations",
					Description: "View the donation leaderboard for a clan",
					Options: []discord.ApplicationCommandOption{
						discord.ApplicationCommandOptionString{
							Name: "tag", Description: "Clan tag", Required: true,
						},
						discord.ApplicationCommandOptionString{
							Name:        "season",
							Description: "Season (e.g. 2025-05 — defaults to current)",
						},
					},
				},
				discord.ApplicationCommandOptionSubCommand{
					Name:        "war-history",
					Description: "View a clan's previous wars",
					Options: []discord.ApplicationCommandOption{
						discord.ApplicationCommandOptionString{
							Name: "tag", Description: "Clan tag", Required: true,
						},
						discord.ApplicationCommandOptionString{
							Name:        "type",
							Description: "War type to include",
							Choices: []discord.ApplicationCommandOptionChoiceString{
								{Name: "Regular Wars (default)", Value: "wars"},
								{Name: "All (incl. CWL)", Value: "all"},
							},
						},
						discord.ApplicationCommandOptionInt{
							Name:        "limit",
							Description: "Number of wars to show (1–25, default 10)",
							MinValue:    &minOne,
							MaxValue:    &maxTwentyFive,
						},
					},
				},
				discord.ApplicationCommandOptionSubCommand{
					Name:        "games",
					Description: "View the clan games leaderboard",
					Options: []discord.ApplicationCommandOption{
						discord.ApplicationCommandOptionString{
							Name: "tag", Description: "Clan tag", Required: true,
						},
						discord.ApplicationCommandOptionString{
							Name: "season", Description: "Season (e.g. 2025-05 — defaults to current)",
						},
					},
				},
				discord.ApplicationCommandOptionSubCommand{
					Name:        "capital",
					Description: "View clan capital overview",
					Options: []discord.ApplicationCommandOption{
						discord.ApplicationCommandOptionString{
							Name: "tag", Description: "Clan tag", Required: true,
						},
					},
				},
				discord.ApplicationCommandOptionSubCommand{
					Name:        "progress",
					Description: "View member upgrade progress",
					Options: []discord.ApplicationCommandOption{
						discord.ApplicationCommandOptionString{
							Name: "tag", Description: "Clan tag", Required: true,
						},
						discord.ApplicationCommandOptionString{
							Name:        "type",
							Description: "Progress type (default: Heroes)",
							Choices: []discord.ApplicationCommandOptionChoiceString{
								{Name: "Heroes (default)", Value: "heroes"},
								{Name: "Troops", Value: "troops"},
								{Name: "Pets", Value: "pets"},
							},
						},
					},
				},
				discord.ApplicationCommandOptionSubCommand{
					Name:        "war-opt",
					Description: "View member war opt-in/opt-out status",
					Options: []discord.ApplicationCommandOption{
						discord.ApplicationCommandOptionString{
							Name: "tag", Description: "Clan tag", Required: true,
						},
					},
				},
				discord.ApplicationCommandOptionSubCommand{
					Name:        "activity",
					Description: "View clan activity board",
					Options: []discord.ApplicationCommandOption{
						discord.ApplicationCommandOptionString{
							Name: "tag", Description: "Clan tag", Required: true,
						},
					},
				},
				discord.ApplicationCommandOptionSubCommand{
					Name:        "summary",
					Description: "View a season summary for top clan members",
					Options: []discord.ApplicationCommandOption{
						discord.ApplicationCommandOptionString{
							Name: "tag", Description: "Clan tag", Required: true,
						},
						discord.ApplicationCommandOptionString{
							Name: "season", Description: "Season (e.g. 2025-05 — defaults to current)",
						},
						discord.ApplicationCommandOptionInt{
							Name:        "limit",
							Description: "Members to include (1–15, default 10)",
							MinValue:    &minOne,
							MaxValue:    &maxFifteen,
						},
					},
				},
			},
		},
	}
}

// ─── Subcommand handlers ──────────────────────────────────────────────────────

func (c *ClanCommands) HandleOverview(data discord.SlashCommandInteractionData, event *handler.CommandEvent) error {
	tag := data.String("tag")
	if err := event.DeferCreateMessage(false); err != nil {
		return err
	}
	clan, err := api.ClashKingClient.GetClanDetails(tag)
	if err != nil {
		_, err = event.CreateFollowupMessage(errMsg("Clan not found", "Could not find a clan with tag `"+tag+"`."))
		return err
	}
	_, err = event.CreateFollowupMessage(discord.MessageCreate{
		Embeds: []discord.Embed{clanOverviewEmbed(clan)},
	})
	return err
}

func (c *ClanCommands) HandleCompo(data discord.SlashCommandInteractionData, event *handler.CommandEvent) error {
	tag := data.String("tag")
	compoType := "Townhall"
	if t, ok := data.OptString("type"); ok {
		compoType = t
	}
	if err := event.DeferCreateMessage(false); err != nil {
		return err
	}
	clan, err := api.ClashKingClient.GetClanDetails(tag)
	if err != nil {
		_, err = event.CreateFollowupMessage(errMsg("Clan not found", "Could not find a clan with tag `"+tag+"`."))
		return err
	}
	_, err = event.CreateFollowupMessage(discord.MessageCreate{
		Embeds: []discord.Embed{clanCompoEmbed(clan, compoType)},
	})
	return err
}

func (c *ClanCommands) HandleMembers(data discord.SlashCommandInteractionData, event *handler.CommandEvent) error {
	tag := data.String("tag")
	sortBy := "trophies"
	if s, ok := data.OptString("sort_by"); ok {
		sortBy = s
	}
	limit := 50
	if l, ok := data.OptInt("limit"); ok {
		limit = l
	}
	if err := event.DeferCreateMessage(false); err != nil {
		return err
	}
	clan, err := api.ClashKingClient.GetClanDetails(tag)
	if err != nil {
		_, err = event.CreateFollowupMessage(errMsg("Clan not found", "Could not find a clan with tag `"+tag+"`."))
		return err
	}
	_, err = event.CreateFollowupMessage(discord.MessageCreate{
		Embeds: []discord.Embed{clanMembersEmbed(clan, sortBy, limit)},
	})
	return err
}

func (c *ClanCommands) HandleDonations(data discord.SlashCommandInteractionData, event *handler.CommandEvent) error {
	tag := data.String("tag")
	season := currentSeason()
	if s, ok := data.OptString("season"); ok {
		season = s
	}
	if err := event.DeferCreateMessage(false); err != nil {
		return err
	}
	clan, err := api.ClashKingClient.GetClanDetails(tag)
	if err != nil {
		_, err = event.CreateFollowupMessage(errMsg("Clan not found", "Could not find a clan with tag `"+tag+"`."))
		return err
	}
	donations, err := api.ClashKingClient.GetClanDonations(tag, season)
	if err != nil || len(donations.Items) == 0 {
		_, err = event.CreateFollowupMessage(errMsg("No data", "No donation data found for this clan and season."))
		return err
	}
	_, err = event.CreateFollowupMessage(discord.MessageCreate{
		Embeds: []discord.Embed{clanDonationsEmbed(clan, donations, season)},
	})
	return err
}

func (c *ClanCommands) HandleWarHistory(data discord.SlashCommandInteractionData, event *handler.CommandEvent) error {
	tag := data.String("tag")
	includeCWL := false
	if t, ok := data.OptString("type"); ok && t == "all" {
		includeCWL = true
	}
	limit := 10
	if l, ok := data.OptInt("limit"); ok {
		limit = l
	}
	if err := event.DeferCreateMessage(false); err != nil {
		return err
	}
	wars, err := api.ClashKingClient.GetPreviousWars(tag, limit, includeCWL)
	if err != nil {
		_, err = event.CreateFollowupMessage(errMsg("Error", "Failed to fetch war history for `"+tag+"`."))
		return err
	}
	clanName := tag
	if clan, err2 := api.ClashKingClient.GetClanDetails(tag); err2 == nil {
		clanName = clan.Name
	}
	_, err = event.CreateFollowupMessage(discord.MessageCreate{
		Embeds: []discord.Embed{clanWarHistoryEmbed(clanName, api.FormatTag(tag), wars)},
	})
	return err
}

// The following subcommands are not yet implemented — they show a coming-soon embed.

func (c *ClanCommands) HandleGames(data discord.SlashCommandInteractionData, event *handler.CommandEvent) error {
	return event.CreateMessage(comingSoonMsg("/clan games"))
}

func (c *ClanCommands) HandleCapital(data discord.SlashCommandInteractionData, event *handler.CommandEvent) error {
	return event.CreateMessage(comingSoonMsg("/clan capital"))
}

func (c *ClanCommands) HandleProgress(data discord.SlashCommandInteractionData, event *handler.CommandEvent) error {
	return event.CreateMessage(comingSoonMsg("/clan progress"))
}

func (c *ClanCommands) HandleWarOpt(data discord.SlashCommandInteractionData, event *handler.CommandEvent) error {
	return event.CreateMessage(comingSoonMsg("/clan war-opt"))
}

func (c *ClanCommands) HandleActivity(data discord.SlashCommandInteractionData, event *handler.CommandEvent) error {
	return event.CreateMessage(comingSoonMsg("/clan activity"))
}

func (c *ClanCommands) HandleSummary(data discord.SlashCommandInteractionData, event *handler.CommandEvent) error {
	return event.CreateMessage(comingSoonMsg("/clan summary"))
}

// ─── Embed builders ───────────────────────────────────────────────────────────

func clanOverviewEmbed(clan *api.ClanDetails) discord.Embed {
	e := utility.Emojis.IconEmojis

	typeStr := clanTypeStr(clan.Type)
	warRecord := "Private"
	if clan.IsWarLogPublic {
		wins := clan.WarWins
		losses := 0
		ties := 0
		if clan.WarLosses != nil {
			losses = *clan.WarLosses
		}
		if clan.WarTies != nil {
			ties = *clan.WarTies
		}
		warRecord = fmt.Sprintf("%dW / %dD / %dL", wins, ties, losses)
		if clan.WarWinStreak > 0 {
			warRecord += fmt.Sprintf(" | 🔥 %d streak", clan.WarWinStreak)
		}
	}

	location := clan.Location.Name
	if location == "" {
		location = "—"
	}
	description := clan.Description
	if description == "" {
		description = "*No description*"
	}

	b := discord.NewEmbedBuilder().
		SetTitle(fmt.Sprintf("%s | Level %d", clan.Name, clan.ClanLevel)).
		SetThumbnail(clan.BadgeURLs.Large).
		SetDescription(description).
		SetColor(clanEmbedColor).
		AddField(e.People.Mention()+" Members", fmt.Sprintf("%d/50", clan.Members), true).
		AddField(e.Trophy.Mention()+" Trophies", formatNum(clan.ClanPoints), true).
		AddField(e.Earth.Mention()+" Location", location, true).
		AddField(e.ClanCastle.Mention()+" Required TH", fmt.Sprintf("TH %d", clan.RequiredTownhallLevel), true).
		AddField(e.CWLMedal.Mention()+" War League", orDash(clan.WarLeague.Name), true).
		AddField(e.CapitalTrophy.Mention()+" Capital League", orDash(clan.CapitalLeague.Name), true).
		AddField(e.ClashSword.Mention()+" War Record", warRecord, true).
		AddField(e.CapitalGold.Mention()+" Capital Points", formatNum(clan.ClanCapitalPoints), true).
		AddField(e.GreenCircle.Mention()+" Type", typeStr, true).
		SetFooter(clan.Tag, "")

	if clan.ClanCapital.CapitalHallLevel > 0 {
		b.AddField(e.ThickCapitalSword.Mention()+" Capital Hall", fmt.Sprintf("Level %d", clan.ClanCapital.CapitalHallLevel), true)
	}

	return b.Build()
}

func clanCompoEmbed(clan *api.ClanDetails, compoType string) discord.Embed {
	var title, body string

	switch compoType {
	case "Role":
		title = fmt.Sprintf("%s — Role Composition", clan.Name)
		counts := map[string]int{}
		for _, m := range clan.MemberList {
			counts[m.Role]++
		}
		roleOrder := []string{"leader", "coLeader", "elder", "member"}
		roleLabels := map[string]string{
			"leader":   "👑 Leader",
			"coLeader": "🔱 Co-Leader",
			"elder":    "⚜️ Elder",
			"member":   "👤 Member",
		}
		var lines []string
		for _, r := range roleOrder {
			if n, ok := counts[r]; ok {
				lines = append(lines, fmt.Sprintf("%-15s `%d`", roleLabels[r], n))
			}
		}
		body = strings.Join(lines, "\n")

	case "League":
		title = fmt.Sprintf("%s — League Composition", clan.Name)
		counts := map[string]int{}
		for _, m := range clan.MemberList {
			name := m.League.Name
			if name == "" {
				name = "Unranked"
			}
			counts[name]++
		}
		type pair struct {
			name  string
			count int
		}
		var pairs []pair
		for k, v := range counts {
			pairs = append(pairs, pair{k, v})
		}
		sort.Slice(pairs, func(i, j int) bool { return pairs[i].count > pairs[j].count })
		var lines []string
		for _, p := range pairs {
			em := leagueEmoji(p.name)
			lines = append(lines, fmt.Sprintf("%s %-25s `%d`", em, p.name, p.count))
		}
		body = strings.Join(lines, "\n")

	default: // Townhall
		title = fmt.Sprintf("%s — TH Composition", clan.Name)
		counts := map[int]int{}
		for _, m := range clan.MemberList {
			counts[m.TownHallLevel]++
		}
		var levels []int
		for k := range counts {
			levels = append(levels, k)
		}
		sort.Sort(sort.Reverse(sort.IntSlice(levels)))
		total := len(clan.MemberList)
		var lines []string
		for _, lvl := range levels {
			n := counts[lvl]
			pct := 0
			if total > 0 {
				pct = n * 100 / total
			}
			em := thEmoji(lvl)
			bar := progressBar(n, total, 10)
			lines = append(lines, fmt.Sprintf("%s TH%-2d  %s `%d` (%d%%)", em, lvl, bar, n, pct))
		}
		body = strings.Join(lines, "\n")
	}

	return discord.NewEmbedBuilder().
		SetTitle(title).
		SetThumbnail(clan.BadgeURLs.Large).
		SetDescription(body).
		SetColor(clanEmbedColor).
		SetFooter(clan.Tag, "").
		Build()
}

func clanMembersEmbed(clan *api.ClanDetails, sortBy string, limit int) discord.Embed {
	members := make([]api.ClanMember, len(clan.MemberList))
	copy(members, clan.MemberList)

	switch sortBy {
	case "townhall":
		sort.Slice(members, func(i, j int) bool {
			if members[i].TownHallLevel != members[j].TownHallLevel {
				return members[i].TownHallLevel > members[j].TownHallLevel
			}
			return members[i].Trophies > members[j].Trophies
		})
	case "donations":
		sort.Slice(members, func(i, j int) bool { return members[i].Donations > members[j].Donations })
	case "donations_received":
		sort.Slice(members, func(i, j int) bool {
			return members[i].DonationsReceived > members[j].DonationsReceived
		})
	default: // trophies
		sort.Slice(members, func(i, j int) bool { return members[i].Trophies > members[j].Trophies })
	}

	if limit > len(members) {
		limit = len(members)
	}
	members = members[:limit]

	sortLabels := map[string]string{
		"trophies":           "🏆 Trophies",
		"townhall":           "🏰 Town Hall",
		"donations":          "🎁 Donations",
		"donations_received": "📥 Received",
	}
	sortLabel := sortLabels[sortBy]

	var lines []string
	for i, m := range members {
		em := thEmoji(m.TownHallLevel)
		var value string
		switch sortBy {
		case "donations":
			value = fmt.Sprintf("`%d donated`", m.Donations)
		case "donations_received":
			value = fmt.Sprintf("`%d received`", m.DonationsReceived)
		case "townhall":
			value = fmt.Sprintf("`TH%d | %d 🏆`", m.TownHallLevel, m.Trophies)
		default:
			value = fmt.Sprintf("`%d 🏆`", m.Trophies)
		}
		lines = append(lines, fmt.Sprintf("`%2d.` %s %-22s %s", i+1, em, truncate(m.Name, 20), value))
	}

	return discord.NewEmbedBuilder().
		SetTitle(fmt.Sprintf("%s — Members by %s", clan.Name, sortLabel)).
		SetThumbnail(clan.BadgeURLs.Large).
		SetDescription(strings.Join(lines, "\n")).
		SetColor(clanEmbedColor).
		SetFooter(fmt.Sprintf("%s • %d/%d members shown", clan.Tag, limit, clan.Members), "").
		Build()
}

func clanDonationsEmbed(clan *api.ClanDetails, donations *api.DonationResponse, season string) discord.Embed {
	names := map[string]string{}
	for _, m := range clan.MemberList {
		names[m.Tag] = m.Name
	}

	type entry struct {
		name     string
		donated  int
		received int
	}

	var entries []entry
	for _, d := range donations.Items {
		donated := toInt(d.Donated)
		received := toInt(d.Received)
		if donated == 0 && received == 0 {
			continue
		}
		name := names[d.Tag]
		if name == "" {
			name = d.Tag
		}
		entries = append(entries, entry{name, donated, received})
	}
	sort.Slice(entries, func(i, j int) bool { return entries[i].donated > entries[j].donated })

	if len(entries) == 0 {
		return errEmbed("No donation data", "No donations tracked for season "+season+".")
	}

	limit := 20
	if len(entries) < limit {
		limit = len(entries)
	}

	e := utility.Emojis.IconEmojis
	var lines []string
	lines = append(lines, fmt.Sprintf("`   %-20s %6s %6s`", "Name", "Given", "Rcvd"))
	for i, en := range entries[:limit] {
		lines = append(lines, fmt.Sprintf("`%2d.` %-20s %s`%5d` %s`%5d`",
			i+1, truncate(en.name, 20),
			e.HandCoins.Mention(), en.donated,
			e.Troop.Mention(), en.received,
		))
	}

	return discord.NewEmbedBuilder().
		SetTitle(fmt.Sprintf("%s — Donations (%s)", clan.Name, season)).
		SetThumbnail(clan.BadgeURLs.Large).
		SetDescription(strings.Join(lines, "\n")).
		SetColor(clanEmbedColor).
		SetFooter(fmt.Sprintf("%s • top %d of %d donors", clan.Tag, limit, len(entries)), "").
		Build()
}

func clanWarHistoryEmbed(clanName, clanTag string, wars *api.WarPreviousResponse) discord.Embed {
	normalTag := strings.ReplaceAll(clanTag, "%23", "#")

	if len(wars.Items) == 0 {
		return errEmbed("No wars found", "No war history available, or the war log is private.")
	}

	e := utility.Emojis.IconEmojis
	var lines []string
	shown := 0
	for _, war := range wars.Items {
		if shown >= 15 {
			break
		}
		our, opp := war.Clan, war.Opponent
		if !strings.EqualFold(our.Tag, normalTag) {
			our, opp = opp, our
		}
		_, resultEmoji := warResult(our, opp)
		date := parseWarDate(war.EndTime)
		cwlMark := ""
		if war.Season != nil {
			cwlMark = " `CWL`"
		}
		lines = append(lines, fmt.Sprintf(
			"%s **%s** vs **%s**%s\n%s %s ⭐ **%d** vs %d | `%dv%d`",
			resultEmoji,
			truncate(our.Name, 18), truncate(opp.Name, 18), cwlMark,
			e.Calendar.Mention(), date,
			our.Stars, opp.Stars,
			war.TeamSize, war.TeamSize,
		))
		shown++
	}

	return discord.NewEmbedBuilder().
		SetTitle(fmt.Sprintf("%s — War History", clanName)).
		SetDescription(strings.Join(lines, "\n\n")).
		SetColor(clanEmbedColor).
		SetFooter(fmt.Sprintf("%s • %d wars shown of %d", normalTag, shown, len(wars.Items)), "").
		Build()
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

func clanTypeStr(t string) string {
	switch t {
	case "open":
		return "🟢 Open"
	case "inviteOnly":
		return "🔵 Invite Only"
	case "closed":
		return "🔴 Closed"
	}
	return t
}

func warResult(our, opp api.WarClan) (string, string) {
	if our.Stars > opp.Stars {
		return "Win", "✅"
	}
	if our.Stars < opp.Stars {
		return "Loss", "❌"
	}
	if our.DestructionPercentage > opp.DestructionPercentage {
		return "Win", "✅"
	}
	if our.DestructionPercentage < opp.DestructionPercentage {
		return "Loss", "❌"
	}
	return "Draw", "🟡"
}

func parseWarDate(endTime string) string {
	if len(endTime) >= 8 {
		// CoC format: 20250520T180000.000Z
		return endTime[0:4] + "-" + endTime[4:6] + "-" + endTime[6:8]
	}
	return endTime
}

func currentSeason() string {
	now := time.Now().UTC()
	return fmt.Sprintf("%d-%02d", now.Year(), int(now.Month()))
}

func formatNum(n int) string {
	s := strconv.Itoa(n)
	if len(s) <= 3 {
		return s
	}
	var out []byte
	for i, ch := range s {
		if i > 0 && (len(s)-i)%3 == 0 {
			out = append(out, ',')
		}
		out = append(out, byte(ch))
	}
	return string(out)
}

func progressBar(value, max, width int) string {
	if max == 0 {
		return strings.Repeat("░", width)
	}
	filled := value * width / max
	return strings.Repeat("█", filled) + strings.Repeat("░", width-filled)
}

func truncate(s string, max int) string {
	runes := []rune(s)
	if len(runes) <= max {
		return s
	}
	return string(runes[:max-1]) + "…"
}

func orDash(s string) string {
	if s == "" {
		return "—"
	}
	return s
}

func toInt(v any) int {
	switch n := v.(type) {
	case int:
		return n
	case int64:
		return int(n)
	case float64:
		return int(n)
	case string:
		i, _ := strconv.Atoi(n)
		return i
	}
	return 0
}

func thEmoji(level int) string {
	key := strconv.Itoa(level)
	if em, ok := utility.Emojis.TownhallEmoji[key]; ok {
		return em.Mention()
	}
	return fmt.Sprintf("TH%d", level)
}

func leagueEmoji(name string) string {
	if em, ok := utility.Emojis.LeagueEmojis[name]; ok {
		return em.Mention()
	}
	return "🏅"
}

func errMsg(title, desc string) discord.MessageCreate {
	return discord.MessageCreate{Embeds: []discord.Embed{errEmbed(title, desc)}}
}

func errEmbed(title, desc string) discord.Embed {
	return discord.NewEmbedBuilder().
		SetTitle("❌ " + title).
		SetDescription(desc).
		SetColor(0xE74C3C).
		Build()
}

func comingSoonMsg(cmd string) discord.MessageCreate {
	embed := discord.NewEmbedBuilder().
		SetTitle("🚧 Coming Soon").
		SetDescription(fmt.Sprintf("`%s` is not yet available in the Go bot. Stay tuned!", cmd)).
		SetColor(0xF39C12).
		Build()
	return discord.MessageCreate{Embeds: []discord.Embed{embed}}
}
