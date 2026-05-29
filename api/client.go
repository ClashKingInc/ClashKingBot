package api

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"log/slog"
	"net/http"
	"strings"
	"time"
)

const baseURL = "https://go.api.clashk.ing"

var httpClient = &http.Client{Timeout: 10 * time.Second}

type apiClient struct{}

var ClashKingClient = &apiClient{}

func (c *apiClient) get(path string, out any) error {
	resp, err := httpClient.Get(baseURL + path)
	if err != nil {
		return fmt.Errorf("GET %s: %w", path, err)
	}
	defer resp.Body.Close()
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return err
	}
	if resp.StatusCode >= 400 {
		return fmt.Errorf("API %d: %s", resp.StatusCode, string(body))
	}
	return json.Unmarshal(body, out)
}

func (c *apiClient) post(path string, reqBody any, out any) error {
	data, err := json.Marshal(reqBody)
	if err != nil {
		return err
	}
	resp, err := httpClient.Post(baseURL+path, "application/json", bytes.NewReader(data))
	if err != nil {
		return fmt.Errorf("POST %s: %w", path, err)
	}
	defer resp.Body.Close()
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return err
	}
	if resp.StatusCode >= 400 {
		return fmt.Errorf("API %d: %s", resp.StatusCode, string(body))
	}
	return json.Unmarshal(body, out)
}

// FormatTag normalises a CoC tag (uppercase, leading #, URL-encoded for path use).
func FormatTag(tag string) string {
	tag = strings.TrimSpace(strings.ToUpper(tag))
	if !strings.HasPrefix(tag, "#") {
		tag = "#" + tag
	}
	return strings.ReplaceAll(tag, "#", "%23")
}

func (c *apiClient) GetClanDetails(tag string) (*ClanDetails, error) {
	var out ClanDetails
	err := c.get("/v2/clan/"+FormatTag(tag)+"/details", &out)
	return &out, err
}

func (c *apiClient) GetClanCompo(tags []string) (*ClanComposition, error) {
	parts := make([]string, len(tags))
	for i, t := range tags {
		parts[i] = "clan_tags=" + FormatTag(t)
	}
	var out ClanComposition
	err := c.get("/v2/clan/compo?"+strings.Join(parts, "&"), &out)
	return &out, err
}

func (c *apiClient) GetClanDonations(tag, season string) (*DonationResponse, error) {
	var out DonationResponse
	err := c.get("/v2/clan/"+FormatTag(tag)+"/donations/"+season, &out)
	return &out, err
}

func (c *apiClient) GetPreviousWars(tag string, limit int, includeCWL bool) (*WarPreviousResponse, error) {
	cwl := "false"
	if includeCWL {
		cwl = "true"
	}
	path := fmt.Sprintf("/v2/war/%s/previous?limit=%d&include_cwl=%s", FormatTag(tag), limit, cwl)
	var out WarPreviousResponse
	err := c.get(path, &out)
	return &out, err
}

func (c *apiClient) GetPlayerExtended(tag string) (*PlayerExtended, error) {
	var out PlayerExtended
	err := c.get("/v2/player/"+FormatTag(tag)+"/extended", &out)
	return &out, err
}

func (c *apiClient) GetPlayersSorted(attribute string, playerTags []string) (*PlayerSortedResponse, error) {
	body := map[string][]string{"player_tags": playerTags}
	var out PlayerSortedResponse
	err := c.post("/v2/players/sorted/"+attribute, body, &out)
	return &out, err
}

// GetClanBoard is kept for backward compatibility — prefer GetClanDetails.
//
// Deprecated: use GetClanDetails.
func (c *apiClient) GetClanBoard(tag string) ClanBoard {
	details, err := c.GetClanDetails(tag)
	if err != nil {
		slog.Warn("GetClanBoard fallback failed", slog.Any("err", err))
		return ClanBoard{}
	}
	badge := ""
	if details.BadgeURLs.Medium != "" {
		badge = details.BadgeURLs.Medium
	}
	return ClanBoard{
		Name:        details.Name,
		Tag:         details.Tag,
		Badge:       badge,
		Description: details.Description,
		Level:       details.ClanLevel,
		MemberCount: details.Members,
		Type:        details.Type,
	}
}
