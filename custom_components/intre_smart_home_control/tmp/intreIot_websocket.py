import asyncio
import websockets
import json
import socket
import requests
from typing import Any, Callable, Optional, final
# Home Assistant 配置
#HOME_ASSISTANT_URL = "http://192.168.110.175:8123"  # Home Assistant 地址
HOME_ASSISTANT_URL = "http://192.168.1.34:8123"  # Home Assistant 地址
ACCESS_TOKEN_HJB="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiIyZmM4MThhYzA2Nzk0OGU0ODdiMWQ4MWE3MDFkZGFkYiIsImlhdCI6MTc0NDY5NDcxMiwiZXhwIjoyMDYwMDU0NzEyfQ.FKbf9TFNOUBL56J6R4731xnNk6UDZ1-8eFbSbNHTK8o"
ACCESS_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiI0MGU0OGQzMjA4OWI0NmNjOTJkMzZhMGRlYTRiMDI3NyIsImlhdCI6MTczNzA5NjM1OSwiZXhwIjoyMDUyNDU2MzU5fQ.9WwxQTnyWxoJt93DtRlomOpd_tfizUXCdi701sfsY7U"  # Home Assistant 长期访问令牌
LIGHT_ENTITY_ID = "light.lumi_cn_332639216_mgl03_s_6"  # 灯光实体 ID
# Change this to your Home Assistant instance URL and token
HOMEASSISTANT_WEBSOCKET_URL = "ws://127.0.0.1:8123/api/websocket"
#ACCESS_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiI0MGU0OGQzMjA4OWI0NmNjOTJkMzZhMGRlYTRiMDI3NyIsImlhdCI6MTczNzA5NjM1OSwiZXhwIjoyMDUyNDU2MzU5fQ.9WwxQTnyWxoJt93DtRlomOpd_tfizUXCdi701sfsY7U"
ACCESS_TOKEN_XIAOYAN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiI3MjAyNmQ4MDcxYmM0ZDdkYTk5OWQ1NTFjNGU0M2QxMiIsImlhdCI6MTc0MDEwMjA5MywiZXhwIjoyMDU1NDYyMDkzfQ.tEuUjsb3pD-OxGXk-WdsKQd76hGcH1_wKbk834CVNdk"
#light.lumi_cn_332639216_mgl03_s_6

def WEBSOCKET_AUTH_JSON(token)->dict:
    return {
            "type": "auth",
            "access_token": token
        }

def WEBSOCKET_GET_STATE_JSON()->dict:
    return {
          "id": 19,
          "type": "get_states"
        }

def WEBSOCKET_CALL_SERVICE_JSON(domain,service,entity_id)->dict:
    return {
          "id": 24,
          "type": "call_service",
          "domain": domain,
          "service": service,
          "target": {
            "entity_id": entity_id
          }
        }

def WEBSOCKET_SUB_STATE_JSON()->dict:
    return {
        "id": 18,
        "type": "subscribe_events",
        "event_type": "state_changed"
        }

class IntreIOTWebSocket():
    _main_loop: asyncio.AbstractEventLoop
    _token:str
    _url:str
    _loop_task: Optional[asyncio.Task]
    def __init__(self,token:str,loop: Optional[asyncio.AbstractEventLoop] = None) -> None:
        self._token=token
        self._url=HOMEASSISTANT_WEBSOCKET_URL
        self._main_loop = loop or asyncio.get_running_loop()
        self._loop_task = None
        self._websocket=None

    async def init_async(self) -> None:
        self._websocket=await websockets.connect(self._url)
        response = await self._websocket.recv()
    
    async def deinit_async(self) -> None:
        if self._loop_task:
            self._loop_task.cancel()
            self._loop_task = None
        self._websocket.close()
    async def auth_req(self) -> None:
        await self._websocket.send(json.dumps(WEBSOCKET_AUTH_JSON(self._token)))
        response = await self._websocket.recv()
        res_obj: dict = json.loads(response)
        print(res_obj)

    async def getHaDeviceList(self)->list:
        await self._websocket.send(json.dumps(WEBSOCKET_GET_STATE_JSON()))
        
        response = await self._websocket.recv()
        res_obj: dict = json.loads(response)
        #print(res_obj)
        if res_obj['success']==True:
            return res_obj['result']
        return res_obj
    
    async def call_service(self,domain:str,service:str,entity_id:str)->list:
        await self._websocket.send(json.dumps(WEBSOCKET_CALL_SERVICE_JSON(domain,service,entity_id)))
        response = await self._websocket.recv()
        if response['success']==True:
            return response['result']
    
    async def sub_state(self)->dict:
        await self._websocket.send(json.dumps(WEBSOCKET_SUB_STATE_JSON()))
        response = await self._websocket.recv()
        self._loop_task = self._main_loop.create_task(self.__loop())
        if response['success']==True:
            return response['result']
    
    async def __loop(self) -> None:
        while True:
            try:
                message = await self._websocket.recv()
                print(f"Received message: {message}")
            except asyncio.CancelledError:
                _LOGGER.error('update_status_and_info task was cancelled')
            await asyncio.sleep(1)


async def ha_test():
    web:IntreIOTWebSocket =IntreIOTWebSocket(ACCESS_TOKEN_HJB)
    await web.init_async()

    print('init ok')
    await web.auth_req()
    print('auth_req ok')
    devicelist=await web.getHaDeviceList()
    
    for device in devicelist:
        
        entity_id = device['entity_id'].split('.')[0]
        
        if entity_id=='light':
            print(device)
        elif entity_id=='switch':
            print(device)



asyncio.get_event_loop().run_until_complete(ha_test())