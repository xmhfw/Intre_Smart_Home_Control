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
        
        await intre_ss.sync_products_to_cloud()
        await intre_ss.sync_scenes_to_cloud()

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
            """启动设备刷新定时器，默认10秒刷新一次"""
            self.__request_refresh_devices_info(hass, config_entry, delay_sec)

    # 添加公共方法来停止定时器
    def stop_refresh_timer(self) -> None:
        """停止设备刷新定时器"""
        if self._refresh_devices_timer:
            self._refresh_devices_timer.cancel()
            self._refresh_devices_timer = None

async def async_setup(hass: HomeAssistant, hass_config: dict) -> bool:
    _LOGGER.debug("intretech init3")
    _LOGGER.debug("intretech intt------------------->.22")
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault('products', {})
    hass.data[DOMAIN].setdefault('intre_ss', {})
    hass.data[DOMAIN].setdefault('intreIot_clients', {})
    '''
    # 创建Intrenitify实例并存储在hass.data中
    intrenitify = Intrenitify(hass)
    hass.data[DOMAIN]['intre_client'] = intrenitify
    
    # 获取配置项
    config_entries = hass.config_entries.async_entries(DOMAIN)
    if config_entries:
        config_entry = next(iter(config_entries))
        # 启动定时器（例如，设置为10秒后首次执行）
        intrenitify.start_refresh_timer(hass, config_entry, 10)
    '''
    return True

async def state_changed_callback(event):
    old_state = event.data.get("old_state")
    new_state = event.data.get("new_state")

    if not (old_state and new_state):
        return

    _LOGGER.debug(f"实体 {event.data['entity_id']} 的状态发生变化:")
    _LOGGER.debug(f"  旧状态: {old_state.state}")
    _LOGGER.debug(f"  新状态: {new_state.state}")


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
    _LOGGER.debug("intretech init4455 ="+str(config_entry.data)+str(hass.data[DOMAIN]))

    #TEST LOG 
    scenes = [state for state in hass.states.async_all() if state.domain == 'scene']
    # 遍历并打印场景名称和实体 ID
    for scene in scenes:
        _LOGGER.debug(f"Scene Name: {scene.name}, Entity ID: {scene.entity_id}")

    _LOGGER.debug("intretech init445522 ="+str(config_entry.data)+str(hass.data[DOMAIN]))
    
    # HA

    intre_ss:IntreManagementEngine= await get_intress_instance_async(hass=hass, config_entry=config_entry,persistent_notify=ha_persistent_notify)
    
    await intre_ss.sync_products_to_cloud()
    await intre_ss.sync_scenes_to_cloud()

    #intreIot_client: IntreIoTClient = await get_intreIot_instance_async(hass=hass, entry_id=entry_id,entry_data=entry_data,persistent_notify=ha_persistent_notify)
    #intreIot_client._http_client.get_home_info('12344')
    #intre_ha:IntreIotHa =IntreIotHa(hass=hass,auto_sync=False)
    #intress:IntreManagementEngine =IntreManagementEngine(hass=hass,intreIot_client=intreIot_client,config_entry=config_entry,intre_ha=intre_ha)

    #hass.data[DOMAIN]['intress'][config_entry.entry_id]=intress
    #await intress.init_async()
    
    
    
    entity_ids=[]
    dr = device_registry.async_get(hass)
    er = entity_registry.async_get(hass)
    # 遍历所有设备
    for device in dr.devices.values():
        _LOGGER.debug(f"设备ID: {device.id}")
        _LOGGER.debug(f"名称: {device.name or '无名设备'}")
        _LOGGER.debug(f"制造商: {device.manufacturer}")
        _LOGGER.debug(f"型号: {device.model}")
        _LOGGER.debug(f"软件版本: {device.sw_version}")
        _LOGGER.debug(f"硬件版本: {device.hw_version}")
        _LOGGER.debug(f"连接信息: {device.connections}")
        _LOGGER.debug(f"唯一标识符: {device.identifiers}")
        _LOGGER.debug(f"所属区域ID: {device.area_id}")
        _LOGGER.debug(f"配置URL: {device.configuration_url}")
        
        er = entity_registry.async_get(hass)
        for entry in er.entities.values():
            if entry.device_id == device.id:
                entity_ids.append(entry.entity_id)
                _LOGGER.debug(f"- 实体ID: {entry.entity_id}")
                _LOGGER.debug(f" 友好名称: {entry.name}")
                _LOGGER.debug(f" 平台: {entry.platform}")
                _LOGGER.debug(f" 唯一ID: {entry.unique_id}")
                _LOGGER.debug(f" 图标: {entry.icon}")
                _LOGGER.debug(f" 设备ID: {entry.device_id}")
                _LOGGER.debug(f" 区域ID: {entry.area_id}")
                _LOGGER.debug(f" 禁用原因: {entry.disabled_by}")
                _LOGGER.debug(f" 隐藏原因: {entry.hidden_by}")
                _LOGGER.debug(f" 能力: {entry.capabilities}")
                _LOGGER.debug(f" 支持功能: {entry.supported_features}")
                _LOGGER.debug(f" 测量单位: {entry.unit_of_measurement}")
                _LOGGER.debug(f" 原始名称: {entry.original_name}")
                _LOGGER.debug(f" 原始图标: {entry.original_icon}")
                _LOGGER.debug(f" 配置项ID: {entry.config_entry_id}")
                _LOGGER.debug(f" 选项: {entry.options}")
                _LOGGER.debug(f" 翻译键: {entry.translation_key}")
                _LOGGER.debug(f" 是否有实体名称: {entry.has_entity_name}")
                _LOGGER.debug("-" * 40)
        _LOGGER.debug("-" * 40)

    # 开始监听
    unsub = async_track_state_change_event(
        hass,  # Home Assistant 实例
        entity_ids,  # 要监听的实体列表
        state_changed_callback,  # 回调函数
    )
   
    
    '''
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

    entry_id = config_entry.entry_id
    entry_data = dict(config_entry.data)
    entry_data['storage_path']=hass.config.path('.storage', DOMAIN)

    intreIot_client: IntreIoTClient = await get_intreIot_instance_async(hass=hass, entry_id=entry_id,entry_data=entry_data,persistent_notify=ha_persistent_notify)
    homes_info=await intreIot_client.get_homes_devices()
    
    hass.data[DOMAIN]['products'][config_entry.entry_id] = homes_info
    hass.data[DOMAIN]['intreIot_clients'][config_entry.entry_id] = intreIot_client
    await hass.config_entries.async_forward_entry_setups(config_entry, SUPPORTED_PLATFORMS)  
    
        

    newproductIdList:list=[]
    oldproductList:list=intreIot_client.user_confg.get('productlist',None)

    for homeid in homes_info:
        for productObj in homes_info[homeid].productObjList:
            newproductIdList.append(productObj.deviceId)

    dr = device_registry.async_get(hass)
    if oldproductList:
        for did in oldproductList:
            if did not in  newproductIdList:
                device_entry = dr.async_get_device(
                    identifiers={(DOMAIN,did)},
                    connections=None)
                if not device_entry:
                    _LOGGER.debug('remove device not found, %s', did)
                    continue
                dr.async_remove_device(device_id=device_entry.id)
                _LOGGER.info('delete device entry, %s, %s', did, device_entry.id)

    await intreIot_client.update_user_confg(newproductIdList)
    '''
    return True
    
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
