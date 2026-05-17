package commands

import (
	"encoding/json"
	"strings"

	"clashking/api"

	"github.com/disgoorg/disgo/discord"
	"github.com/disgoorg/disgo/handler"
	"github.com/disgoorg/snowflake/v2"
)

type EmbedCommands struct{}

func (e *EmbedCommands) Commands() []discord.ApplicationCommandCreate {
	return []discord.ApplicationCommandCreate{
		discord.SlashCommandCreate{
			Name:        "embed",
			Description: "Manage and post embeds",
			Options: []discord.ApplicationCommandOption{
				discord.ApplicationCommandOptionSubCommand{
					Name:        "post",
					Description: "Post a saved embed to a channel",
					Options: []discord.ApplicationCommandOption{
						discord.ApplicationCommandOptionString{
							Name:         "name",
							Description:  "Name of the embed to post",
							Required:     true,
							Autocomplete: true,
						},
						discord.ApplicationCommandOptionChannel{
							Name:         "channel",
							Description:  "Channel to post the embed in (defaults to current channel)",
							Required:     false,
							ChannelTypes: []discord.ChannelType{discord.ChannelTypeGuildText},
						},
					},
				},
			},
		},
	}
}

func (e *EmbedCommands) HandlePost(data discord.SlashCommandInteractionData, event *handler.CommandEvent) error {
	if event.GuildID() == nil {
		return event.CreateMessage(discord.NewMessageCreateBuilder().
			SetContent("This command can only be used in a server.").
			SetEphemeral(true).Build())
	}
	guildID := *event.GuildID()

	if err := event.DeferCreateMessage(true); err != nil {
		return err
	}

	embedName := data.String("name")

	channelID := data.Snowflake("channel")
	if channelID == snowflake.ID(0) {
		channelID = event.Channel().ID()
	}

	embeds, err := api.ClashKingClient.GetServerEmbeds(guildID)
	if err != nil {
		_, _ = event.UpdateInteractionResponse(discord.NewMessageUpdateBuilder().SetContent("❌ Failed to fetch embeds.").Build())
		return err
	}

	var found *api.ServerEmbed
	for i := range embeds {
		if embeds[i].Name == embedName {
			found = &embeds[i]
			break
		}
	}

	if found == nil {
		_, err = event.UpdateInteractionResponse(discord.NewMessageUpdateBuilder().SetContent("❌ Embed not found.").Build())
		return err
	}

	msgJSON, err := discohookToRawMessage(found.Data)
	if err != nil {
		_, _ = event.UpdateInteractionResponse(discord.NewMessageUpdateBuilder().SetContent("❌ Failed to parse embed data.").Build())
		return err
	}

	if err = api.ClashKingClient.PostDiscordMessage(channelID, msgJSON); err != nil {
		_, _ = event.UpdateInteractionResponse(discord.NewMessageUpdateBuilder().SetContent("❌ Failed to post embed: " + err.Error()).Build())
		return err
	}

	_, err = event.UpdateInteractionResponse(discord.NewMessageUpdateBuilder().SetContent("✅ Embed posted!").Build())
	return err
}

func (e *EmbedCommands) AutocompletePost(event *handler.AutocompleteEvent) error {
	if event.GuildID() == nil {
		return event.AutocompleteResult(nil)
	}
	guildID := *event.GuildID()

	focused := event.Data.Focused()
	if focused.Name != "name" {
		return event.AutocompleteResult(nil)
	}

	query := ""
	var rawStr string
	if err := json.Unmarshal(focused.Value, &rawStr); err == nil {
		query = strings.ToLower(rawStr)
	}

	embeds, err := api.ClashKingClient.GetServerEmbeds(guildID)
	if err != nil {
		return event.AutocompleteResult(nil)
	}

	choices := make([]discord.AutocompleteChoice, 0, 25)
	for _, embed := range embeds {
		if query == "" || strings.Contains(strings.ToLower(embed.Name), query) {
			choices = append(choices, discord.AutocompleteChoiceString{
				Name:  embed.Name,
				Value: embed.Name,
			})
		}
		if len(choices) >= 25 {
			break
		}
	}
	return event.AutocompleteResult(choices)
}

// discohookToRawMessage extracts the first message payload from a Discohook data map
// and returns raw JSON ready to POST to Discord's REST API.
// Handles both classic embeds and Components V2 (flags: 32768) formats.
func discohookToRawMessage(data map[string]any) (json.RawMessage, error) {
	var msgData map[string]any

	if msgs, ok := data["messages"].([]any); ok && len(msgs) > 0 {
		if msg0, ok := msgs[0].(map[string]any); ok {
			if d, ok := msg0["data"].(map[string]any); ok {
				msgData = d
			}
		}
	}

	if msgData == nil {
		// Fall back to top-level content + embeds for older/simpler payloads.
		msgData = map[string]any{}
		if c, ok := data["content"].(string); ok && c != "" {
			msgData["content"] = c
		}
		if e, ok := data["embeds"]; ok {
			msgData["embeds"] = e
		}
	}

	// Normalize components before sending to Discord.
	if components, ok := msgData["components"].([]any); ok {
		msgData["components"] = normalizeComponents(components)
	}

	raw, err := json.Marshal(msgData)
	return raw, err
}

// normalizeComponents fixes Components V2 data for Discord's API:
//   - Buttons (type 2) without a label get label: " " (Discord requires it)
//   - File components (type 13) with external URLs are removed (Discord forbids them in bot messages)
func normalizeComponents(components []any) []any {
	result := make([]any, 0, len(components))
	for _, raw := range components {
		c, ok := raw.(map[string]any)
		if !ok {
			result = append(result, raw)
			continue
		}

		cType, _ := c["type"].(float64)

		// Remove file components with external URLs.
		if int(cType) == 13 {
			continue
		}

		// Recurse into nested components (action rows, containers).
		if nested, ok := c["components"].([]any); ok {
			c["components"] = normalizeComponents(nested)
		}

		// Fix buttons missing a label.
		if int(cType) == 2 {
			if _, hasLabel := c["label"]; !hasLabel {
				c["label"] = "\u200b"
			}
		}

		// Fix button accessories inside sections (type 9).
		if int(cType) == 9 {
			if acc, ok := c["accessory"].(map[string]any); ok {
				accType, _ := acc["type"].(float64)
				if int(accType) == 2 {
					if _, hasLabel := acc["label"]; !hasLabel {
						acc["label"] = "\u200b"
					}
				}
			}
		}

		result = append(result, c)
	}
	return result
}

