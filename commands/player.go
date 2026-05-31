package commands

import (
	"fmt"
	"strings"

	"clashking/api"
	"clashking/utility"

	"github.com/disgoorg/disgo/discord"
	"github.com/disgoorg/disgo/handler"
)

const playerEmbedColor = 0x3498DB // Blue

// PlayerCommands handles all /player subcommands.
type PlayerCommands struct{}

// Commands returns the full /player slash command definition.
func (p *PlayerCommands) Commands() []discord.ApplicationCommandCreate {
	return []discord.ApplicationCommandCreate{
		discord.SlashCommandCreate{
			Name:        "player",
			Description: "Player commands",
			Options: []discord.ApplicationCommandOption{
				discord.ApplicationCommandOptionSubCommand{
					Name:        "lookup",
					Description: "Look up a player's profile and stats",
					Options: []discord.ApplicationCommandOption{
						discord.ApplicationCommandOptionString{
							Name:        "tag",
							Description: "Player tag (e.g. #2PP)",
							Required:    true,
						},
					},
				},
				discord.ApplicationCommandOptionSubCommand{
					Name:        "accounts",
					Description: "View accounts linked to a Discord user",
					Options: []discord.ApplicationCommandOption{
						discord.ApplicationCommandOptionUser{
							Name:        "user",
							Description: "Discord user (defaults to yourself)",
						},
					},
				},
				discord.ApplicationCommandOptionSubCommand{
					Name:        "todo",
					Description: "View upgrade to-do list for a player",
					Options: []discord.ApplicationCommandOption{
						discord.ApplicationCommandOptionString{
							Name:        "tag",
							Description: "Player tag (e.g. #2PP)",
							Required:    true,
						},
					},
				},
				discord.ApplicationCommandOptionSubCommand{
					Name:        "war-stats",
					Description: "View war statistics for a player",
					Options: []discord.ApplicationCommandOption{
						discord.ApplicationCommandOptionString{
							Name:        "tag",
							Description: "Player tag (e.g. #2PP)",
							Required:    true,
						},
					},
				},
				discord.ApplicationCommandOptionSubCommand{
					Name:        "stats",
					Description: "View detailed stats for a player",
					Options: []discord.ApplicationCommandOption{
						discord.ApplicationCommandOptionString{
							Name:        "tag",
							Description: "Player tag (e.g. #2PP)",
							Required:    true,
						},
					},
				},
			},
		},
	}
}

// ─── Subcommand handlers ──────────────────────────────────────────────────────

func (p *PlayerCommands) HandleLookup(data discord.SlashCommandInteractionData, event *handler.CommandEvent) error {
	tag := data.String("tag")
	if err := event.DeferCreateMessage(false); err != nil {
		return err
	}
	player, err := api.ClashKingClient.GetPlayerExtended(tag)
	if err != nil {
		_, err = event.CreateFollowupMessage(errMsg("Player not found", "Could not find a player with tag `"+tag+"`."))
		return err
	}
	_, err = event.CreateFollowupMessage(playerLookupMsg(player))
	return err
}

func (p *PlayerCommands) HandleAccounts(data discord.SlashCommandInteractionData, event *handler.CommandEvent) error {
	return event.CreateMessage(comingSoonMsg("/player accounts"))
}

func (p *PlayerCommands) HandleTodo(data discord.SlashCommandInteractionData, event *handler.CommandEvent) error {
	return event.CreateMessage(comingSoonMsg("/player todo"))
}

func (p *PlayerCommands) HandleWarStats(data discord.SlashCommandInteractionData, event *handler.CommandEvent) error {
	return event.CreateMessage(comingSoonMsg("/player war-stats"))
}

func (p *PlayerCommands) HandleStats(data discord.SlashCommandInteractionData, event *handler.CommandEvent) error {
	tag := data.String("tag")
	if err := event.DeferCreateMessage(false); err != nil {
		return err
	}
	player, err := api.ClashKingClient.GetPlayerExtended(tag)
	if err != nil {
		_, err = event.CreateFollowupMessage(errMsg("Player not found", "Could not find a player with tag `"+tag+"`."))
		return err
	}
	_, err = event.CreateFollowupMessage(playerStatsMsg(player))
	return err
}

// ─── Message builders ─────────────────────────────────────────────────────────

func playerLookupMsg(player *api.PlayerExtended) discord.MessageCreate {
	e := utility.Emojis.IconEmojis

	leagueName := player.League.Name
	if leagueName == "" {
		leagueName = "Unranked"
	}
	leagueEm := leagueEmoji(leagueName)

	clanLine := "—"
	if player.Clan != nil {
		clanLine = fmt.Sprintf("%s `%s`", player.Clan.Name, player.Clan.Tag)
	}

	warPref := "—"
	switch player.WarPreference {
	case "in":
		warPref = e.OptIn.Mention() + " Opted In"
	case "out":
		warPref = e.OptOut.Mention() + " Opted Out"
	}

	header := fmt.Sprintf("### %s %s | XP %d\n%s %s  ·  %s %s",
		thEmoji(player.TownHallLevel), player.Name, player.ExpLevel,
		leagueEm, leagueName,
		e.Trophy.Mention(), formatNum(player.Trophies),
	)
	row1 := fmt.Sprintf("%s **Clan:** %s  ·  %s **Role:** %s  ·  %s **War Pref:** %s",
		e.ClanCastle.Mention(), clanLine,
		e.People.Mention(), roleLabel(player.Role),
		e.ClashSword.Mention(), warPref,
	)
	row2 := fmt.Sprintf("%s **War Stars:** %s  ·  %s **Attack Wins:** %s  ·  %s **Defense Wins:** %s",
		e.WarStar.Mention(), formatNum(player.WarStars),
		e.BrokenSword.Mention(), formatNum(player.AttackWins),
		e.ClashSword.Mention(), formatNum(player.DefenseWins),
	)
	row3 := fmt.Sprintf("%s **Donations:** %s given  ·  %s **Received:** %s",
		e.HandCoins.Mention(), formatNum(player.Donations),
		e.Troop.Mention(), formatNum(player.DonationsReceived),
	)

	comps := []discord.ContainerSubComponent{
		discord.NewSection(
			discord.NewTextDisplay(header),
		).WithAccessory(discord.NewThumbnail(player.League.IconURLs.Medium)),
		discord.NewSmallSeparator(),
		discord.NewTextDisplay(row1),
		discord.NewTextDisplay(row2),
		discord.NewTextDisplay(row3),
	}

	if player.BuilderBaseTrophies != nil {
		comps = append(comps, discord.NewTextDisplay(fmt.Sprintf(
			"%s **Builder Trophies:** %s",
			e.VersusTrophy.Mention(), formatNum(*player.BuilderBaseTrophies),
		)))
	}

	if player.Activity != nil || player.LastOnline != nil {
		lastSeen := "—"
		if player.LastOnline != nil {
			lastSeen = fmt.Sprintf("<t:%d:R>", *player.LastOnline)
		}
		activity := "—"
		if player.Activity != nil {
			activity = fmt.Sprintf("%d days active", *player.Activity)
		}
		comps = append(comps, discord.NewTextDisplay(fmt.Sprintf(
			"%s **Last Seen:** %s  ·  %s **Activity:** %s",
			e.Clock.Mention(), lastSeen,
			e.Calendar.Mention(), activity,
		)))
	}

	comps = append(comps, discord.NewSmallSeparator(), discord.NewTextDisplay("-# "+player.Tag))

	return discord.NewMessageCreateV2(
		discord.NewContainer(comps...).WithAccentColor(playerEmbedColor),
	)
}

func playerStatsMsg(player *api.PlayerExtended) discord.MessageCreate {
	e := utility.Emojis.IconEmojis

	var lines []string
	lines = append(lines, fmt.Sprintf("%s **TH%d** | XP %d | %s %d 🏆",
		thEmoji(player.TownHallLevel), player.TownHallLevel, player.ExpLevel,
		e.Trophy.Mention(), player.Trophies,
	))
	lines = append(lines, "")
	lines = append(lines, fmt.Sprintf("%s Donations: `%d` given / `%d` received",
		e.HandCoins.Mention(), player.Donations, player.DonationsReceived,
	))
	lines = append(lines, fmt.Sprintf("%s War Stars: `%d` | Attack Wins: `%d` | Defense Wins: `%d`",
		e.WarStar.Mention(), player.WarStars, player.AttackWins, player.DefenseWins,
	))
	if player.BestTrophies > 0 {
		lines = append(lines, fmt.Sprintf("%s Best Trophies: `%d`",
			e.Trophy.Mention(), player.BestTrophies,
		))
	}
	if player.BuilderBaseTrophies != nil {
		lines = append(lines, fmt.Sprintf("%s Builder Trophies: `%d`",
			e.VersusTrophy.Mention(), *player.BuilderBaseTrophies,
		))
	}
	if player.Activity != nil {
		lines = append(lines, fmt.Sprintf("%s Activity: `%d` active days this season",
			e.Calendar.Mention(), *player.Activity,
		))
	}
	if player.LastOnline != nil {
		lines = append(lines, fmt.Sprintf("%s Last Seen: <t:%d:R>",
			e.Clock.Mention(), *player.LastOnline,
		))
	}

	return discord.NewMessageCreateV2(
		discord.NewContainer(
			discord.NewTextDisplay(fmt.Sprintf("**%s** — Stats", player.Name)),
			discord.NewSmallSeparator(),
			discord.NewTextDisplay(strings.Join(lines, "\n")),
			discord.NewSmallSeparator(),
			discord.NewTextDisplay("-# "+player.Tag),
		).WithAccentColor(playerEmbedColor),
	)
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

func roleLabel(role string) string {
	switch role {
	case "leader":
		return "👑 Leader"
	case "coLeader":
		return "🔱 Co-Leader"
	case "elder":
		return "⚜️ Elder"
	case "member":
		return "👤 Member"
	}
	return role
}
