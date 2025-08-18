from homeassistant.config_entries import ConfigEntries
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry, entity_registry
import logging
import threading
import time
import asyncio
import websockets
import json
import socket
import requests
from typing import Optional
from .intreiot.intreIot_cloud import IntreIotHttpClient
from .intreiot.intreIot_client import IntreIoTClient
from .intreiot.const import (DOMAIN, SUPPORTED_PLATFORMS)
from homeassistant.helpers.event import async_track_state_change_event
from .intreiot.intre_manage_engine import (IntreManagementEngine,get_intress_instance_async)
from .intreiot.engine_manager import EngineManager
from .intreiot.intreIot_ha import (IntreIotHa)
from typing import Any, Callable, Optional, final
#from homeassistant.helpers.scene import async_get_scenes
_LOGGER = logging.getLogger(__name__)
#from .const import DOMAIN
#from .config_flow import IntreHomeConfigFlow
HOME_ASSISTANT_URL = "http://192.168.1.34:8123"  # Home Assistant 地址
ACCESS_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiI0MGU0OGQzMjA4OWI0NmNjOTJkMzZhMGRlYTRiMDI3NyIsImlhdCI6MTczNzA5NjM1OSwiZXhwIjoyMDUyNDU2MzU5fQ.9WwxQTnyWxoJt93DtRlomOpd_tfizUXCdi701sfsY7U"  # Home Assistant 长期访问令牌

_LOGGER = logging.getLogger(__name__)
class Intrenitify():
    _main_loop: asyncio.AbstractEventLoop
    _refresh_devices_timer: Optional[asyncio.TimerHandle]
    
    def __init__(self, hass: HomeAssistant) -> None:
        self._main_loop = hass.loop
        self._refresh_devices_timer = None
    @final
    async def async_setup_entry(
        self,hass: HomeAssistant, config_entry: ConfigEntry
    ) -> bool:
        # 注册更新监听器
        """Set up an entry."""
        def ha_persistent_notify(
            notify_id: str, title: Optional[str] = None,
            message: Optional[str] = None
        ) -> None:
            """Send messages in Notifications dialog box."""
            if title:
                persistent_notification.async_create(
                    hass=hass,  message=message,
                    title=title, notification_id=notify_id)
            else:
                persistent_notification.async_dismiss(
                    hass=hass, notification_id=notify_id)
        _LOGGER.debug("intretech init4455 ="+str(config_entry.data)+str(hass.data[DOMAIN]))

        #TEST LOG 
        scenes = [state for state in hass.states.async_all() if state.domain == 'scene']
        # 遍历并打印场景名称和实体 ID
        for scene in scenes:
            _LOGGER.debug(f"Scene Name: {scene.name}, Entity ID: {scene.entity_id}")

        _LOGGER.debug("intretech init445522 ="+str(config_entry.data)+str(hass.data[DOMAIN]))
        intre_ss:IntreManagementEngine= await get_intress_instance_async(hass=hass, config_entry=config_entry,persistent_notify=ha_persistent_notify)
        
        #await intre_ss.sync_products_to_cloud()
        #await intre_ss.sync_scenes_to_cloud()

        return True

    @final
    def __request_refresh_devices_info(self, hass: HomeAssistant, config_entry: ConfigEntry, delay_sec: int) -> None:
        if self._refresh_devices_timer:
            self._refresh_devices_timer.cancel()
            self._refresh_devices_timer = None
        
        self._refresh_devices_timer = self._main_loop.call_later(
            delay_sec, lambda: self._main_loop.create_task(
                self.async_setup_entry(hass, config_entry)))   
    # 添加公共方法来启动定时器
    def start_refresh_timer(self, hass: HomeAssistant, config_entry: ConfigEntry, delay_sec: int = 10) -> None:
            """启动设备刷新定时器,默认10秒刷新一次"""
            self.__request_refresh_devices_info(hass, config_entry, delay_sec)

    # 添加公共方法来停止定时器
    def stop_refresh_timer(self) -> None:
        """停止设备刷新定时器"""
        if self._refresh_devices_timer:
            self._refresh_devices_timer.cancel()
            self._refresh_devices_timer = None

async def async_setup(hass: HomeAssistant, hass_config: dict) -> bool:
    _LOGGER.debug("intretech async_setup init")
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault('products', {})
    hass.data[DOMAIN].setdefault('intre_ss', {})
    hass.data[DOMAIN].setdefault('intreIot_clients', {})
    return True

'''
#config_flow = IntreHomeConfigFlow
async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> bool:
    # 注册更新监听器
    """Set up an entry."""
    def ha_persistent_notify(
        notify_id: str, title: Optional[str] = None,
        message: Optional[str] = None
    ) -> None:
        """Send messages in Notifications dialog box."""
        if title:
            persistent_notification.async_create(
                hass=hass,  message=message,
                title=title, notification_id=notify_id)
        else:
            persistent_notification.async_dismiss(
                hass=hass, notification_id=notify_id)

    _LOGGER.debug("async_setup_entry="+str(config_entry.data)+str(hass.data[DOMAIN]))
    # HA
    intre_ss:IntreManagementEngine= await get_intress_instance_async(hass=hass, config_entry=config_entry,persistent_notify=ha_persistent_notify)
    
    return True
 '''
async def async_initialize_core(hass: HomeAssistant, config_entry: ConfigEntry):
    """核心初始化逻辑（可重复调用）"""
    def ha_persistent_notify(
        notify_id: str, title: Optional[str] = None,
        message: Optional[str] = None
    ) -> None:
        from homeassistant.components import persistent_notification
        if title:
            persistent_notification.async_create(
                hass=hass, message=message, title=title, notification_id=notify_id
            )
        else:
            persistent_notification.async_dismiss(hass=hass, notification_id=notify_id)

    _LOGGER.debug("核心初始化逻辑执行: " + str(config_entry.data))
    # 创建管理引擎实例（核心逻辑）
    intre_ss: IntreManagementEngine = await get_intress_instance_async(
        hass=hass, 
        config_entry=config_entry,
        persistent_notify=ha_persistent_notify
    )

    # 关键：将实例注册到全局 EngineManager
    EngineManager.register_instance("intre_manage_engine", intre_ss)  # 注册实例，名称与客户端获取时一致
    _LOGGER.debug("IntreManagementEngine 实例已注册到 EngineManager")

    # 其他需要重复执行的初始化操作（如同步设备、场景等）
    # await intre_ss.sync_products_to_cloud()
    # await intre_ss.sync_scenes_to_cloud()
    return True

# 原来的 async_setup_entry 只调用一次，负责绑定配置项
async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> bool:
    """首次设置配置项（仅执行一次）"""
    # 调用核心初始化逻辑
    return await async_initialize_core(hass, config_entry)



async def async_unload_entry(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> bool:
    """Unload the entry."""
    '''
    entry_id = config_entry.entry_id
    # Unload the platform
    unload_ok = await hass.config_entries.async_unload_platforms(
        config_entry, SUPPORTED_PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN]['products'].pop(entry_id, None)
    
    intreIot_client: IntreIoTClient = hass.data[DOMAIN]['intreIot_clients'].pop(entry_id, None)
    if intreIot_client:
        await intreIot_client.deinit_async()
    del intreIot_client
    '''
    return True


async def async_remove_entry(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> bool:
    """Remove the entry."""
    storage: Optional[IntreIoTStorage] = hass.data[DOMAIN].get('intreiot_storage', None)

    # Clean device list
    await storage.remove_async(domain='IntreIot_config', name=f'{config_entry.entry_id}_cn', type_=dict)
   
    return True


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
