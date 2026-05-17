package commands

import (
	"fmt"

	"clashking/api"
	"clashking/utility"

	"github.com/disgoorg/disgo/discord"
	"github.com/disgoorg/disgo/handler"
)

type ClanCommands struct{}

func (c *ClanCommands) Commands() []discord.ApplicationCommandCreate {
	return []discord.ApplicationCommandCreate{
		discord.SlashCommandCreate{
			Name:        "clan",
			Description: "Look up a clan",
			Options: []discord.ApplicationCommandOption{
				discord.ApplicationCommandOptionString{
					Name:        "tag",
					Description: "a clan tag as found in game",
					Required:    true,
				},
			},
		},
	}
}

func (c *ClanCommands) Handle(data discord.SlashCommandInteractionData, event *handler.CommandEvent) error {
	clan_tag := data.Options["tag"]
	fmt.Println(clan_tag.String())
	board_data := api.ClashKingClient.GetClanBoard(clan_tag.String())
	fmt.Println(board_data)
	return event.CreateMessage(discord.MessageCreate{
		Content: fmt.Sprintf("You looked up %s clan tag", clan_tag),
		Embeds: []discord.Embed{
			{
				Title:       board_data.Name,
				Description: utility.Emojis.IconEmojis.ClanCastle.Mention(),
				Thumbnail: &discord.EmbedResource{
					URL: board_data.Badge,
				},
			},
		},
		Components: []discord.LayoutComponent{
			discord.NewActionRow(
				discord.NewPrimaryButton("button1", "/button1/testData"),
			),
		},
	})
}

func (c *ClanCommands) Components(event *handler.ComponentEvent) error {
	data := event.Vars["data"]
	return event.CreateMessage(discord.MessageCreate{Content: "component: " + data})
}
