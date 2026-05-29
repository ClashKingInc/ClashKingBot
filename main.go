package main

import (
	"context"
	"log/slog"
	"os"
	"os/signal"
	"syscall"

	"github.com/disgoorg/disgo"
	"github.com/disgoorg/disgo/bot"
	"github.com/disgoorg/disgo/discord"
	"github.com/disgoorg/disgo/handler"
	"github.com/disgoorg/disgo/handler/middleware"
	"github.com/disgoorg/snowflake/v2"
	"github.com/joho/godotenv"

	"clashking/commands"
	"clashking/utility"
)

func main() {
	if err := godotenv.Load(); err != nil {
		slog.Warn("no .env file loaded", slog.Any("err", err))
	}
	token := os.Getenv("BOT_TOKEN")
	if token == "" {
		slog.Error("BOT_TOKEN is not set")
		os.Exit(1)
	}

	slog.Info("starting ClashKing Go bot", slog.String("disgo_version", disgo.Version))

	clanCmds := &commands.ClanCommands{}
	playerCmds := &commands.PlayerCommands{}

	r := handler.New()
	r.Use(middleware.Logger)

	// /clan subcommands
	r.SlashCommand("/clan/overview", clanCmds.HandleOverview)
	r.SlashCommand("/clan/compo", clanCmds.HandleCompo)
	r.SlashCommand("/clan/members", clanCmds.HandleMembers)
	r.SlashCommand("/clan/donations", clanCmds.HandleDonations)
	r.SlashCommand("/clan/war-history", clanCmds.HandleWarHistory)
	r.SlashCommand("/clan/games", clanCmds.HandleGames)
	r.SlashCommand("/clan/capital", clanCmds.HandleCapital)
	r.SlashCommand("/clan/progress", clanCmds.HandleProgress)
	r.SlashCommand("/clan/war-opt", clanCmds.HandleWarOpt)
	r.SlashCommand("/clan/activity", clanCmds.HandleActivity)
	r.SlashCommand("/clan/summary", clanCmds.HandleSummary)

	// /player subcommands
	r.SlashCommand("/player/lookup", playerCmds.HandleLookup)
	r.SlashCommand("/player/accounts", playerCmds.HandleAccounts)
	r.SlashCommand("/player/todo", playerCmds.HandleTodo)
	r.SlashCommand("/player/war-stats", playerCmds.HandleWarStats)
	r.SlashCommand("/player/stats", playerCmds.HandleStats)

	r.NotFound(commands.CommandUtils.HandleNotFound)

	client, err := disgo.New(token,
		bot.WithDefaultGateway(),
		bot.WithEventListeners(r),
	)
	if err != nil {
		slog.Error("error creating bot client", slog.Any("err", err))
		os.Exit(1)
	}

	utility.LoadEmojiConfig(client)

	var allCommands []discord.ApplicationCommandCreate
	allCommands = append(allCommands, clanCmds.Commands()...)
	allCommands = append(allCommands, playerCmds.Commands()...)

	guildIDs := guildIDsFromEnv()
	if err = handler.SyncCommands(client, allCommands, guildIDs); err != nil {
		slog.Error("error syncing commands", slog.Any("err", err))
	}

	defer client.Close(context.TODO())

	if err = client.OpenGateway(context.TODO()); err != nil {
		slog.Error("error connecting to gateway", slog.Any("err", err))
		os.Exit(1)
	}

	slog.Info("bot is running — press CTRL-C to stop")
	s := make(chan os.Signal, 1)
	signal.Notify(s, syscall.SIGINT, syscall.SIGTERM, os.Interrupt)
	<-s
}

// guildIDsFromEnv returns a slice of guild IDs from the GUILD_ID env var (comma-separated).
// Returns an empty slice (global commands) if the var is not set.
func guildIDsFromEnv() []snowflake.ID {
	raw := os.Getenv("GUILD_ID")
	if raw == "" {
		return nil
	}
	id, err := snowflake.Parse(raw)
	if err != nil {
		slog.Warn("invalid GUILD_ID", slog.String("value", raw))
		return nil
	}
	return []snowflake.ID{id}
}
