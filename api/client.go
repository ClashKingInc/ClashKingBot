package api

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
)

const baseURL = "http://localhost:8000"
const version = "v2"
const fullUrl = baseURL + "/" + version

type apiClient struct{}

var ClashKingClient = &apiClient{}

func (c *apiClient) GetClanBoard(clan_tag string) ClanBoard {
	resp, _ := http.Get(fullUrl + "/clan/" + clan_tag + "/board")
	defer resp.Body.Close()

	var board ClanBoard
	body, _ := io.ReadAll(resp.Body)
	_ = json.Unmarshal(body, &board)
	fmt.Println(board)
	return board
}
