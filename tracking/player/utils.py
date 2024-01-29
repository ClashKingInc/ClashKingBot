from msgspec import Struct
import pendulum as pend
from datetime import timedelta
import coc

def gen_raid_date():
    now = pend.now(tz=pend.UTC)
    current_dayofweek = now.weekday()
    if (current_dayofweek == 4 and now.hour >= 7) or (current_dayofweek == 5) or (current_dayofweek == 6) or (
            current_dayofweek == 0 and now.hour < 7):
        if current_dayofweek == 0:
            current_dayofweek = 7
        fallback = current_dayofweek - 4
        raidDate = (now - timedelta(fallback)).date()
        return str(raidDate)
    else:
        forward = 4 - current_dayofweek
        raidDate = (now + timedelta(forward)).date()
        return str(raidDate)

def gen_season_date():
    end = coc.utils.get_season_end().replace(tzinfo=pend.UTC).date()
    month = end.month
    if month <= 9:
        month = f"0{month}"
    return f"{end.year}-{month}"

def gen_legend_date():
    now = pend.now(tz=pend.UTC)
    hour = now.hour
    if hour < 5:
        date = (now - timedelta(1)).date()
    else:
        date = now.date()
    return str(date)

def gen_games_season():
    now = pend.now(tz=pend.UTC)
    month = now.month
    if month <= 9:
        month = f"0{month}"
    return f"{now.year}-{month}"

def get_player_changes(previous_response: dict, response: dict):
    new_json = {}
    fields_to_update = []
    ok_achievements = {"Gold Grab", "Elixir Escapade", "Heroic Heist", "Games Champion", "Aggressive Capitalism",
                       "Well Seasoned", "Nice and Tidy", "War League Legend", "Wall Buster"}
    for key, item in response.items():
        old_item = previous_response.get(key)
        if old_item != item:
            fields_to_update.append(key)
        not_ok_fields = {"labels", "legendStatistics", "playerHouse", "versusBattleWinCount"}
        if key in not_ok_fields:
            continue
        if old_item != item:
            if isinstance(item, list):
                for count, spot in enumerate(item):
                    spot_name = spot["name"]
                    if key == "achievements" and spot_name not in ok_achievements:
                        continue
                    old_ = next((item for item in old_item if item["name"] == spot_name), None)
                    if old_ != spot:
                        if key == "achievements":
                            if old_ is not None:
                                new_json[(key, spot_name.replace(".", ""))] = (old_["value"], spot["value"])
                            else:
                                new_json[(key, spot_name.replace(".", ""))] = (None, spot["value"])
                        else:
                            if old_ is not None:
                                new_json[(key, spot_name.replace(".", ""))] = (old_["level"], spot["level"])
                            else:
                                new_json[(key, spot_name.replace(".", ""))] = (None, spot["level"])
            else:
                if key == "clan":
                    new_json[(key, key)] = (None, {"tag": item["tag"], "name": item["name"]})
                elif key == "league":
                    new_json[(key, key)] = (None, {"tag": item["id"], "name": item["name"]})
                else:
                    new_json[(key, key)] = (old_item, item)

    return (new_json, fields_to_update)


class Player(Struct):
    tag: str