import importlib
import logging
import os
import sys
import asyncio
import json
import unicodedata
from homeassistant.config_entries import ConfigEntries
from homeassistant.helpers import device_registry, entity_registry
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from typing import Any, Callable, Optional, final
from .intreIot_ha import IntreIotHa
from .intreIot_module import (IntreIoTProduct,IntreIoTModule)
from .const  import (DOMAIN, SUPPORTED_PLATFORMS,MODULE_PRIORITY_DB,PRODUCT_KEY_DB,NETWORK_REFRESH_INTERVAL)

from .intreIot_client import IntreIoTClient
from .intreIot_network import IntreIoTNetwork
from .intreIot_storage import IntreIoTStorage
from collections import Counter

_LOGGER = logging.getLogger(__name__)


class  IntreManagementEngine():
    _main_loop: asyncio.AbstractEventLoop
    _intre_ha:IntreIotHa
    _intre_products:list[IntreIoTProduct]
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
    _get_cloud_scene_entity_id_list:list
    _device_entity_id_list:list
    _rspdata:list
    _HaDeviceSN:list
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
        self._get_cloud_scene_entity_id_list = []
        self._device_entity_id_list = []
        self._rspdata = []
        self._HaDeviceSN = []
        self._product_device_id = []
    async def init_async(self) -> None:
        
        self.__request_refresh_scene_device_info(30)
        config_data={}
        #config_data['_hadevices']=self._hadevices
        self._hass.data[DOMAIN]['config_data']=config_data

        await self._hass.config_entries.async_forward_entry_setups(self._config_entry, ['notify'])  
        
        '''
        #获取HA 平台所有子设备
        self._hadevices=self._intre_ha.get_device_list()

        #数据存储
        config_data={}
        config_data['_hadevices']=self._hadevices
        self._hass.data[DOMAIN]['config_data']=config_data

        await self._hass.config_entries.async_forward_entry_setups(self._config_entry, ['notify'])  

        _LOGGER.debug('config end')

        #确认每一个HA平台下的设备映射到intre平台下设备的product key
        for hadevice in self._hadevices:
            _LOGGER.debug(hadevice)
            product = hadevice['product']
            product.set_parent_device_id(self._intreIot_client._device_id)
            productkey=self.get_productKey_by_modules(product.get_modules())
            if productkey is not None:
                product.set_productKey(productkey)
                self._intre_products.append(product)
        _LOGGER.debug(self._intre_products)
        _LOGGER.debug(f"config end222当前_intre_products数量: {len(self._intre_products)}")
        _LOGGER.error('config end222')
        self._intre_ha.sub_device_state(self.state_changed_callback)
        self.__request_refresh_scene_device_info(40)
        #self.__request_refresh_device_info(5)
        '''

    async def setup_devices_and_forward_setup(self):
        from ..notify import (notify_async_forward_entry_setups)
        """设置设备并转发配置项"""
        # 获取设备列表
        self._intre_products=[]
        self._hadevices = self._intre_ha.get_device_list()
        
        # 存储配置数据
        config_data = {'_hadevices': self._hadevices}
        self._hass.data[DOMAIN]['config_data'] = config_data
        
        
        _LOGGER.debug('config end')
        #await self._hass.config_entries.async_unforward_entry_setups(self._config_entry, ['notify'])
        #await self._hass.config_entries.async_forward_entry_setups(self._config_entry, [])
        #await self._hass.config_entries.async_forward_entry_setups(self._config_entry, ['notify'])  
        await notify_async_forward_entry_setups(hass=self._hass,config_entry=self._config_entry,async_add_entities=None,moudle_list=['switch','curtain','singleColorTemperatureLight','dualColorTemperatureLight','RGBWLight','RGBCWLight','event'])
        # 处理设备产品密钥映射
        for hadevice in self._hadevices:
            _LOGGER.debug(hadevice)
            product = hadevice['product']
            product.set_parent_device_id(self._intreIot_client._device_id)
            productkey = self.get_productKey_by_modules(product.get_modules())
            if productkey is not None:
                product.set_productKey(productkey)
                self._intre_products.append(product)
        self._intre_ha.sub_device_state(self.state_changed_callback)
        _LOGGER.debug(f"CON当前_intre_products数量: {len(self._intre_products)}")


    def bacth_service_call_req(self,batch_serice_call_data:list)->None:
        _LOGGER.debug(f"batch_serice_call_data: {batch_serice_call_data}") 
    #情景   
    def add_scene_module_json(self,name:str,entity_id:str)->dict:
        for product in self._intre_products:
            product_info =product.get_product_json()
            parent_device_id = product_info["parentDeviceId"]
            #_LOGGER.error('676767676767: %s',parent_device_id )
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
                    "deviceId":parent_device_id,
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
            
    async def sync_scenes_to_cloud(self)->None:
        _LOGGER.debug('sync_scenes_to_cloud')
        
        self._user_config = await self._storage.load_user_config_async(
                uid=self._config_entry.entry_id, cloud_server=self._cloud_server)

        self._scene_entity_id_list = self._user_config.get("coself._scene_entity_id_list", [])
        _LOGGER.error('同步到 self._scene_entity_id_list: %s', json.dumps(self._scene_entity_id_list, ensure_ascii=False))
        await self._storage.update_user_config_async(
            uid=self._config_entry.entry_id, cloud_server=self._cloud_server,
            config={'coself._scene_entity_id_list': self._scene_entity_id_list})
        
        scenes = [state for state in self._hass.states.async_all() if state.domain == 'scene']
        current_scene_entity_ids = [scene.entity_id for scene in scenes]
        # 清理无效的实体 ID
        for entity_id in self._scene_entity_id_list.copy():  # 使用 copy() 避免在迭代过程中修改列表
            if entity_id not in current_scene_entity_ids:
                self._scene_entity_id_list.remove(entity_id)
                #_LOGGER.debug(f"Removed invalid scene entity_id: {entity_id}")

        for scene in scenes: 
             #_LOGGER.debug(f"synccloudName: {scene.name}, Entity ID: {scene.entity_id}")
             Scene_Entity_id = scene.entity_id
             if Scene_Entity_id not in self._scene_entity_id_list:
                self._scene_entity_id_list.append(Scene_Entity_id)
                self._user_config = await self._storage.load_user_config_async(
                    uid=self._config_entry.entry_id, cloud_server=self._cloud_server)

                #_LOGGER.error('user config, %s', json.dumps(self._user_config))
                await self._storage.update_user_config_async(
                    uid=self._config_entry.entry_id, cloud_server=self._cloud_server,
                    config={'coself._scene_entity_id_list': self._scene_entity_id_list})
                #_LOGGER.error('Updated self._scene_entity_id_list: %s', json.dumps(self._scene_entity_id_list, ensure_ascii=False))

                scenes_data = self.add_scene_module_json(name=scene.name,entity_id=scene.entity_id)
                await self._intreIot_client._http_client.add_scene_module(scene_info=scenes_data)
             else:
                 _LOGGER.error('scenes_to_cloud未有新情景')


        rsp = await self._intreIot_client._http_client.get_scene_module()
        #检查获取到的云端情景列表
        if isinstance(rsp, dict) and "sceneList" in rsp and isinstance(rsp["sceneList"], list):
            self._get_cloud_scene_entity_id_list = [scene["identifier"] for scene in rsp["sceneList"]]
        else:
            self._get_cloud_scene_entity_id_list = []
            _LOGGER.debug("Error: rsp['sceneList'] is not a valid list or rsp is not a dictionary.")
        _LOGGER.error('_get_cloud_scene_entity_id_list: %s', json.dumps(self._get_cloud_scene_entity_id_list, ensure_ascii=False))
        _LOGGER.debug('_scene_entity_id_list: %s', json.dumps(self._scene_entity_id_list, ensure_ascii=False))
        cloud_only = [x for x in self._get_cloud_scene_entity_id_list 
              if x not in self._scene_entity_id_list]  
        _LOGGER.error('cloud_only: %s', json.dumps(cloud_only, ensure_ascii=False))
        if cloud_only:
            for scene in cloud_only: 
             scenes_data = self.delete_scene_module_json(entity_id=scene)
             #_LOGGER.debug(json.dumps(scenes_data))
             await self._intreIot_client._http_client.delete_scene_module(identifier=scenes_data)
        '''
        
        scenes = [state for state in self._hass.states.async_all() if state.domain == 'scene']  
        for scene in scenes: 
             _LOGGER.debug(f"synccloudEntity ID: {scene.entity_id}")
             scenes_data = self.delete_scene_module_json(entity_id=scene.entity_id)
             _LOGGER.debug(json.dumps(scenes_data))
             await self._intreIot_client._http_client.delete_scene_module(identifier=scenes_data)      
        '''     
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

    async def sync_products_to_cloud(self)->None:
        _LOGGER.debug('sync_products_to_cloud')
        self._user_config = await self._storage.load_user_config_async(
                uid=self._config_entry.entry_id, cloud_server=self._cloud_server)

        self._rspdata = self._user_config.get("device._device_entity_id_list", [])
        self._product_device_id = self._user_config.get("product_device_id", [])
        self._HaDeviceSN = self._user_config.get("HaDeviceSN", [])
        #_LOGGER.error('user config, %s', json.dumps(self._user_config))
        _LOGGER.error('同步到 self._rspdata: %s', json.dumps(self._rspdata, ensure_ascii=False))
        _LOGGER.error('同步到 product_device_id: %s', json.dumps(self._product_device_id, ensure_ascii=False))
        _LOGGER.error('同步到 HaDeviceSN: %s', json.dumps(self._HaDeviceSN, ensure_ascii=False))

        
        _hadevices = self._hass.data[DOMAIN]['config_data']['_hadevices']
        #_LOGGER.debug(json.dumps(product_info))
        for hadevice in _hadevices:
            entitys = hadevice['entitys']
            for entity in entitys:
                if entity['entry'].entity_id.split(".")[0] in ['light', 'switch','cover','event']:
                    getha_entity_id = entity['entry'].entity_id
                    if getha_entity_id not in self._device_entity_id_list:
                        self._device_entity_id_list.append(getha_entity_id)
        

        #_LOGGER.error('1111 self._device_entity_id_list: %s',json.dumps(self._device_entity_id_list, ensure_ascii=False))
        #_LOGGER.error('1111 self._rspdata: %s',json.dumps(self._rspdata, ensure_ascii=False))
        flatten_rspdata = [item for sublist in self._rspdata for item in sublist] 
        
        if set(flatten_rspdata) == set(self._device_entity_id_list):
            _LOGGER.debug('相等')
        else:
            _LOGGER.debug(f"当前_intre_products数量: {len(self._intre_products)}")
            if self._intre_products:
                _LOGGER.error('同步到 HaDeviceSN: %s', json.dumps(self._HaDeviceSN, ensure_ascii=False))
                for product in self._intre_products:
                    _LOGGER.debug('---------1------------------------------------')
                    product_info =product.get_product_json()
                    _LOGGER.debug(f"设备SN: {product_info['deviceSn']}")  

                    if product_info['deviceSn'] not in self._HaDeviceSN:
                        self._HaDeviceSN.append(product_info['deviceSn']) 
                        _LOGGER.error('同步到 HaDeviceSN22222: %s', json.dumps(self._HaDeviceSN, ensure_ascii=False))


                        #_LOGGER.debug(json.dumps(product_info))
                        rspdata=await self._intreIot_client._http_client.add_sub_device(product_info=product_info)
                        #product._deviceId=rspdata.get('deviceId',None)
                        #_LOGGER.debug('--------------------------------------------------')
                        
                        # 修改后
                        if rspdata is not None:
                            product._deviceId = rspdata.get('deviceId', None)
                            _LOGGER.debug(product._deviceId)
                        else:
                            # 处理 rspdata 为 None 的情况
                            product._deviceId = None
                            # 可以添加日志记录错误
                            _LOGGER.debug("rspdata is None, cannot get deviceId")
                        if product._deviceId not in self._product_device_id:
                            self._product_device_id.append(product._deviceId)
                        dynamic_info =product.get_dynamic_module_json()
                        #_LOGGER.debug(json.dumps(dynamic_info))
                        #_LOGGER.debug("instanceModuleKey111 的值列表：%s", json.dumps(self._rspdata, ensure_ascii=False))
                        rsp= [module["instanceModuleKey"] for module in dynamic_info["dynamicModuleList"]]
                        if rsp not in self._rspdata:
                            self._rspdata.append(rsp)
                        
                        #_LOGGER.debug("instanceModuleKey 的值列表：%s", json.dumps(self._rspdata, ensure_ascii=False))
                        #_LOGGER.error('22222 self._device_entity_id_list: %s',json.dumps(self._device_entity_id_list, ensure_ascii=False))
                        await self._intreIot_client._http_client.add_dynamic_module(dynamic_info=dynamic_info)
                        _LOGGER.debug('Initializing55555555555555...')
        _LOGGER.error('33同步到 self._rspdata: %s', json.dumps(self._rspdata, ensure_ascii=False))
        _LOGGER.error('33同步到 product_device_id: %s', json.dumps(self._product_device_id, ensure_ascii=False))
        _LOGGER.error('33同步到 HaDeviceSN: %s', json.dumps(self._HaDeviceSN, ensure_ascii=False))

        #_LOGGER.error('user config, %s', json.dumps(self._user_config))
        await self._storage.update_user_config_async(
            uid=self._config_entry.entry_id, cloud_server=self._cloud_server,
            config={'device._device_entity_id_list': self._rspdata,'product_device_id':self._product_device_id,'HaDeviceSN': self._HaDeviceSN})    
        #_LOGGER.error('2222 self._rspdata: %s',json.dumps(self._rspdata, ensure_ascii=False))
        #_LOGGER.error('2222 self._product_device_id: %s',json.dumps(self._product_device_id, ensure_ascii=False))
        _LOGGER.debug(f"333当前_intre_products数量: {len(self._intre_products)}")
        
        for product, device_id in zip(self._intre_products, self._product_device_id):
            product_info =product.get_product_json()
            parent_device_id = product_info["parentDeviceId"]
            product._deviceId = device_id
            _LOGGER.debug(f"Parent Device ID: {parent_device_id}") 
            prop_set_topic:str = f'{MQTT_ToH}device/{product.productKey}/{product.deviceId}/down/tls/property/set'
            self._intreIot_client.sub_prop_set(topic=prop_set_topic,handler=product.prop_set_callback)
            _LOGGER.debug(f"订阅的主题是111: {prop_set_topic}")  # 打印订阅的 topic
            
            service_call_topic:str = f'{MQTT_ToH}device/{product.productKey}/{product.deviceId}/down/tls/service/call'
            self._intreIot_client.sub_service_call(topic=service_call_topic,handler=product.service_call_callback)
            _LOGGER.debug(f"订阅的主题是222: {service_call_topic}")  # 打印订阅的 topic                          
            
            bacth_service_prop_topic:str = f'{MQTT_ToH}device/{product.productKey}/{product.deviceId}/down/tls/batch/property/service/set'
            self._intreIot_client.sub_bacth_service_prop(topic=bacth_service_prop_topic,handler=product.service_call_callback)
        
        bacth_service_prop_topic:str = f'{MQTT_ToH}device/Intre.BGZ001/{parent_device_id}/down/tls/batch/property/service/set'
        self._intreIot_client.sub_bacth_service_prop(topic=bacth_service_prop_topic,handler=self.ha_bacth_service_prop_callback)
        _LOGGER.debug(f"订阅的主题是333: {bacth_service_prop_topic}")  # 打印订阅的 topic      
    
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
    
    async def report_event_async(self,productkey:str,deviceid:str,modulekey:str,eventkey:str,event_value:str)->None:
        await self._intreIot_client.report_event_async(productkey=productkey,deviceid=deviceid,modulekey=modulekey,eventkey=eventkey,event_value=event_value)
        _LOGGER.debug(
            f"准备上报属性: productkey={productkey}, deviceid={deviceid}, "
            f"modulekey={modulekey}, eventkey={eventkey}, event_value={event_value}"   
        )
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
    async def AAAA(self) -> bool:
        await self.setup_devices_and_forward_setup()
        _LOGGER.debug('__request_refresh_scene_device_info')
        
        self._user_config = await self._storage.load_user_config_async(
                uid=self._config_entry.entry_id, cloud_server=self._cloud_server)

        self._scene_entity_id_list = self._user_config.get("coself._scene_entity_id_list", [])
        #_LOGGER.error('同步到 self._scene_entity_id_list: %s', json.dumps(self._scene_entity_id_list, ensure_ascii=False))
        await self._storage.update_user_config_async(
            uid=self._config_entry.entry_id, cloud_server=self._cloud_server,
            config={'coself._scene_entity_id_list': self._scene_entity_id_list})
        
        scenes = [state for state in self._hass.states.async_all() if state.domain == 'scene']
        current_scene_entity_ids = [scene.entity_id for scene in scenes]
        # 清理无效的实体 ID
        for entity_id in self._scene_entity_id_list.copy():  # 使用 copy() 避免在迭代过程中修改列表
            if entity_id not in current_scene_entity_ids:
                self._scene_entity_id_list.remove(entity_id)
                #_LOGGER.debug(f"Removed invalid scene entity_id: {entity_id}")

        for scene in scenes: 
             #_LOGGER.debug(f"synccloudName: {scene.name}, Entity ID: {scene.entity_id}")
             Scene_Entity_id = scene.entity_id
             if Scene_Entity_id not in self._scene_entity_id_list:
                self._scene_entity_id_list.append(Scene_Entity_id)
                self._user_config = await self._storage.load_user_config_async(
                    uid=self._config_entry.entry_id, cloud_server=self._cloud_server)

                #_LOGGER.error('user config, %s', json.dumps(self._user_config))
                await self._storage.update_user_config_async(
                    uid=self._config_entry.entry_id, cloud_server=self._cloud_server,
                    config={'coself._scene_entity_id_list': self._scene_entity_id_list})
                #_LOGGER.error('Updated self._scene_entity_id_list: %s', json.dumps(self._scene_entity_id_list, ensure_ascii=False))

                scenes_data = self.add_scene_module_json(name=scene.name,entity_id=scene.entity_id)
                await self._intreIot_client._http_client.add_scene_module(scene_info=scenes_data)
             else:
                 _LOGGER.error('scenes_to_cloud未有新情景')

        rsp = await self._intreIot_client._http_client.get_scene_module()
        #检查获取到的云端情景列表
        if isinstance(rsp, dict) and "sceneList" in rsp and isinstance(rsp["sceneList"], list):
            self._get_cloud_scene_entity_id_list = [scene["identifier"] for scene in rsp["sceneList"]]
        else:
            self._get_cloud_scene_entity_id_list = []
            #_LOGGER.debug("Error: rsp['sceneList'] is not a valid list or rsp is not a dictionary.")
        #删除app重复的情景
        '''
        counter = Counter(self._get_cloud_scene_entity_id_list)
        duplicates = []
        for x in self._get_cloud_scene_entity_id_list:
            if counter[x] > 1:  # 如果该元素是重复的
                duplicates.append(x)  # 添加到结果列表
                counter[x] -= 1  # 减少计数
                if counter[x] <= (counter[x] // 2):  # 保留一半的重复项
                    counter[x] = 0  # 计数为 0 表示不再添加
        #_LOGGER.debug('duplicates: %s', json.dumps(duplicates, ensure_ascii=False))
        if duplicates:
            for scene in duplicates: 
             scenes_data = self.delete_scene_module_json(entity_id=scene)
             await self._intreIot_client._http_client.delete_scene_module(identifier=scenes_data)
        '''
        _LOGGER.debug('_get_cloud_scene_entity_id_list: %s', json.dumps(self._get_cloud_scene_entity_id_list, ensure_ascii=False))
        _LOGGER.debug('_scene_entity_id_list: %s', json.dumps(self._scene_entity_id_list, ensure_ascii=False))
        cloud_only = [x for x in self._get_cloud_scene_entity_id_list 
              if x not in self._scene_entity_id_list]  
        _LOGGER.debug('cloud_only: %s', json.dumps(cloud_only, ensure_ascii=False))
        if cloud_only:
            for scene in cloud_only: 
             scenes_data = self.delete_scene_module_json(entity_id=scene)
             await self._intreIot_client._http_client.delete_scene_module(identifier=scenes_data)
            
        #删除app重复的情景END
        ##################################################################################################
        _LOGGER.debug('sync_products_to_cloud')


        self._user_config = await self._storage.load_user_config_async(
                uid=self._config_entry.entry_id, cloud_server=self._cloud_server)
        self._HaDeviceSN = self._user_config.get("HaDeviceSN", [])
        self._product_device_id = self._user_config.get("product_device_id", [])
        #_LOGGER.error('user config, %s', json.dumps(self._user_config))
        #_LOGGER.error('步到 self._rspdata: %s', json.dumps(self._rspdata, ensure_ascii=False))
        if self._intre_products:
            _LOGGER.error('同步到 HaDeviceSN: %s', json.dumps(self._HaDeviceSN, ensure_ascii=False))
            for product in self._intre_products:
                _LOGGER.debug('---------1------------------------------------')
                product_info =product.get_product_json()
                parent_device_id = product_info["parentDeviceId"]
                _LOGGER.debug(f"设备SN: {product_info['deviceSn']}")  
                _LOGGER.debug(f"1111Parent Device ID: {parent_device_id}") 
                if product_info['deviceSn'] not in self._HaDeviceSN:
                    self._HaDeviceSN.append(product_info['deviceSn']) 
                    _LOGGER.error('同步到 HaDeviceSN22222: %s', json.dumps(self._HaDeviceSN, ensure_ascii=False))

                    #_LOGGER.debug(f"99999999Processing device: {product_info['deviceName']} ({product_info['deviceSn']})")
                    #_LOGGER.debug(json.dumps(product_info))
                    rspdata=await self._intreIot_client._http_client.add_sub_device(product_info=product_info)
                    #product._deviceId=rspdata.get('deviceId',None)
                    # 修改后
                    if rspdata is not None:
                        product._deviceId = rspdata.get('deviceId', None)
                        #_LOGGER.debug(product._deviceId)
                    else:
                        # 处理 rspdata 为 None 的情况
                        product._deviceId = None
                        # 可以添加日志记录错误
                        #_LOGGER.debug("rspdata is None494, cannot get deviceId")
                    if product._deviceId not in self._product_device_id:
                        self._product_device_id.append(product._deviceId) 
                    dynamic_info =product.get_dynamic_module_json()
                    #_LOGGER.debug(json.dumps(dynamic_info))
                    rsp= [module["instanceModuleKey"] for module in dynamic_info["dynamicModuleList"]]
                    #_LOGGER.debug(rsp)
                    #_LOGGER.error('555555555 self._rspdata: %s',json.dumps(self._rspdata, ensure_ascii=False))
                    if rsp not in self._rspdata:
                        self._rspdata.append(rsp)
                        #_LOGGER.error('44444 self._rspdata: %s',json.dumps(self._rspdata, ensure_ascii=False))
                    await self._intreIot_client._http_client.add_dynamic_module(dynamic_info=dynamic_info)
                    #_LOGGER.debug("instanceModuleKey 的值列表：%s", json.dumps(self._rspdata, ensure_ascii=False))
                    #_LOGGER.error('22222 self._device_entity_id_list: %s',json.dumps(self._device_entity_id_list, ensure_ascii=False))
                    #_LOGGER.error('2222 self._rspdata: %s',json.dumps(self._rspdata, ensure_ascii=False)) 
            _LOGGER.error('同步到 HaDeviceSN111111: %s', json.dumps(self._HaDeviceSN, ensure_ascii=False))
            _LOGGER.error('33同步到 product_device_id: %s', json.dumps(self._product_device_id, ensure_ascii=False))
        for product, device_id in zip(self._intre_products, self._product_device_id):
            product_info =product.get_product_json()
            #parent_device_id = product_info["parentDeviceId"]
            product._deviceId = device_id
            _LOGGER.debug(f"Parent Device ID: {parent_device_id}") 
            prop_set_topic:str = f'{MQTT_ToH}device/{product.productKey}/{product.deviceId}/down/tls/property/set'
            self._intreIot_client.sub_prop_set(topic=prop_set_topic,handler=product.prop_set_callback)
            _LOGGER.debug(f"订阅的主题是111: {prop_set_topic}")  # 打印订阅的 topic
            
            service_call_topic:str = f'{MQTT_ToH}device/{product.productKey}/{product.deviceId}/down/tls/service/call'
            self._intreIot_client.sub_service_call(topic=service_call_topic,handler=product.service_call_callback)
            _LOGGER.debug(f"订阅的主题是222: {service_call_topic}")  # 打印订阅的 topic                          
            
            bacth_service_prop_topic:str = f'{MQTT_ToH}device/{product.productKey}/{product.deviceId}/down/tls/batch/property/service/set'
            self._intreIot_client.sub_bacth_service_prop(topic=bacth_service_prop_topic,handler=product.service_call_callback)
        _LOGGER.debug(f"2222Parent Device ID: {parent_device_id}") 
        bacth_service_prop_topic:str = f'{MQTT_ToH}device/Intre.BGZ001/{parent_device_id}/down/tls/batch/property/service/set'
        self._intreIot_client.sub_bacth_service_prop(topic=bacth_service_prop_topic,handler=self.ha_bacth_service_prop_callback)
        _LOGGER.debug(f"订阅的主题是333: {bacth_service_prop_topic}")  # 打印订阅的 topic   
        #_LOGGER.error('user config, %s', json.dumps(self._user_config))
        await self._storage.update_user_config_async(
            uid=self._config_entry.entry_id, cloud_server=self._cloud_server,
            config={'HaDeviceSN': self._HaDeviceSN,'product_device_id':self._product_device_id})
            #config={'device._device_entity_id_list': self._rspdata,'HaDeviceSN': self._HaDeviceSN})
        #_LOGGER.error('3333 self._rspdata: %s',json.dumps(self._rspdata, ensure_ascii=False)) 
        
        #self.__request_refresh_scene_device_info(30)
        '''
        _hadevices = self._hass.data[DOMAIN]['config_data']['_hadevices']
        #_LOGGER.debug(json.dumps(product_info))
        
        for hadevice in _hadevices:
            entitys = hadevice['entitys']
            for entity in entitys:
                if entity['entry'].entity_id.split(".")[0] in ['light', 'switch','cover','event']:
                    getha_entity_id = entity['entry'].entity_id
                    if getha_entity_id not in self._device_entity_id_list:
                        self._device_entity_id_list.append(getha_entity_id)
        
        #_LOGGER.error('1111 self._device_entity_id_list: %s',json.dumps(self._device_entity_id_list, ensure_ascii=False))
        #_LOGGER.error('1111 self._rspdata: %s',json.dumps(self._rspdata, ensure_ascii=False))
        flatten_rspdata = [item for sublist in self._rspdata for item in sublist] 
        #_LOGGER.error('flatten_rspdata: %s', json.dumps(flatten_rspdata, ensure_ascii=False)) 
        
        if set(flatten_rspdata) == set(self._device_entity_id_list):
            _LOGGER.debug('相等')
        else:
            _LOGGER.debug(f"当前_intre_products数量: {len(self._intre_products)}")
            if self._intre_products:
                _LOGGER.error('同步到 HaDeviceSN: %s', json.dumps(self._HaDeviceSN, ensure_ascii=False))
                for product in self._intre_products:
                    _LOGGER.debug('---------1------------------------------------')
                    product_info =product.get_product_json()
                    _LOGGER.debug(f"设备SN: {product_info['deviceSn']}")  

                    if product_info['deviceSn'] not in self._HaDeviceSN:
                        self._HaDeviceSN.append(product_info['deviceSn']) 
                        _LOGGER.error('同步到 HaDeviceSN22222: %s', json.dumps(self._HaDeviceSN, ensure_ascii=False))

                        #_LOGGER.debug(f"99999999Processing device: {product_info['deviceName']} ({product_info['deviceSn']})")
                        #_LOGGER.debug(json.dumps(product_info))
                        rspdata=await self._intreIot_client._http_client.add_sub_device(product_info=product_info)
                        #product._deviceId=rspdata.get('deviceId',None)
                        # 修改后
                        if rspdata is not None:
                            product._deviceId = rspdata.get('deviceId', None)
                            #_LOGGER.debug(product._deviceId)
                        else:
                            # 处理 rspdata 为 None 的情况
                            product._deviceId = None
                            # 可以添加日志记录错误
                            #_LOGGER.debug("rspdata is None494, cannot get deviceId")
                        dynamic_info =product.get_dynamic_module_json()
                        #_LOGGER.debug(json.dumps(dynamic_info))
                        rsp= [module["instanceModuleKey"] for module in dynamic_info["dynamicModuleList"]]
                        #_LOGGER.debug(rsp)
                        #_LOGGER.error('555555555 self._rspdata: %s',json.dumps(self._rspdata, ensure_ascii=False))
                        if rsp not in self._rspdata:
                            self._rspdata.append(rsp)
                            #_LOGGER.error('44444 self._rspdata: %s',json.dumps(self._rspdata, ensure_ascii=False))
                        await self._intreIot_client._http_client.add_dynamic_module(dynamic_info=dynamic_info)
                        #_LOGGER.debug("instanceModuleKey 的值列表：%s", json.dumps(self._rspdata, ensure_ascii=False))
                        #_LOGGER.error('22222 self._device_entity_id_list: %s',json.dumps(self._device_entity_id_list, ensure_ascii=False))
                        #_LOGGER.error('2222 self._rspdata: %s',json.dumps(self._rspdata, ensure_ascii=False)) 
                _LOGGER.error('同步到 HaDeviceSN111111: %s', json.dumps(self._HaDeviceSN, ensure_ascii=False))

        
        #_LOGGER.error('user config, %s', json.dumps(self._user_config))
        await self._storage.update_user_config_async(
            uid=self._config_entry.entry_id, cloud_server=self._cloud_server,
            config={'HaDeviceSN': self._HaDeviceSN})
            #config={'device._device_entity_id_list': self._rspdata,'HaDeviceSN': self._HaDeviceSN})
        #_LOGGER.error('3333 self._rspdata: %s',json.dumps(self._rspdata, ensure_ascii=False)) 
        
        self.__request_refresh_scene_device_info(40)
        '''
        return True
    @final
    async def refresh_device_async(self) -> bool:
        _LOGGER.debug('refresh_device_async')
        '''
        self._user_config = await self._storage.load_user_config_async(
                uid=self._config_entry.entry_id, cloud_server=self._cloud_server)
        #_LOGGER.error('user config, %s', json.dumps(self._user_config))
        #_LOGGER.error('同步到 self._device_entity_id_list: %s', json.dumps(self._device_entity_id_list, ensure_ascii=False))
        await self._storage.update_user_config_async(
            uid=self._config_entry.entry_id, cloud_server=self._cloud_server,
            config={'device._device_entity_id_list': self._device_entity_id_list})
        
        _hadevices = self._hass.data[DOMAIN]['config_data']['_hadevices']
        #_LOGGER.debug(json.dumps(product_info))
        for hadevice in _hadevices:
            entitys = hadevice['entitys']
            for entity in entitys:
                if entity['entry'].entity_id.split(".")[0] in ['light', 'switch','cover','event']:
                    getha_entity_id = entity['entry'].entity_id
                    if getha_entity_id not in self._device_entity_id_list:
                        self._device_entity_id_list.append(getha_entity_id)
        
                        self._user_config = await self._storage.load_user_config_async(
                            uid=self._config_entry.entry_id, cloud_server=self._cloud_server)

                        #_LOGGER.error('user config, %s', json.dumps(self._user_config))
                        await self._storage.update_user_config_async(
                            uid=self._config_entry.entry_id, cloud_server=self._cloud_server,
                            config={'device._device_entity_id_list': self._device_entity_id_list})
        #_LOGGER.error('1111 self._device_entity_id_list: %s',json.dumps(self._device_entity_id_list, ensure_ascii=False))
        #_LOGGER.error('1111 self._rspdata: %s',json.dumps(self._rspdata, ensure_ascii=False))
        flatten_rspdata = [item for sublist in self._rspdata for item in sublist] 
        
        if set(flatten_rspdata) == set(self._device_entity_id_list):
            _LOGGER.debug('相等')
        else:
            for product in self._intre_products:
    
                product_info =product.get_product_json()
                #_LOGGER.debug(json.dumps(product_info))
                rspdata=await self._intreIot_client._http_client.add_sub_device(product_info=product_info)
                product._deviceId=rspdata.get('deviceId',None)
                dynamic_info =product.get_dynamic_module_json()
                #_LOGGER.debug(json.dumps(dynamic_info))
                rsp= [module["instanceModuleKey"] for module in dynamic_info["dynamicModuleList"]]
                if rsp not in self._rspdata:
                    self._rspdata.append(rsp)
                #_LOGGER.debug("instanceModuleKey 的值列表：%s", json.dumps(self._rspdata, ensure_ascii=False))
                #_LOGGER.error('22222 self._device_entity_id_list: %s',json.dumps(self._device_entity_id_list, ensure_ascii=False))
                #_LOGGER.error('2222 self._rspdata: %s',json.dumps(self._rspdata, ensure_ascii=False)) 
                
                await self._intreIot_client._http_client.add_dynamic_module(dynamic_info=dynamic_info)
        '''    
        self.__request_refresh_device_info(5)
        return True         
    @final
    def __request_refresh_scene_device_info(self,delay_sec: int) -> None:
        if self._refresh_scene_device_timer:
            #_LOGGER.debug("AAAAAAAAAAAAAAAAAAAAAAAAAAAAA__request_refresh_scene_device_info 的值列表")
            self._refresh_scene_device_timer.cancel()
            self._refresh_scene_device_timer = None
        
        self._refresh_scene_device_timer = self._main_loop.call_later(
            delay_sec, lambda: self._main_loop.create_task(
                self.AAAA()))
    @final
    def __request_refresh_device_info(self,delay_sec: int) -> None:
        if self._refresh_device_timer:
            self._refresh_device_timer.cancel()
            self._refresh_device_timer = None
        
        self._refresh_scene_device_timer = self._main_loop.call_later(
            delay_sec, lambda: self._main_loop.create_task(
                self.refresh_device_async()))

    @final
    async def sync_ha_device_and_scene_cloud(self) -> bool:
        await self.setup_devices_and_forward_setup()
        _LOGGER.debug('__request_refresh_scene_device_info')
        
        self._user_config = await self._storage.load_user_config_async(
                uid=self._config_entry.entry_id, cloud_server=self._cloud_server)

        self._scene_entity_id_list = self._user_config.get("coself._scene_entity_id_list", [])
        #_LOGGER.error('同步到 self._scene_entity_id_list: %s', json.dumps(self._scene_entity_id_list, ensure_ascii=False))
        await self._storage.update_user_config_async(
            uid=self._config_entry.entry_id, cloud_server=self._cloud_server,
            config={'coself._scene_entity_id_list': self._scene_entity_id_list})
        
        scenes = [state for state in self._hass.states.async_all() if state.domain == 'scene']
        current_scene_entity_ids = [scene.entity_id for scene in scenes]
        # 清理无效的实体 ID
        for entity_id in self._scene_entity_id_list.copy():  # 使用 copy() 避免在迭代过程中修改列表
            if entity_id not in current_scene_entity_ids:
                self._scene_entity_id_list.remove(entity_id)
                #_LOGGER.debug(f"Removed invalid scene entity_id: {entity_id}")

        for scene in scenes: 
             #_LOGGER.debug(f"synccloudName: {scene.name}, Entity ID: {scene.entity_id}")
             Scene_Entity_id = scene.entity_id
             if Scene_Entity_id not in self._scene_entity_id_list:
                self._scene_entity_id_list.append(Scene_Entity_id)
                self._user_config = await self._storage.load_user_config_async(
                    uid=self._config_entry.entry_id, cloud_server=self._cloud_server)

                #_LOGGER.error('user config, %s', json.dumps(self._user_config))
                await self._storage.update_user_config_async(
                    uid=self._config_entry.entry_id, cloud_server=self._cloud_server,
                    config={'coself._scene_entity_id_list': self._scene_entity_id_list})
                #_LOGGER.error('Updated self._scene_entity_id_list: %s', json.dumps(self._scene_entity_id_list, ensure_ascii=False))

                scenes_data = self.add_scene_module_json(name=scene.name,entity_id=scene.entity_id)
                await self._intreIot_client._http_client.add_scene_module(scene_info=scenes_data)
             else:
                 _LOGGER.error('scenes_to_cloud未有新情景')

        rsp = await self._intreIot_client._http_client.get_scene_module()
        #检查获取到的云端情景列表
        if isinstance(rsp, dict) and "sceneList" in rsp and isinstance(rsp["sceneList"], list):
            self._get_cloud_scene_entity_id_list = [scene["identifier"] for scene in rsp["sceneList"]]
        else:
            self._get_cloud_scene_entity_id_list = []
            #_LOGGER.debug("Error: rsp['sceneList'] is not a valid list or rsp is not a dictionary.")
        #删除app重复的情景
        '''
        counter = Counter(self._get_cloud_scene_entity_id_list)
        duplicates = []
        for x in self._get_cloud_scene_entity_id_list:
            if counter[x] > 1:  # 如果该元素是重复的
                duplicates.append(x)  # 添加到结果列表
                counter[x] -= 1  # 减少计数
                if counter[x] <= (counter[x] // 2):  # 保留一半的重复项
                    counter[x] = 0  # 计数为 0 表示不再添加
        #_LOGGER.debug('duplicates: %s', json.dumps(duplicates, ensure_ascii=False))
        if duplicates:
            for scene in duplicates: 
             scenes_data = self.delete_scene_module_json(entity_id=scene)
             await self._intreIot_client._http_client.delete_scene_module(identifier=scenes_data)
        '''
        _LOGGER.debug('_get_cloud_scene_entity_id_list: %s', json.dumps(self._get_cloud_scene_entity_id_list, ensure_ascii=False))
        _LOGGER.debug('_scene_entity_id_list: %s', json.dumps(self._scene_entity_id_list, ensure_ascii=False))
        cloud_only = [x for x in self._get_cloud_scene_entity_id_list 
              if x not in self._scene_entity_id_list]  
        _LOGGER.debug('cloud_only: %s', json.dumps(cloud_only, ensure_ascii=False))
        if cloud_only:
            for scene in cloud_only: 
             scenes_data = self.delete_scene_module_json(entity_id=scene)
             await self._intreIot_client._http_client.delete_scene_module(identifier=scenes_data)
            
        #删除app重复的情景END
        ##################################################################################################
        _LOGGER.debug('sync_products_to_cloud')


        self._user_config = await self._storage.load_user_config_async(
                uid=self._config_entry.entry_id, cloud_server=self._cloud_server)
        self._HaDeviceSN = self._user_config.get("HaDeviceSN", [])
        self._product_device_id = self._user_config.get("product_device_id", [])
        #_LOGGER.error('user config, %s', json.dumps(self._user_config))
        #_LOGGER.error('步到 self._rspdata: %s', json.dumps(self._rspdata, ensure_ascii=False))
        if self._intre_products:
            _LOGGER.error('同步到 HaDeviceSN: %s', json.dumps(self._HaDeviceSN, ensure_ascii=False))
            for product in self._intre_products:
                _LOGGER.debug('---------1------------------------------------')
                product_info =product.get_product_json()
                parent_device_id = product_info["parentDeviceId"]
                _LOGGER.debug(f"设备SN: {product_info['deviceSn']}")  
                _LOGGER.debug(f"1111Parent Device ID: {parent_device_id}") 
                if product_info['deviceSn'] not in self._HaDeviceSN:
                    self._HaDeviceSN.append(product_info['deviceSn']) 
                    _LOGGER.error('同步到 HaDeviceSN22222: %s', json.dumps(self._HaDeviceSN, ensure_ascii=False))

                    #_LOGGER.debug(f"99999999Processing device: {product_info['deviceName']} ({product_info['deviceSn']})")
                    #_LOGGER.debug(json.dumps(product_info))
                    rspdata=await self._intreIot_client._http_client.add_sub_device(product_info=product_info)
                    #product._deviceId=rspdata.get('deviceId',None)
                    # 修改后
                    if rspdata is not None:
                        product._deviceId = rspdata.get('deviceId', None)
                        #_LOGGER.debug(product._deviceId)
                    else:
                        # 处理 rspdata 为 None 的情况
                        product._deviceId = None
                        # 可以添加日志记录错误
                        #_LOGGER.debug("rspdata is None494, cannot get deviceId")
                    if product._deviceId not in self._product_device_id:
                        self._product_device_id.append(product._deviceId) 
                    dynamic_info =product.get_dynamic_module_json()
                    #_LOGGER.debug(json.dumps(dynamic_info))
                    rsp= [module["instanceModuleKey"] for module in dynamic_info["dynamicModuleList"]]
                    #_LOGGER.debug(rsp)
                    #_LOGGER.error('555555555 self._rspdata: %s',json.dumps(self._rspdata, ensure_ascii=False))
                    if rsp not in self._rspdata:
                        self._rspdata.append(rsp)
                        #_LOGGER.error('44444 self._rspdata: %s',json.dumps(self._rspdata, ensure_ascii=False))
                    await self._intreIot_client._http_client.add_dynamic_module(dynamic_info=dynamic_info)
                    #_LOGGER.debug("instanceModuleKey 的值列表：%s", json.dumps(self._rspdata, ensure_ascii=False))
                    #_LOGGER.error('22222 self._device_entity_id_list: %s',json.dumps(self._device_entity_id_list, ensure_ascii=False))
                    #_LOGGER.error('2222 self._rspdata: %s',json.dumps(self._rspdata, ensure_ascii=False)) 
            _LOGGER.error('同步到 HaDeviceSN111111: %s', json.dumps(self._HaDeviceSN, ensure_ascii=False))
            _LOGGER.error('33同步到 product_device_id: %s', json.dumps(self._product_device_id, ensure_ascii=False))
        for product, device_id in zip(self._intre_products, self._product_device_id):
            product_info =product.get_product_json()
            #parent_device_id = product_info["parentDeviceId"]
            product._deviceId = device_id
            _LOGGER.debug(f"Parent Device ID: {parent_device_id}") 
            prop_set_topic:str = f'{MQTT_ToH}device/{product.productKey}/{product.deviceId}/down/tls/property/set'
            self._intreIot_client.sub_prop_set(topic=prop_set_topic,handler=product.prop_set_callback)
            _LOGGER.debug(f"订阅的主题是111: {prop_set_topic}")  # 打印订阅的 topic
            
            service_call_topic:str = f'{MQTT_ToH}/device/{product.productKey}/{product.deviceId}/down/tls/service/call'
            self._intreIot_client.sub_service_call(topic=service_call_topic,handler=product.service_call_callback)
            _LOGGER.debug(f"订阅的主题是222: {service_call_topic}")  # 打印订阅的 topic                          
            
            bacth_service_prop_topic:str = f'{MQTT_ToH}/device/{product.productKey}/{product.deviceId}/down/tls/batch/property/service/set'
            self._intreIot_client.sub_bacth_service_prop(topic=bacth_service_prop_topic,handler=product.service_call_callback)
        _LOGGER.debug(f"2222Parent Device ID: {parent_device_id}") 
        bacth_service_prop_topic:str = f'{MQTT_ToH}/device/Intre.BGZ001/{parent_device_id}/down/tls/batch/property/service/set'
        self._intreIot_client.sub_bacth_service_prop(topic=bacth_service_prop_topic,handler=self.ha_bacth_service_prop_callback)
        _LOGGER.debug(f"订阅的主题是333: {bacth_service_prop_topic}")  # 打印订阅的 topic   
        #_LOGGER.error('user config, %s', json.dumps(self._user_config))
        await self._storage.update_user_config_async(
            uid=self._config_entry.entry_id, cloud_server=self._cloud_server,
            config={'HaDeviceSN': self._HaDeviceSN,'product_device_id':self._product_device_id})
            #config={'device._device_entity_id_list': self._rspdata,'HaDeviceSN': self._HaDeviceSN})
        #_LOGGER.error('3333 self._rspdata: %s',json.dumps(self._rspdata, ensure_ascii=False)) 
        
        #self.__request_refresh_scene_device_info(30)
        '''
        _hadevices = self._hass.data[DOMAIN]['config_data']['_hadevices']
        #_LOGGER.debug(json.dumps(product_info))
        
        for hadevice in _hadevices:
            entitys = hadevice['entitys']
            for entity in entitys:
                if entity['entry'].entity_id.split(".")[0] in ['light', 'switch','cover','event']:
                    getha_entity_id = entity['entry'].entity_id
                    if getha_entity_id not in self._device_entity_id_list:
                        self._device_entity_id_list.append(getha_entity_id)
        
        #_LOGGER.error('1111 self._device_entity_id_list: %s',json.dumps(self._device_entity_id_list, ensure_ascii=False))
        #_LOGGER.error('1111 self._rspdata: %s',json.dumps(self._rspdata, ensure_ascii=False))
        flatten_rspdata = [item for sublist in self._rspdata for item in sublist] 
        #_LOGGER.error('flatten_rspdata: %s', json.dumps(flatten_rspdata, ensure_ascii=False)) 
        
        if set(flatten_rspdata) == set(self._device_entity_id_list):
            _LOGGER.debug('相等')
        else:
            _LOGGER.debug(f"当前_intre_products数量: {len(self._intre_products)}")
            if self._intre_products:
                _LOGGER.error('同步到 HaDeviceSN: %s', json.dumps(self._HaDeviceSN, ensure_ascii=False))
                for product in self._intre_products:
                    _LOGGER.debug('---------1------------------------------------')
                    product_info =product.get_product_json()
                    _LOGGER.debug(f"设备SN: {product_info['deviceSn']}")  

                    if product_info['deviceSn'] not in self._HaDeviceSN:
                        self._HaDeviceSN.append(product_info['deviceSn']) 
                        _LOGGER.error('同步到 HaDeviceSN22222: %s', json.dumps(self._HaDeviceSN, ensure_ascii=False))

                        #_LOGGER.debug(f"99999999Processing device: {product_info['deviceName']} ({product_info['deviceSn']})")
                        #_LOGGER.debug(json.dumps(product_info))
                        rspdata=await self._intreIot_client._http_client.add_sub_device(product_info=product_info)
                        #product._deviceId=rspdata.get('deviceId',None)
                        # 修改后
                        if rspdata is not None:
                            product._deviceId = rspdata.get('deviceId', None)
                            #_LOGGER.debug(product._deviceId)
                        else:
                            # 处理 rspdata 为 None 的情况
                            product._deviceId = None
                            # 可以添加日志记录错误
                            #_LOGGER.debug("rspdata is None494, cannot get deviceId")
                        dynamic_info =product.get_dynamic_module_json()
                        #_LOGGER.debug(json.dumps(dynamic_info))
                        rsp= [module["instanceModuleKey"] for module in dynamic_info["dynamicModuleList"]]
                        #_LOGGER.debug(rsp)
                        #_LOGGER.error('555555555 self._rspdata: %s',json.dumps(self._rspdata, ensure_ascii=False))
                        if rsp not in self._rspdata:
                            self._rspdata.append(rsp)
                            #_LOGGER.error('44444 self._rspdata: %s',json.dumps(self._rspdata, ensure_ascii=False))
                        await self._intreIot_client._http_client.add_dynamic_module(dynamic_info=dynamic_info)
                        #_LOGGER.debug("instanceModuleKey 的值列表：%s", json.dumps(self._rspdata, ensure_ascii=False))
                        #_LOGGER.error('22222 self._device_entity_id_list: %s',json.dumps(self._device_entity_id_list, ensure_ascii=False))
                        #_LOGGER.error('2222 self._rspdata: %s',json.dumps(self._rspdata, ensure_ascii=False)) 
                _LOGGER.error('同步到 HaDeviceSN111111: %s', json.dumps(self._HaDeviceSN, ensure_ascii=False))

        
        #_LOGGER.error('user config, %s', json.dumps(self._user_config))
        await self._storage.update_user_config_async(
            uid=self._config_entry.entry_id, cloud_server=self._cloud_server,
            config={'HaDeviceSN': self._HaDeviceSN})
            #config={'device._device_entity_id_list': self._rspdata,'HaDeviceSN': self._HaDeviceSN})
        #_LOGGER.error('3333 self._rspdata: %s',json.dumps(self._rspdata, ensure_ascii=False)) 
        
        self.__request_refresh_scene_device_info(40)
        '''
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