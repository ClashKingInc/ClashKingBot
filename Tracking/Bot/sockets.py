import settings
from fastapi import WebSocket, Depends, Query, WebSocketDisconnect
from fastapi_jwt_auth import AuthJWT
from fastapi_jwt_auth.exceptions import AuthJWTException

async def clan_websocket(websocket: WebSocket, token: str = Query(...), Authorize: AuthJWT = Depends()):
    await websocket.accept()
    settings.CLAN_CLIENTS.add(websocket)
    try:
        '''Authorize.jwt_required("websocket", token=token)
        await websocket.send_text("Successfully Login!")
        decoded_token = Authorize.get_raw_jwt(token)
        await websocket.send_text(f"Here your decoded token: {decoded_token}")'''
        try:
            while True:
                data = await websocket.receive_text()
        except WebSocketDisconnect:
            settings.CLAN_CLIENTS.remove(websocket)
    except AuthJWTException as err:
        await websocket.send_text(err.message)
        await websocket.close()

async def war_websocket(websocket: WebSocket, token: str = Query(...), Authorize: AuthJWT = Depends()):
    await websocket.accept()
    settings.WAR_CLIENTS.add(websocket)
    try:
        '''Authorize.jwt_required("websocket", token=token)
        await websocket.send_text("Successfully Login!")
        decoded_token = Authorize.get_raw_jwt(token)
        await websocket.send_text(f"Here your decoded token: {decoded_token}")'''
        try:
            while True:
                data = await websocket.receive_text()
        except WebSocketDisconnect:
            settings.WAR_CLIENTS.remove(websocket)
    except AuthJWTException as err:
        await websocket.send_text(err.message)
        await websocket.close()

async def raid_websocket(websocket: WebSocket, token: str = Query(...), Authorize: AuthJWT = Depends()):
    await websocket.accept()
    settings.RAID_CLIENTS.add(websocket)
    try:
        '''Authorize.jwt_required("websocket", token=token)
        await websocket.send_text("Successfully Login!")
        decoded_token = Authorize.get_raw_jwt(token)
        await websocket.send_text(f"Here your decoded token: {decoded_token}")'''
        try:
            while True:
                data = await websocket.receive_text()
        except WebSocketDisconnect:
            settings.RAID_CLIENTS.remove(websocket)
    except AuthJWTException as err:
        await websocket.send_text(err.message)
        await websocket.close()