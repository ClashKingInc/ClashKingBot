package api

import (
	"encoding/json"
	"fmt"
	"io"
	"log/slog"
	"net/http"

	"github.com/disgoorg/snowflake/v2"
)

// ServerEmbed is an embed stored in the database for a guild.
type ServerEmbed struct {
	Name string         `json:"name"`
	Data map[string]any `json:"data"`
}

type serverEmbedsResponse struct {
	Items []ServerEmbed `json:"items"`
	Total int           `json:"total"`
}

// GetServerEmbeds fetches all custom embeds configured for a guild.
func (c *apiClient) GetServerEmbeds(guildID snowflake.ID) ([]ServerEmbed, error) {
	url := fmt.Sprintf("%s/v2/server/%s/embeds", c.baseURL, guildID)
	slog.Info("GetServerEmbeds", slog.String("url", url))

	resp, err := c.get(url)
	if err != nil {
		slog.Error("GetServerEmbeds request failed", slog.Any("err", err))
		return nil, err
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}

	slog.Info("GetServerEmbeds response", slog.Int("status", resp.StatusCode), slog.String("body", string(body)))

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("API returned status %d: %s", resp.StatusCode, string(body))
	}

	var result serverEmbedsResponse
	if err := json.Unmarshal(body, &result); err != nil {
		return nil, err
	}
	return result.Items, nil
}
