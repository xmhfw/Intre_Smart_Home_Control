import asyncio
import websockets
import json
import socket
import requests
import qrcode
# Home Assistant 配置
#HOME_ASSISTANT_URL = "http://192.168.110.175:8123"  # Home Assistant 地址
HOME_ASSISTANT_URL = "http://192.168.1.34:8123"  # Home Assistant 地址
#ACCESS_TOKEN_HJB="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiIyZmM4MThhYzA2Nzk0OGU0ODdiMWQ4MWE3MDFkZGFkYiIsImlhdCI6MTc0NDY5NDcxMiwiZXhwIjoyMDYwMDU0NzEyfQ.FKbf9TFNOUBL56J6R4731xnNk6UDZ1-8eFbSbNHTK8o"
ACCESS_TOKEN_HQB = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiI5ODFjMzJiODViOWQ0MTU3OThiMGYyZDBkMzU5MzIyZCIsImlhdCI6MTc0NDc2MjgyMCwiZXhwIjoyMDYwMTIyODIwfQ.5D1_rejcpU9Wql4iMfdy1UeA5b9PCQ1hIot2W-iVaLE"
ACCESS_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiI0MGU0OGQzMjA4OWI0NmNjOTJkMzZhMGRlYTRiMDI3NyIsImlhdCI6MTczNzA5NjM1OSwiZXhwIjoyMDUyNDU2MzU5fQ.9WwxQTnyWxoJt93DtRlomOpd_tfizUXCdi701sfsY7U"  # Home Assistant 长期访问令牌
LIGHT_ENTITY_ID = "light.lumi_cn_332639216_mgl03_s_6"  # 灯光实体 ID
# Change this to your Home Assistant instance URL and token
HA_URL = "ws://127.0.0.1:8123/api/websocket"
#ACCESS_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiI0MGU0OGQzMjA4OWI0NmNjOTJkMzZhMGRlYTRiMDI3NyIsImlhdCI6MTczNzA5NjM1OSwiZXhwIjoyMDUyNDU2MzU5fQ.9WwxQTnyWxoJt93DtRlomOpd_tfizUXCdi701sfsY7U"
ACCESS_TOKEN_XIAOYAN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiI3MjAyNmQ4MDcxYmM0ZDdkYTk5OWQ1NTFjNGU0M2QxMiIsImlhdCI6MTc0MDEwMjA5MywiZXhwIjoyMDU1NDYyMDkzfQ.tEuUjsb3pD-OxGXk-WdsKQd76hGcH1_wKbk834CVNdk"
#light.lumi_cn_332639216_mgl03_s_6
async def connect_ha():
    async with websockets.connect(HA_URL) as websocket:
        # Authenticate
        auth_message = {
            "type": "auth",
            "access_token": ACCESS_TOKEN_HQB
        }
        
        command = {
          "id": 24,
          "type": "call_service",
          "domain": "light",
          "service": "turn_off",
          "target": {
            "entity_id": "light.lumi_cn_332639216_mgl03_s_6"
          }
        }
        getstate_msg = {
            "id": 2,
            "type": "call_service",
            "domain": "light",
            "service": "services"
        }
        
        get_state={
          "id": 19,
          "type": "get_states"
        }
        get_service={
            "id": 19,
            "type": "get_services"
        }
        
        subscribe_event={
          "id": 18,
          "type": "subscribe_events",
        }
        
        #connect
        await websocket.send(json.dumps(auth_message))
        response = await websocket.recv()
        print(f"Auth response: {response}")

        #await websocket.send(json.dumps(get_state))
        #response = await websocket.recv()
        #print(f"Auth response: {response}")
        
        #subscribe_event
        await websocket.send(json.dumps(get_state))
        response = await websocket.recv()
        
        
        print(f"Auth response: {response}")
        # Now you can listen for events or send commands
        while True:
            message = await websocket.recv()
            print(f"Received message: {message}")

# Run the client
#asyncio.get_event_loop().run_until_complete(connect_ha())
#await connect_ha()
# Run the client
asyncio.get_event_loop().run_until_complete(connect_ha())
'''

# 控制灯光的函数
def control_entity(entity_id,cmd):

    domain=entity_id.split('.', 1)[0]
    url = f"{HOME_ASSISTANT_URL}/api/services/{domain}/{cmd}"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    data = {
        "entity_id": entity_id
    }
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        print(f"domain {cmd} 操作成功")
    else:
        print(f"domain {cmd} 操作失败: {response.text}")

# Socket 服务端
def start_socket_server():
    # 创建 Socket 对象
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(("0.0.0.0", 8888))  # 绑定 IP 和端口
    server_socket.listen(5)  # 监听客户端连接
    print("Socket 服务端已启动，等待客户端连接...")

    while True:
            conn, addr = server_socket.accept()
            with conn:
                print(f"Connected by {addr}")
                data = conn.recv(1024)
                if not data:
                    continue
                
                try:
                    # 解析 JSON 数据
                    json_data = json.loads(data.decode('utf-8'))
                    entity_id = json_data.get('entity_id')
                    cmd = json_data.get('cmd')
                    
                    if entity_id and cmd:
                        control_entity(entity_id, cmd)
                    else:
                        print("Invalid JSON data: missing 'entity_id' or 'cmd'")
                except json.JSONDecodeError:
                    print("Invalid JSON data received")
'''