package commands

import (
	"github.com/disgoorg/disgo/discord"
	"github.com/disgoorg/disgo/handler"
)

type command_utils struct{}

var CommandUtils = &command_utils{}

func (h *command_utils) HandleNotFound(event *handler.InteractionEvent) error {
	return event.CreateMessage(discord.MessageCreate{Content: "not found"})
}
