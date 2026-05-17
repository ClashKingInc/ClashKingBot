package main

import (
	"context"
	"fmt"
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

	"clashking/background"
	"clashking/commands"
	"clashking/utility"
)

var (
	token       string
	newCommands []discord.ApplicationCommandCreate
	guildID, _  = snowflake.Parse("1315502785831374848")
)

func main() {
	background.StartClanTracking()

}
func rest() {

	if err := godotenv.Load(); err != nil {
		slog.Warn("no .env file loaded", slog.Any("err", err))
	}
	token = os.Getenv("BOT_TOKEN")
	slog.Info("starting example...")
	slog.Info("disgo version", slog.String("version", disgo.Version))

	clanCommands := commands.ClanCommands{}
	r := handler.New()
	r.Use(middleware.Logger)
	r.Group(func(r handler.Router) {
		r.Use(middleware.Print("group2")) //command logs
		r.SlashCommand("/clan", clanCommands.Handle)
		r.Component("/button1/{data}", clanCommands.Components)
	})
	r.NotFound(commands.CommandUtils.HandleNotFound)

	client, err := disgo.New(token,
		bot.WithDefaultGateway(),
		bot.WithEventListeners(r),
	)
	if err != nil {
		slog.Error("error while building bot", slog.Any("err", err))
		return
	}

	newCommands = append(newCommands, clanCommands.Commands()...)

	emojis := utility.LoadEmojiConfig(client)
	fmt.Println(emojis)
	if err = handler.SyncCommands(client, newCommands, []snowflake.ID{}); err != nil {
		slog.Error("error while syncing commands", slog.Any("err", err))
		return
	}

	defer client.Close(context.TODO())

	if err = client.OpenGateway(context.TODO()); err != nil {
		slog.Error("error while connecting to gateway", slog.Any("err", err))
	}

	slog.Info("example is now running. Press CTRL-C to exit.")
	s := make(chan os.Signal, 1)
	signal.Notify(s, syscall.SIGINT, syscall.SIGTERM, os.Interrupt)
	<-s
}
