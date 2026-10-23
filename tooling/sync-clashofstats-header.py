"""Copy only the authorized legacy service header to private local config."""
import json
import os
from pathlib import Path
from dotenv import dotenv_values, set_key
from pymongo import MongoClient

source = dotenv_values('/Users/matthewanderson/GolandProjects/clashking_schemas/.env')
workspace = Path('/Users/matthewanderson/ClashKing/.clashking')
target = workspace / 'local.env'
if dotenv_values(target).get('DISCORD_CLIENT_ID') != '808566437199216691':
    raise RuntimeError('Expected local Beta workspace')
with MongoClient(source['STATIC_MONGODB'], serverSelectionTimeoutMS=10000) as client:
    row = client['bot']['settings'].find_one(
        {'clashofstats_user_agent': {'$exists': True}},
        {'_id': 0, 'clashofstats_user_agent': 1},
    )
header = (row or {}).get('clashofstats_user_agent')
if not isinstance(header, str) or not header or '\n' in header or '\r' in header:
    raise RuntimeError('Missing or invalid configured header')
for destination in [target, workspace / 'state' / 'bot.env']:
    if not destination.is_file():
        raise RuntimeError('Expected existing private local environment file')
    set_key(destination, 'CLASHOFSTATS_USER_AGENT', header, quote_mode='always')
    os.chmod(destination, 0o600)
print(json.dumps({'headerConfigured': True, 'scope': 'local Beta only'}))
