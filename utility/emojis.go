package utility

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"strings"

	"github.com/disgoorg/disgo/bot"
	"github.com/disgoorg/disgo/discord"
	"github.com/disintegration/imaging"
	"github.com/mitchellh/mapstructure"
)

type IconEmojis struct {
	AnimatedClashSwords discord.Emoji `json:"animated_clash_swords"`
	Average             discord.Emoji `json:"average"`
	Back                discord.Emoji `json:"back"`
	Blank               discord.Emoji `json:"blank"`
	BrokenSword         discord.Emoji `json:"broken_sword"`
	BrownShield         discord.Emoji `json:"brown_shield"`
	Calendar            discord.Emoji `json:"calendar"`
	CapitalGold         discord.Emoji `json:"capital_gold"`
	CapitalTrophy       discord.Emoji `json:"capital_trophy"`
	ClanCastle          discord.Emoji `json:"clan_castle"`
	ClanGames           discord.Emoji `json:"clan_games"`
	ClashSword          discord.Emoji `json:"clash_sword"`
	Clock               discord.Emoji `json:"clock"`
	CWLMedal            discord.Emoji `json:"cwl_medal"`
	DarkElixir          discord.Emoji `json:"dark_elixir"`
	DiscordIcon         discord.Emoji `json:"discord"`
	DoubleUpArrow       discord.Emoji `json:"double_up_arrow"`
	DownRedArrow        discord.Emoji `json:"down_red_arrow"`
	Earth               discord.Emoji `json:"earth"`
	Elixir              discord.Emoji `json:"elixir"`
	EquipmentCommon     discord.Emoji `json:"equipment_common"`
	EquipmentEpic       discord.Emoji `json:"equipment_epic"`
	Excel               discord.Emoji `json:"excel"`
	Eye                 discord.Emoji `json:"eye"`
	Forward             discord.Emoji `json:"forward"`
	Gear                discord.Emoji `json:"gear"`
	Gold                discord.Emoji `json:"gold"`
	GreenCheck          discord.Emoji `json:"green_check"`
	GreenCircle         discord.Emoji `json:"green_circle"`
	GreyCircle          discord.Emoji `json:"grey_circle"`
	GreyDash            discord.Emoji `json:"grey_dash"`
	HandCoins           discord.Emoji `json:"hand_coins"`
	Hashmark            discord.Emoji `json:"hashmark"`
	Heart               discord.Emoji `json:"heart"`
	NoStar              discord.Emoji `json:"no_star"`
	OptIn               discord.Emoji `json:"opt_in"`
	OptOut              discord.Emoji `json:"opt_out"`
	People              discord.Emoji `json:"people"`
	PetPaw              discord.Emoji `json:"pet_paw"`
	Pin                 discord.Emoji `json:"pin"`
	RaidMedal           discord.Emoji `json:"raid_medal"`
	Ratio               discord.Emoji `json:"ratio"`
	RedCircle           discord.Emoji `json:"red_circle"`
	RedTick             discord.Emoji `json:"red_tick"`
	RedX                discord.Emoji `json:"red_x"`
	RedditIcon          discord.Emoji `json:"reddit_icon"`
	Refresh             discord.Emoji `json:"refresh"`
	Search              discord.Emoji `json:"search"`
	Shield              discord.Emoji `json:"shield"`
	Spells              discord.Emoji `json:"spells"`
	SquareSumBox        discord.Emoji `json:"square_sum_box"`
	SquareXDeny         discord.Emoji `json:"square_x_deny"`
	Terminal            discord.Emoji `json:"terminal"`
	ThickCapitalSword   discord.Emoji `json:"thick_capital_sword"`
	Time                discord.Emoji `json:"time"`
	ToggleOff           discord.Emoji `json:"toggle_off"`
	ToggleOn            discord.Emoji `json:"toggle_on"`
	Trashcan            discord.Emoji `json:"trashcan"`
	Troop               discord.Emoji `json:"troop"`
	Trophy              discord.Emoji `json:"trophy"`
	Unranked            discord.Emoji `json:"unranked"`
	UpGreenArrow        discord.Emoji `json:"up_green_arrow"`
	UserSearch          discord.Emoji `json:"user_search"`
	VersusTrophy        discord.Emoji `json:"versus_trophy"`
	WarStar             discord.Emoji `json:"war_star"`
	Warning             discord.Emoji `json:"warning"`
	WoodSwords          discord.Emoji `json:"wood_swords"`
	Wrench              discord.Emoji `json:"wrench"`
	XP                  discord.Emoji `json:"xp"`
}

type EmojiHolder struct {
	TownhallEmoji       map[string]discord.Emoji `json:"townhall_emojis"`
	SuperTroopEmoji     map[string]discord.Emoji `json:"super_troop_emojis"`
	PetEmoji            map[string]discord.Emoji `json:"pet_emojis"`
	HeroEquipment       map[string]discord.Emoji `json:"hero_equipment_emojis"`
	IconEmojis          IconEmojis               `json:"icon_emojis"`
	LeagueEmojis        map[string]discord.Emoji `json:"league_emojis"`
	TroopEmojis         map[string]discord.Emoji `json:"troop_emojis"`
	SpellEmojis         map[string]discord.Emoji `json:"spell_emojis"`
	BuilderLeagueEmojis map[string]discord.Emoji `json:"builder_league_emojis"`
	CWLLeagueEmojis     map[string]discord.Emoji `json:"cwl_league_emojis"`
	LeagueTierEmojis    map[string]discord.Emoji `json:"league_tier_emojis"`
	BlueNumbers         map[string]discord.Emoji `json:"blue_numbers"`
	GoldNumbers         map[string]discord.Emoji `json:"gold_numbers"`
}

var Emojis EmojiHolder

const assetsURL = "https://assets.clashk.ing"

func LoadEmojiConfig(client *bot.Client) EmojiHolder {
	resp, _ := http.Get("https://assets.clashk.ing/bot/emojis.json")
	defer resp.Body.Close()

	currentEmojis, _ := client.Rest.GetApplicationEmojis(client.ApplicationID)

	currentEmojisMap := make(map[string]discord.Emoji)
	for _, emoji := range currentEmojis {
		currentEmojisMap[emoji.Name] = emoji
	}

	var emojiConfig map[string]map[string]string
	_ = json.NewDecoder(resp.Body).Decode(&emojiConfig)

	emojiMap := make(map[string]map[string]discord.Emoji)
	validEmojiNames := make(map[string]bool)

	createEmoji := func(name string, url string) discord.Emoji {
		fmt.Println("Creating emoji: " + name)
		fmt.Println(url)
		resp, _ := http.Get(url)
		defer resp.Body.Close()

		img, _ := imaging.Decode(resp.Body)

		resized := imaging.Fit(img, 128, 128, imaging.Lanczos)
		var buf bytes.Buffer
		_ = imaging.Encode(&buf, resized, imaging.PNG)
		imgData := buf.Bytes()

		if len(imgData) == 0 {
			fmt.Println("%s produced empty data", name)
		}
		if len(imgData) > 256*1024 {
			fmt.Println("%s is %d bytes (>256KB)", name, len(imgData))
		}

		iconType := discord.IconTypePNG
		switch ct := resp.Header.Get("Content-Type"); {
		case strings.Contains(ct, "jpeg"):
			iconType = discord.IconTypeJPEG
		case strings.Contains(ct, "gif"):
			iconType = discord.IconTypeGIF
		}

		icon := discord.NewIconRaw(iconType, imgData)

		createdEmoji, err := client.Rest.CreateApplicationEmoji(client.ApplicationID, discord.EmojiCreate{
			Name:  name,
			Image: *icon,
		})
		fmt.Println(err)
		return *createdEmoji
	}

	for emojiType, typeEmojis := range emojiConfig {
		if _, ok := emojiMap[emojiType]; !ok {
			emojiMap[emojiType] = make(map[string]discord.Emoji)
		}
		for name, filePath := range typeEmojis {
			normalizer := func(s string) string {
				return strings.ToLower(
					strings.ReplaceAll(
						strings.ReplaceAll(s, " ", ""), ".", ""),
				)
			}

			switch emojiType {
			case "townhall_emojis":
				normalizer = func(s string) string {
					return fmt.Sprintf("th%s", s)
				}
			case "blue_numbers":
				normalizer = func(s string) string {
					return fmt.Sprintf("blue_%s", s)
				}
			case "gold_numbers":
				normalizer = func(s string) string {
					return fmt.Sprintf("gold_%s", s)
				}
			case "spell_emojis":
				normalizer = func(s string) string {
					return strings.ToLower(
						strings.ReplaceAll(
							strings.ReplaceAll(s, " ", ""), "spell", ""),
					)
				}
			}

			normalizedName := normalizer(name)
			if _, ok := currentEmojisMap[normalizedName]; !ok {
				emoji := createEmoji(normalizedName, assetsURL+filePath)
				emojiMap[emojiType][name] = emoji
			} else {
				emojiMap[emojiType][name] = currentEmojisMap[normalizedName]
			}
			validEmojiNames[normalizedName] = true
		}
	}

	for _, emoji := range currentEmojis {
		if _, ok := validEmojiNames[emoji.Name]; !ok {
			_ = client.Rest.DeleteApplicationEmoji(client.ApplicationID, emoji.ID)
		}
	}

	cfg := &mapstructure.DecoderConfig{
		TagName: "json",
		Result:  &Emojis,
	}
	dec, _ := mapstructure.NewDecoder(cfg)
	_ = dec.Decode(emojiMap)

	return Emojis
}
