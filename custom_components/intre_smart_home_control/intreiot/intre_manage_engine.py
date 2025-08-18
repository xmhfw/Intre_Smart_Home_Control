import importlib
import logging
import os
import sys
import asyncio
import json
import unicodedata
import aiohttp
from homeassistant.config_entries import ConfigEntries
from homeassistant.helpers import device_registry, entity_registry
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from typing import Any, Callable, Optional, final
from .intreIot_ha import IntreIotHa
from .intreIot_module import (IntreIoTProduct,IntreIoTModule)
from .const  import (DOMAIN, SUPPORTED_PLATFORMS,MODULE_PRIORITY_DB,PRODUCT_KEY_DB,NETWORK_REFRESH_INTERVAL,MQTT_ToH,INTRE_PHYSICAL_MODEL_CONTROL_VERSION,INTRE_HA_PRODUCT_KEY)
from .intreIot_client import IntreIoTClient
from .intreIot_network import IntreIoTNetwork
from .intreIot_storage import IntreIoTStorage
from collections import Counter
from homeassistant.helpers import device_registry
LONG_LIVED_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiIxMjljN2YwMDZlMTU0NjQ0OTQyMDdhMGEyMzRiMTI1YSIsImlhdCI6MTc1NTI1NDE2OSwiZXhwIjoyMDcwNjE0MTY5fQ.-URgGajTKRAt02qG-uJ082AR_h3FJQgimprSAp-U1QE"
HA_IP = "10.0.0.105"
ENTITY_ID = "switch.ws04_d2_5_1"
_LOGGER = logging.getLogger(__name__)

class Intrenitify():
    def __init__(self) -> None:
        pass
    #获取HA盒子MAC地址    
    def get_ha_mac_address(self) -> Optional[str]:
        import fcntl
        import struct
        import socket

        # 常见的网络接口名称列表，按优先级排序
        interfaces = ['eth0', 'wlan0', 'en0', 'ens33', 'eth1', 'wlan1']
        
        for ifname in interfaces:
            try:
                # 创建socket连接
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                # 获取接口的MAC地址
                info = fcntl.ioctl(
                    s.fileno(),
                    0x8927,  # SIOCGIFHWADDR
                    struct.pack('256s', ifname.encode('utf-8')[:15])
                )
                # 解析MAC地址
                mac = ':'.join(['%02x' % b for b in info[18:24]])
                # 排除本地回环接口的MAC（通常为00:00:00:00:00:00）
                if mac != '00:00:00:00:00:00':
                    _LOGGER.debug(f"获取到HA设备MAC地址: {mac} (接口: {ifname})")
                    return mac
            except IOError:
                # 接口不存在时继续尝试下一个
                continue
            except Exception as e:
                _LOGGER.debug(f"获取MAC地址时出错: {str(e)}")
                continue
        
        # 如果上述接口都失败，尝试获取所有可用接口
        try:
            import netifaces
            for interface in netifaces.interfaces():
                if interface.startswith(('lo', 'docker')):  # 跳过回环和docker虚拟接口
                    continue
                addrs = netifaces.ifaddresses(interface)
                if netifaces.AF_LINK in addrs:
                    mac = addrs[netifaces.AF_LINK][0]['addr']
                    if mac != '00:00:00:00:00:00':
                        _LOGGER.debug(f"通过netifaces获取到HA设备MAC地址: {mac} (接口: {interface})")
                        return mac
        except ImportError:
            _LOGGER.debug("未安装netifaces库,无法枚举所有网络接口")
        except Exception as e:
            _LOGGER.debug(f"通过netifaces获取MAC地址时出错: {str(e)}")
        
        _LOGGER.debug("无法获取HA设备的MAC地址")
        return None     
class  IntreManagementEngine():
    _main_loop: asyncio.AbstractEventLoop
    _intre_ha:IntreIotHa
    _intre_devicesn_add:list[str]  #本地存储所有已经创建成盈趣物模型的产品列表
    _intre_products:list[IntreIoTProduct]  #本地存储所有添加过产品列表
    _intre_devicesn_sub:list[str]  #本地存储已经订阅的产品
    _hadevices:list
    _sub_tree:dict[str,list[Callable[str, None]]]
    _hass:HomeAssistant
    _config_entry:ConfigEntry
    _intreIot_client:IntreIoTClient
    _storage:IntreIoTStorage
    _cloud_server: str
    _uid:str
    _user_config: dict
    _deviceId: str
    _propertylist:str
    _refresh_scene_device_timer: Optional[asyncio.TimerHandle]
    _refresh_device_timer: Optional[asyncio.TimerHandle]
    _scene_entity_id_list:list
    _device_entity_id_list:list
    _rspdata:list
    _sync_product_info:list
    _product_device_id:list
    def __init__(
        self,
        hass: HomeAssistant, 
        intreIot_client:IntreIoTClient,
        storage:IntreIoTStorage,
        config_entry: ConfigEntry,
        intre_ha:IntreIotHa,
        loop: Optional[asyncio.AbstractEventLoop] = None) -> None:
        self._storage = storage
        self._main_loop = loop or asyncio.get_running_loop()
        self._intre_ha=intre_ha
        self._hass =hass
        self._sub_tree={}
        self._intre_products=[]
        self._config_entry = config_entry
        self._intreIot_client=intreIot_client
        self._cloud_server='cn'
        self._user_config={}
        self._deviceId = None
        self._propertylist = None
        self._refresh_scene_device_timer = None
        self._refresh_device_timer = None
        self._scene_entity_id_list = []
        self._device_entity_id_list = []
        self._rspdata = []
        self._sync_product_info = []
        self._product_device_id = []
    ''' 
    #HA设备离在线
    async def get_ha_device_status(self, ha_ip, entity_id, long_lived_token):
        """更精准区分设备在线状态和功能开关状态"""
        api_url = f"http://{ha_ip}:8123/api/states/{entity_id}"
        headers = {
            "Authorization": f"Bearer {long_lived_token}",
            "Content-Type": "application/json"
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url, headers=headers, timeout=5) as response:
                    # 1. 实体存在（200）：正常获取状态
                    if response.status == 200:
                        device_data = await response.json()
                        # 设备在线状态（基于available字段）
                        is_available = device_data.get("attributes", {}).get("available")
                        # 功能开关状态（基于state字段）
                        switch_state = device_data.get("state", "unknown")
                        _LOGGER.debug(f"switch_state: {switch_state}")
                        _LOGGER.debug(f"is_available: {is_available}")
                        # 组合状态描述
                        online_desc = "在线" if is_available else "离线"
                        func_desc = f"（功能关闭）" if switch_state == "off" else f"（功能开启）"
                        if switch_state == "on":
                            online_desc = "在线" 
                            func_desc = "（功能开启）"
                            return {
                                "online_status": f"{online_desc}{func_desc}",
                                "switch_state": switch_state,
                                "is_power_off": False  # 设备未断电（能正常通信）
                            }
                        elif switch_state == "off":
                            online_desc = "在线" 
                            func_desc = "（功能关闭）" 
                            return {
                                "online_status":f"{online_desc}{func_desc}",
                                "switch_state": "off",
                                "is_power_off": False
                            } 
                        elif switch_state == "unknown":
                            online_desc = "离线" 
                            func_desc = "unfunction"
                            return {
                                "online_status": f"{online_desc}{func_desc}",
                                "switch_state": switch_state,
                                "is_power_off": True  # 设备断电（不能正常通信）
                            }
                    
                    # 2. 404错误：实体不存在（可能是设备彻底离线或未注册）
                    elif response.status == 404:
                        online_desc = "离线" 
                        func_desc = "unfunction" 
                        return {
                            "online_status":f"{online_desc}{func_desc}",
                            "switch_state": "unknown",
                            "is_power_off": True
                        }
                    
                    # 3. 其他HTTP错误
                    else:
                        return {
                            "online_status": f"获取失败:HTTP状态码({response.status})",
                            "switch_state": None,
                            "is_power_off": None
                        }

        # 网络错误：设备无法通信（大概率断电）
        except (aiohttp.ClientConnectionError, asyncio.TimeoutError):
            return {
                "online_status": "离线（无法连接，可能已断电）",
                "switch_state": "unknown",
                "is_power_off": True
            }
        
        except Exception as e:
            return {
                "online_status": f"获取失败:{str(e)}",
                "switch_state": None,
                "is_power_off": None
            }
    '''
    async def init_async(self) -> None:
        self._intre_products=[]
        self._intre_devicesn_add=[]  #本地存储所有已经创建成盈趣物模型的产品devicesn
        self._intre_devicesn_sub=[]  #本地存储已经订阅的产品devicesn

        self.__request_refresh_scene_device_info(10)
        config_data={}
        self._hass.data[DOMAIN]['config_data']=config_data
        await self._hass.config_entries.async_forward_entry_setups(self._config_entry, ['notify'])  
        # 建立与客户端的双向关联（如果需要）
        if hasattr(self._intreIot_client, 'set_management_engine'):
            self._intreIot_client.set_management_engine(self)
            _LOGGER.debug("Established bidirectional reference with IntreIoTClient")
           
        down_tls_property_report_reply_topic:str = f'{MQTT_ToH}device/Intre.BGZ001/{self._intreIot_client._device_id}/down/tls/property/report-reply'
        self._intreIot_client.down_tls_property_report_reply(topic=down_tls_property_report_reply_topic,handler=self.down_tls_property_report_reply_topic_callback)
        _LOGGER.debug(f"订阅的主题是333: {down_tls_property_report_reply_topic}")  # 打印订阅的 topic
        #更新网关物模型版本
        await self._intreIot_client._http_client.update_device_version(deviceId=self._intreIot_client._device_id,newVersionCode=INTRE_PHYSICAL_MODEL_CONTROL_VERSION)   
        # 实例化Intrenitify类
        intre_obj = Intrenitify()
        # 获取MAC地址
        mac_address = intre_obj.get_ha_mac_address()
        if mac_address:
            _LOGGER.info(f"当前HA设备的MAC地址是: {mac_address}")
            await self.report_prop_async('Intre.BGZ001',self._intreIot_client._device_id,'deviceInfo','wireMacAddress',mac_address)       
        else:
            _LOGGER.warning("无法获取HA设备的MAC地址")
       

        _LOGGER.debug("IntreManagementEngine initialization completed successfully")

    def bacth_service_call_req(self,batch_serice_call_data:list)->None:
        _LOGGER.debug(f"batch_serice_call_data: {batch_serice_call_data}") 
   

    #情景   
    def add_scene_module_json(self,name:str,entity_id:str)->dict:
        service_input_dict = {
            "sceneId": entity_id
        }
        service_input_value = json.dumps(service_input_dict)
        return{
            "identifier":entity_id ,
            "sceneName": name,
            "execution": [
              {
                "device": {
                    "deviceId":self._intreIot_client._device_id,
                    "moduleKey":"deviceInfo",
                    "propertyList":self._propertylist,
                    "serviceList": [
                    {
                        "serviceKey":  "executeScene",
                        "serviceInputValue": service_input_value
                    }
                    ]
                }
              }
            ]
        }  

    def delete_scene_module_json(self,entity_id:str)->dict:   
        return{
            "identifier":entity_id 
        }  
            
    
    #设备动态新增
    def get_productKey_by_modules(self,_moduleObjList:list[IntreIoTModule]):
        productKey=None
        first_module_index=float('inf')

        for _module in _moduleObjList:
            if _module.module_code in MODULE_PRIORITY_DB:
                index = MODULE_PRIORITY_DB.index(_module.module_code)
                if index < first_module_index:
                    first_module_index = index
                    productKey = PRODUCT_KEY_DB[_module.module_code]

        return productKey

    async def __parse_ha_device(self)->None:
        self._intre_ha.get_device_list()

    async def state_changed_callback(self,event):
        _LOGGER.debug(f'event={event}')
        entity_id=event.data['entity_id']
        if entity_id in self._sub_tree:
            for handler in self._sub_tree[entity_id]:
                await handler(event.data.get("new_state"))
        
    def sub_entity(self, entityid: str, handler: Callable[[dict, Any], None]) -> bool:
        if entityid in self._sub_tree:
            self._sub_tree[entityid].append(handler)
        else:
            self._sub_tree[entityid]=[handler]
        return True
   
    def down_data_define_report_reply_topic_callback(self,data:dict)->bool:  
        _LOGGER.debug(data)
        _LOGGER.debug('down_data_define_report_reply_topic_callback')

    def down_tls_event_report_reply_topic_callback(self,data:dict)->bool:  
        _LOGGER.debug(data)
        _LOGGER.debug('down_tls_event_report_reply_topic_callback')
    
    def down_tls_property_report_reply_topic_callback(self,data:dict)->bool:  
        _LOGGER.debug(data)
        _LOGGER.debug('down_tls_property_report_reply_topic_callback')
       
    def ha_bacth_service_prop_callback(self,data:dict)->bool:
        _LOGGER.debug(data)
        _LOGGER.debug('ha_bacth_service_prop_callback')
        # 遍历 deviceModuleList 和 serviceList
        for module in data.get("deviceModuleList", []):
            for service in module.get("serviceList", []):
                if service.get("serviceKey") == "executeScene":
                    # 解析 serviceInputValue 中的 sceneId
                    service_input_value = service.get("serviceInputValue")
                    if service_input_value:
                        service_input_dict = json.loads(service_input_value)
                        scene_id = service_input_dict.get("sceneId")
                        data={
                            'entity_id':scene_id
                        }
                        if scene_id:
                            _LOGGER.debug(f"收到情景ID: {scene_id}")
                            self.call_ha_service('scene','turn_on',data)
                        else:
                            _LOGGER.debug("serviceInputValue 中缺少 sceneId 字段")
                    else:
                        _LOGGER.debug("消息中缺少 serviceInputValue 字段")
    
    
    def call_ha_service(self,domain:str,service:str,data:str)->None:
        self._intre_ha.ha_call_service(domain=domain,service=service,data=data)  
    
    async def report_prop_async(self,productkey:str,deviceid:str,modulekey:str,propkey:str,prop_value:str)->None:
        await self._intreIot_client.report_prop_async(productkey=productkey,deviceid=deviceid,modulekey=modulekey,propkey=propkey,prop_value=prop_value)
        _LOGGER.debug("开关新状态")  
    async def report_device_tsl_log_async(self,productkey:str,deviceid:str,tls_logs:list)->None:  
        await self._intreIot_client.report_device_tsl_log_async(productkey=productkey,deviceid=deviceid,tls_logs=tls_logs)
        _LOGGER.debug("TLS_LOG") 
    async def report_device_down_tsl_log_async(self,productkey:str,deviceid:str)->None:  
        await self._intreIot_client.report_device_down_tsl_log_async(productkey=productkey,deviceid=deviceid)
        _LOGGER.debug("DOWN_TLS_LOG") 
    async def report_event_async(self,productkey:str,deviceid:str,modulekey:str,eventkey:str,event_value:str)->None:
        await self._intreIot_client.report_event_async(productkey=productkey,deviceid=deviceid,modulekey=modulekey,eventkey=eventkey,event_value=event_value)
        _LOGGER.debug(
            f"准备上报属性: productkey={productkey}, deviceid={deviceid}, "
            f"modulekey={modulekey}, eventkey={eventkey}, event_value={event_value}"   
        )
    async def data_define_report_async(self,productkey:str,deviceid:str,data_define:list)->None:
        await self._intreIot_client.data_define_report_async(productkey=productkey,deviceid=deviceid,data_define=data_define) 
    async def prop_set_reply_async(self,productkey:str,deviceid:str,msgid:str,code:str)->None:
        await self._intreIot_client.prop_set_reply_async(productkey=productkey,deviceid=deviceid,msgid=msgid,code=code)
    @property
    def user_confg(self) -> dict:
        return self._user_config

    async def update_user_confg(self,user_config:dict) -> None:
        await self._storage.update_user_config_async(
            uid=self._uid, cloud_server=self._cloud_server,
            config={'productlist': user_config})
        return 
    '''
    async def deinit_async(self) -> None:
        await self._http_client.deinit_async()

        # Cancel refresh auth info
        if self._refresh_scene_device_timer:
            self._refresh_scene_device_timer.cancel()
            self._refresh_scene_device_timer = None
    '''
          
    @final
    def __request_refresh_scene_device_info(self,delay_sec: int) -> None:
        if self._refresh_scene_device_timer:
            self._refresh_scene_device_timer.cancel()
            self._refresh_scene_device_timer = None
        
        self._refresh_scene_device_timer = self._main_loop.call_later(
            delay_sec, lambda: self._main_loop.create_task(
                self.sync_ha_device_and_scene_cloud()))

    @final
    async def subscribe_device(self) -> bool:
        for product in self._intre_products:

            batch_modules = product.get_modules_prop_json()
            
            prop_set_topic:str = f'{MQTT_ToH}device/{product.productKey}/{product.deviceId}/down/tls/property/set'
            self._intreIot_client.sub_prop_set(topic=prop_set_topic,handler=product.prop_set_callback)
            _LOGGER.debug(f"订阅的主题是111: {prop_set_topic}")  # 打印订阅的 topic
            
            service_call_topic:str = f'{MQTT_ToH}device/{product.productKey}/{product.deviceId}/down/tls/service/call'
            self._intreIot_client.sub_service_call(topic=service_call_topic,handler=product.service_call_callback)
            _LOGGER.debug(f"订阅的主题是222: {service_call_topic}")  # 打印订阅的 topic                          
            
            bacth_service_prop_topic:str = f'{MQTT_ToH}device/{product.productKey}/{product.deviceId}/down/tls/batch/property/service/set'
            self._intreIot_client.sub_bacth_service_prop(topic=bacth_service_prop_topic,handler=product.bacth_service_prop_callback)
            _LOGGER.debug(f"订阅的主题是333: {bacth_service_prop_topic}")  # 打印订阅的 topic  
            self._intre_devicesn_sub.append(product.deviceSn)

            await self._intreIot_client.report_batch_module_prop_async(productkey=product.productKey,deviceid=product.deviceId,batch_modules=batch_modules)

            down_data_define_report_reply_topic:str = f'{MQTT_ToH}device/{product.productKey}/{product.deviceId}/down/tls/data-define/report-reply'
            self._intreIot_client.down_data_define_report_reply(topic=down_data_define_report_reply_topic,handler=self.down_data_define_report_reply_topic_callback)
            down_tls_event_report_reply_topic:str = f'{MQTT_ToH}device/{product.productKey}/{product.deviceId}/down/tls/event/report-reply'
            self._intreIot_client.down_tls_event_report_reply(topic=down_tls_event_report_reply_topic,handler=self.down_tls_event_report_reply_topic_callback)
            '''
            down_tls_property_report_reply_topic:str = f'{MQTT_ToH}device/{product.productKey}/{product.deviceId}/down/tls/property/report-reply'
            self._intreIot_client.down_tls_property_report_reply(topic=down_tls_property_report_reply_topic,handler=self.down_tls_property_report_reply_topic_callback)
            _LOGGER.debug(f"订阅的主题是333: {down_tls_event_report_reply_topic}")  # 打印订阅的 topic   
            '''
        return True
    @final
    async def sync_ha_device_and_scene_cloud(self) -> bool:

        _LOGGER.debug("sync_ha_device_and_scene_cloud start")
        from ..notify import (notify_async_forward_entry_setups)
        
        #获取配置数据
        self._user_config = await self._storage.load_user_config_async(uid=self._config_entry.entry_id, cloud_server=self._cloud_server)
        _LOGGER.debug(f'self._user_config={self._user_config}')
        ##############################################scene sync#############################

        #1.获取HA平台的所有scene
        if self._config_entry.data['scene_sync'] ==True:
            ha_scenes = [state for state in self._hass.states.async_all() if state.domain == 'scene']
            local_scene_entity_ids = [scene.entity_id for scene in ha_scenes]
            _LOGGER.debug(f'local_scene_entity_ids={local_scene_entity_ids}')
            
            #2.获取云端情景列表
            cloud_scene_entity_id_list=[]
            rsp = await self._intreIot_client._http_client.get_scene_module()
            if rsp is not None:#从云端获取情景列表成功
                if isinstance(rsp, dict) and "sceneList" in rsp and isinstance(rsp["sceneList"], list):
                    cloud_scene_entity_id_list = [scene["identifier"] for scene in rsp["sceneList"]]
                _LOGGER.debug(f'cloud_scene_entity_id_list={cloud_scene_entity_id_list}')
                #3.遍历cloud平所有scene，如果不在HA中，则删除
                for entity_id in cloud_scene_entity_id_list: 
                    #_LOGGER.debug(f"synccloudName: {scene.name}, Entity ID: {scene.entity_id}")
                    if entity_id not in local_scene_entity_ids:
                        scenes_data = self.delete_scene_module_json(entity_id=entity_id)
                        await self._intreIot_client._http_client.delete_scene_module(identifier=scenes_data)

                #4.遍历HA平台所有scene，针对未同步的scene,同步到cloud,并更新记录表
                for scene in ha_scenes: 
                    #_LOGGER.debug(f"synccloudName: {scene.name}, Entity ID: {scene.entity_id}")
                    if scene.entity_id not in cloud_scene_entity_id_list:
                        scenes_data = self.add_scene_module_json(name=scene.name,entity_id=scene.entity_id)
                        await self._intreIot_client._http_client.add_scene_module(scene_info=scenes_data)

                if self._intreIot_client._device_id not in self._intre_devicesn_sub:
                    self._intre_devicesn_sub.append(self._intreIot_client._device_id)
                    bacth_service_prop_topic:str = f'{MQTT_ToH}device/Intre.BGZ001/{self._intreIot_client._device_id}/down/tls/batch/property/service/set'
                    self._intreIot_client.sub_bacth_service_prop(topic=bacth_service_prop_topic,handler=self.ha_bacth_service_prop_callback)
                
                
        ##############################################device sync#############################
        if self._config_entry.data['device_sync'] ==True:
            #1.获取HA平台符合要求的设备
            locol_hadevices = self._intre_ha.get_ha_devices()

            #订阅所有实体状态变化
            sub_entitys_list=[]
            for ha_device in locol_hadevices:
                for entity in  ha_device['entitys']:   
                    sub_entitys_list.append(entity['entry'].entity_id)
            _LOGGER.debug(f'sub_entitys_list={sub_entitys_list}')
            self._intre_ha.sub_entitys_state(sub_entitys_list,self.state_changed_callback)

            #2.从配置数据中获取记录已经添加到cloud 的device sn
            self._sync_product_info = self._user_config.get("sync_product_info", [])

            #3.获取所有已经创建模型的设备
            alredy_create_model_List=[product.deviceSn for product in self._intre_products]
            _LOGGER.debug(f'alredy_create_model_List={alredy_create_model_List}')
            #查找所有还没有创建模型的设备，添加到_hadevices
            _hadevices=[]
            for locol_device in locol_hadevices: 
                if locol_device['deviceId']  not in alredy_create_model_List:
                    hadevice={}
                    product_info={}
                    product_info['deviceId'] = locol_device['deviceId']               
                    product_info['productManufacturer'] = locol_device['productManufacturer']
                    product_info['deviceName'] = locol_device['deviceName']
                    product:IntreIoTProduct = IntreIoTProduct(product_info=product_info)
                    hadevice['product']=product
                    hadevice['entitys'] = locol_device['entitys']
                    _hadevices.append(hadevice)
            
            #针对还没创建模型的设备创建物模型，并计算product key
        
            config_data = {'_hadevices': _hadevices}
            self._hass.data[DOMAIN]['config_data'] = config_data
            await notify_async_forward_entry_setups(hass=self._hass,config_entry=self._config_entry,async_add_entities=None,moudle_list=['switch','curtain','singleColorTemperatureLight','dualColorTemperatureLight','RGBWLight','RGBCWLight'])

            for hadevice in _hadevices:
                _LOGGER.debug(hadevice)
                product = hadevice['product']
                product.set_parent_device_id(self._intreIot_client._device_id)
                productkey = self.get_productKey_by_modules(product.get_modules())
                if productkey is not None:
                    product.set_productKey(productkey)
                    self._intre_products.append(product)

            _LOGGER.debug(f'self._intre_devicesn_add={self._intre_devicesn_add}')
            _LOGGER.debug(f'self._sync_product_info={self._sync_product_info}')
            #4.遍历所有已经创建模型的设备，针对还没添加到cloud的，做添加操作，添加成功后，记录到_sync_product_info，添加后的deviceSN 记录到_intre_devicesn_add
            for product in self._intre_products:
                device_id = next((info['deviceId'] for info in self._sync_product_info 
                            if info.get('deviceSn') == product.deviceSn and 'deviceId' in info),
                                None  # 未找到时返回None
                            )
                if device_id is None:
                    product_info =product.get_product_json()
                    _LOGGER.debug("product_info11")
                    _LOGGER.debug(product_info)
                    rspdata=await self._intreIot_client._http_client.add_sub_device(product_info=product_info)  
                    if rspdata is not None:#添加成功
                        product._deviceId = rspdata.get('deviceId', None)
                        _LOGGER.debug(f'add to cloud product.deviceSn={product.deviceSn}')
                        sync_info={}
                        sync_info['deviceId']=product._deviceId
                        sync_info['deviceSn']=product_info['deviceSn']

                        self._sync_product_info.append(sync_info)
                        self._intre_devicesn_add.append(product.deviceSn)

                        dynamic_info =product.get_dynamic_module_json()
                        rsp= [module["instanceModuleKey"] for module in dynamic_info["dynamicModuleList"]]
                        await self._intreIot_client._http_client.add_dynamic_module(dynamic_info=dynamic_info)  
                    else:
                        product._deviceId = None
                else:
                    product._deviceId = device_id
                    if product.deviceSn not in self._intre_devicesn_add:
                        self._intre_devicesn_add.append(product.deviceSn)

            await self._storage.update_user_config_async(
                        uid=self._config_entry.entry_id, cloud_server=self._cloud_server,
                        config={'sync_product_info': self._sync_product_info})
            _LOGGER.debug(f'1111self._sync_product_info={self._sync_product_info}')
            _LOGGER.debug(f'self._intre_devicesn_sub={self._intre_devicesn_sub}')
            #5.遍历所有已经添加到cloud的设备，针对还未订阅的，做订阅操作
            for product in self._intre_products:
                if product.deviceSn in self._intre_devicesn_add:#已经添加到云平台
                    if product.deviceSn not in self._intre_devicesn_sub:

                        haProVerInfo =product.get_haProVerInfo_json()
                        _LOGGER.debug("haProVerInfo")
                        _LOGGER.debug(haProVerInfo)
                        await self._intreIot_client._http_client.update_ha_product_version(haProVerInfo=haProVerInfo)
                        batch_modules = product.get_modules_prop_json()
                        
                        prop_set_topic:str = f'{MQTT_ToH}device/{product.productKey}/{product.deviceId}/down/tls/property/set'
                        self._intreIot_client.sub_prop_set(topic=prop_set_topic,handler=product.prop_set_callback)
                        _LOGGER.debug(f"订阅的主题是111: {prop_set_topic}")  # 打印订阅的 topic
                        
                        service_call_topic:str = f'{MQTT_ToH}device/{product.productKey}/{product.deviceId}/down/tls/service/call'
                        self._intreIot_client.sub_service_call(topic=service_call_topic,handler=product.service_call_callback)
                        _LOGGER.debug(f"订阅的主题是222: {service_call_topic}")  # 打印订阅的 topic                          
                        
                        bacth_service_prop_topic:str = f'{MQTT_ToH}device/{product.productKey}/{product.deviceId}/down/tls/batch/property/service/set'
                        self._intreIot_client.sub_bacth_service_prop(topic=bacth_service_prop_topic,handler=product.bacth_service_prop_callback)
                        self._intre_devicesn_sub.append(product.deviceSn)

                        await self._intreIot_client.report_batch_module_prop_async(productkey=product.productKey,deviceid=product.deviceId,batch_modules=batch_modules)

                        down_data_define_report_reply_topic:str = f'{MQTT_ToH}device/{product.productKey}/{product.deviceId}/down/tls/data-define/report-reply'
                        self._intreIot_client.down_data_define_report_reply(topic=down_data_define_report_reply_topic,handler=self.down_data_define_report_reply_topic_callback)
                        down_tls_event_report_reply_topic:str = f'{MQTT_ToH}device/{product.productKey}/{product.deviceId}/down/tls/event/report-reply'
                        self._intreIot_client.down_tls_event_report_reply(topic=down_tls_event_report_reply_topic,handler=self.down_tls_event_report_reply_topic_callback)
                        '''
                        down_tls_property_report_reply_topic:str = f'{MQTT_ToH}device/{product.productKey}/{product.deviceId}/down/tls/property/report-reply'
                        self._intreIot_client.down_tls_property_report_reply(topic=down_tls_property_report_reply_topic,handler=self.down_tls_property_report_reply_topic_callback)
                        _LOGGER.debug(f"订阅的主题是333: {down_tls_event_report_reply_topic}")  # 打印订阅的 topic   
                        '''
        '''
        # 获取状态并打印
        device_status = await self.get_ha_device_status(HA_IP, ENTITY_ID, LONG_LIVED_TOKEN)
        _LOGGER.debug(f"HA子设备 - 在线状态: {device_status['online_status']}, 开关状态: {device_status['switch_state']}")
        '''                  
        self.__request_refresh_scene_device_info(30)
        return True


@staticmethod
async def get_intress_instance_async(
    hass: HomeAssistant, config_entry:ConfigEntry,
    persistent_notify: Optional[Callable[[str, str, str], None]] = None
) -> IntreManagementEngine:
    entry_id = config_entry.entry_id
    entry_data = dict(config_entry.data)
    entry_data['storage_path']=hass.config.path('.storage', DOMAIN)
    if entry_id is None:
        _LOGGER.info('invalid entry_id')
    
    intre_ss:IntreManagementEngine = None
    
    if a := hass.data[DOMAIN].get('intre_ss', {}).get(entry_id, None):
        _LOGGER.debug('instance exist, %s', entry_id)
        intre_ss = a
        await intre_ss.init_async()
    else:

        if entry_data is None:
            _LOGGER.info('config_entryis None')
        
        # Get running loop
        loop: asyncio.AbstractEventLoop = asyncio.get_running_loop()
        if loop is None:
            _LOGGER.info('loop is None')

        #IntreIoT ha
        intre_ha:Optional[IntreIoTStorage] = hass.data[DOMAIN].get(
            'intre_ha', None)
        if not intre_ha:
            intre_ha = IntreIotHa(
            hass=hass,
            auto_sync=False,
            loop=loop
            )
            _LOGGER.info('create intre_ha instance')
        
        #IntreIoT storage
        storage: Optional[IntreIoTStorage] = hass.data[DOMAIN].get(
            'intreiot_storage', None)
        if not storage:
            storage = IntreIoTStorage(
            root_path=entry_data['storage_path'], loop=loop)
            hass.data[DOMAIN]['intreiot_storage'] = storage
            _LOGGER.info('create intreiot_storage instance')   

        # IntreIoT network
        network: Optional[IntreIoTNetwork] = hass.data[DOMAIN].get(
            'intreiot_network', None)
        if not network:
            network = IntreIoTNetwork(
                refresh_interval=NETWORK_REFRESH_INTERVAL,
                loop=loop)
            hass.data[DOMAIN]['intreiot_network'] = network
            await network.init_async()
            _LOGGER.info('create intreiot_network instance')

        # IntreIoT client
        intreIot_client: Optional[IntreIoTClient] = hass.data[DOMAIN].get(
            'intreIot_client', None)
        if not intreIot_client:
            intreIot_client = IntreIoTClient(entry_id=entry_id,
                entry_data=entry_data,
                network=network,
                hass=hass,
                config_entry=config_entry,
                loop=loop
            )
            hass.data[DOMAIN]['intreIot_clients'] = intreIot_client
            await intreIot_client.init_async()
            _LOGGER.info('create intreIot_client instance')
        
        # IntreIoT intress
        intre_ss:IntreManagementEngine =IntreManagementEngine(
            hass=hass,
            intreIot_client=intreIot_client,
            storage=storage,
            config_entry=config_entry,
            intre_ha=intre_ha
        )
    
        intreIot_client.persistent_notify = persistent_notify
        hass.data[DOMAIN]['intre_ss'].setdefault(entry_id, intre_ss)
        _LOGGER.debug('new intre_ss instance, %s, %s', entry_id, entry_data)
        await intre_ss.init_async()
        
    return intre_ss