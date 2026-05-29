package commands

import (
	"fmt"
	"strings"
	"time"

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
	_, err = event.CreateFollowupMessage(discord.MessageCreate{
		Embeds: []discord.Embed{playerLookupEmbed(player)},
	})
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
	_, err = event.CreateFollowupMessage(discord.MessageCreate{
		Embeds: []discord.Embed{playerStatsEmbed(player)},
	})
	return err
}

// ─── Embed builders ───────────────────────────────────────────────────────────

func playerLookupEmbed(player *api.PlayerExtended) discord.Embed {
	e := utility.Emojis.IconEmojis

	thEm := thEmoji(player.TownHallLevel)
	leagueEm := ""
	if em, ok := utility.Emojis.LeagueEmojis[player.League.Name]; ok {
		leagueEm = em.Mention() + " "
	}

	clanName := "—"
	clanTag := ""
	if player.Clan != nil {
		clanName = player.Clan.Name
		clanTag = player.Clan.Tag
	}

	roleStr := roleLabel(player.Role)
	warPref := "—"
	if player.WarPreference == "in" {
		warPref = e.OptIn.Mention() + " Opted In"
	} else if player.WarPreference == "out" {
		warPref = e.OptOut.Mention() + " Opted Out"
	}

	lastOnlineStr := "—"
	if player.LastOnline != nil {
		t := time.Unix(*player.LastOnline, 0)
		lastOnlineStr = "<t:" + fmt.Sprint(*player.LastOnline) + ":R>"
		_ = t
	}

	activityStr := "—"
	if player.Activity != nil {
		activityStr = fmt.Sprintf("%d days active", *player.Activity)
	}

	b := discord.NewEmbedBuilder().
		SetTitle(fmt.Sprintf("%s %s | XP %d", thEm, player.Name, player.ExpLevel)).
		SetDescription(fmt.Sprintf("%s**%s**\n%s `%s`",
			leagueEm, player.League.Name,
			e.Trophy.Mention(), fmt.Sprint(player.Trophies),
		)).
		SetColor(playerEmbedColor).
		AddField(e.ClanCastle.Mention()+" Clan", fmt.Sprintf("%s\n`%s`", clanName, clanTag), true).
		AddField(e.People.Mention()+" Role", roleStr, true).
		AddField(e.ClashSword.Mention()+" War Preference", warPref, true).
		AddField(e.Trophy.Mention()+" Trophies", formatNum(player.Trophies), true).
		AddField(e.WarStar.Mention()+" War Stars", formatNum(player.WarStars), true).
		AddField(e.BrokenSword.Mention()+" Attack Wins", formatNum(player.AttackWins), true).
		AddField(e.HandCoins.Mention()+" Donations", formatNum(player.Donations), true).
		AddField(e.Troop.Mention()+" Received", formatNum(player.DonationsReceived), true)

	if player.Activity != nil || player.LastOnline != nil {
		b.AddField(e.Clock.Mention()+" Last Seen", lastOnlineStr, true).
			AddField(e.Calendar.Mention()+" Activity", activityStr, true)
	}

	if player.BuilderBaseTrophies != nil {
		b.AddField(e.VersusTrophy.Mention()+" Builder Trophies", formatNum(*player.BuilderBaseTrophies), true)
	}

	b.SetFooter(player.Tag, "")
	return b.Build()
}

func playerStatsEmbed(player *api.PlayerExtended) discord.Embed {
	e := utility.Emojis.IconEmojis
	thEm := thEmoji(player.TownHallLevel)

	var lines []string
	lines = append(lines, fmt.Sprintf("%s **TH%d** | XP %d | %s %d 🏆",
		thEm, player.TownHallLevel, player.ExpLevel,
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

	return discord.NewEmbedBuilder().
		SetTitle(fmt.Sprintf("%s — Stats", player.Name)).
		SetDescription(strings.Join(lines, "\n")).
		SetColor(playerEmbedColor).
		SetFooter(player.Tag, "").
		Build()
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
