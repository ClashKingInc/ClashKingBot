package api

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"

	"github.com/disgoorg/snowflake/v2"
)

type apiClient struct {
	token    string
	botToken string
	baseURL  string
	httpClient *http.Client
}

var ClashKingClient = &apiClient{httpClient: &http.Client{}}

func (c *apiClient) Init(token string) {
	c.botToken = token
	c.token = token
	// Allow a separate API token (e.g. for local dev where API expects a different token).
	if apiToken := os.Getenv("API_TOKEN"); apiToken != "" {
		c.token = apiToken
	}
	c.baseURL = os.Getenv("API_URL")
	if c.baseURL == "" {
		c.baseURL = "https://go.api.clashk.ing"
	}
}

func (c *apiClient) get(url string) (*http.Response, error) {
	req, err := http.NewRequest(http.MethodGet, url, nil)
	if err != nil {
		return nil, err
	}
	if c.token != "" {
		req.Header.Set("Authorization", "Bearer "+c.token)
	}
	return c.httpClient.Do(req)
}

// PostDiscordMessage posts raw JSON payload to a Discord channel using the bot token.
// This handles all message formats including Components V2 (flags: 32768).
func (c *apiClient) PostDiscordMessage(channelID snowflake.ID, payload json.RawMessage) error {
	url := fmt.Sprintf("https://discord.com/api/v10/channels/%s/messages", channelID)
	req, err := http.NewRequest(http.MethodPost, url, bytes.NewReader(payload))
	if err != nil {
		return err
	}
	req.Header.Set("Authorization", "Bot "+c.botToken)
	req.Header.Set("Content-Type", "application/json")
	resp, err := c.httpClient.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	if resp.StatusCode >= 400 {
		body, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("discord API error %d: %s", resp.StatusCode, body)
	}
	return nil
}

func (c *apiClient) GetClanBoard(clanTag string) ClanBoard {
	resp, err := c.get(c.baseURL + "/v2/clan/" + clanTag + "/board")
	if err != nil {
		fmt.Println(err)
		return ClanBoard{}
	}
	defer resp.Body.Close()

	var board ClanBoard
	body, _ := io.ReadAll(resp.Body)
	_ = json.Unmarshal(body, &board)
	fmt.Println(board)
	return board
}
