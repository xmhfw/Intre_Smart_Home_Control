import asyncio
import base64
import json
import logging
import re
import time
import hmac
import hashlib
import paho.mqtt.client as mqtt
from typing import Any, Callable, Optional, final
from urllib.parse import urlencode
import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntries
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import (Entity,DeviceInfo)
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from .intreiot.intreIot_module import (IntreIoTProduct,IntreIoTModule)
from .intreiot.intre_manage_engine import (IntreManagementEngine)
from .intreiot.const   import (DOMAIN, SUPPORTED_PLATFORMS)
from .intreiot.intreIot_client import IntreIoTClient
from .util import StateUtils
_LOGGER = logging.getLogger(__name__)
async def async_setup_entry(
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback,
) -> None:
    intre_ss:IntreManagementEngine =hass.data[DOMAIN]['intre_ss'][config_entry.entry_id]
    _hadevices = hass.data[DOMAIN]['config_data']['_hadevices']
    
    for hadevice in _hadevices:
        product = hadevice['product']
        entitys = hadevice['entitys']
        for entity in entitys:
            #_LOGGER.debug('switch create'+entity['entry'].entity_id)
            if entity['entry'].entity_id.split(".")[0]== 'switch':
                module_info={}
                _LOGGER.debug('switch create')
                module_info['moduleCode']='switch'
                module_info['moduleKey']=entity['entry'].entity_id
                module_info['moduleName']= entity['entry'].name
                module_info['entity_id']= entity['entry'].entity_id
                switch :IntreSwitch = IntreSwitch(intre_ss=intre_ss,product=product,module_info=module_info)
                _LOGGER.debug(product.deviceSn)
                _LOGGER.debug(product._name) 
                product.add_modules(switch)

class IntreSwitch(IntreIoTModule):
    _product:IntreIoTProduct
    _intre_ss:IntreManagementEngine
    _onOff:bool

    def __init__(self,intre_ss:IntreManagementEngine,product:IntreIoTProduct,module_info:dict) -> None:
        super().__init__(module_info=module_info)
        _LOGGER.debug('Initializing IntreSwitch...')
        self._intre_ss=intre_ss
        self._product=product

        self._onOff =StateUtils.util_get_state_onoff(intre_ss._intre_ha.get_entity_state(self._entity_id))
        self._intre_ss.sub_entity(self._entity_id,self._entity_state_notify)
        self._product.sub_prop_set(self._module_key,self.attr_change_req)
        self._product.sub_service_call(self._module_key,self.service_call_req)
        self._product.sub_bacth_service_prop_call(self._module_key,self.batch_service_prop_call_req)
        _LOGGER.debug(self._onOff) 
    
    @final
    def get_module_prop_json(self)->dict:
        timestamp_ms = str(int(time.time() * 1000))
        return {
            "moduleKey":self._module_key,
            "propertyList": [
                {
                "propertyKey": "onOff",
                "propertyValue":str(int(self._onOff)),  
                "timestamp": timestamp_ms
                }
            ]
        }
        

    @final
    def get_module_json(self)->dict:
        timestamp_ms = str(int(time.time() * 1000))
        # 规则：提取末尾数字作为序号，格式为"灯X"
        match = re.search(r'_(\d+)$', self._module_key)
        if match:
            index = match.group(1)
            instance_module_name = f"灯{index}"
        else:
            # 匹配失败时使用默认名称
            instance_module_name = "未知设备"

        result= {
            "templateModuleKey":'switch_1',
            "instanceModuleKey": self._module_key,
            "instanceModuleName": instance_module_name,  # 动态生成的名称
            "propertyList": [
                {
                "propertyKey": "onOff",
                "propertyValue":str(int(self._onOff)),  
                "timestamp": timestamp_ms
                }
            ]
        }
        _LOGGER.debug(
            f"productKey: {self._product.productKey}, deviceId: {self._product.deviceId} "
            f"_module_key: {self._module_key}, _module_name: {self._module_name}"          
        )

        _LOGGER.debug(result)
        return result

    async def _entity_state_notify(self,newstate)->None:
        _LOGGER.debug(f"开关新状态: {newstate.state,newstate.entity_id}")  
        self._onOff=StateUtils.util_get_state_onoff(newstate)
        await self._intre_ss.report_prop_async(self._product.productKey,self._product.deviceId,self._module_key,'onOff',str(int(self._onOff)))
        
        _LOGGER.debug("SWITCH state" + str(self._onOff))
        return

    def service_call_req(self, service_call_data: dict) -> None:
        _LOGGER.debug(f"service_call_data: {service_call_data}")
        
        data = {
            'entity_id': self._entity_id
        }
        
        # 获取服务字典（不是列表）
        service = service_call_data.get('module', {}).get('service', {})
        
        # 检查服务键
        if service.get('serviceKey') == 'toggleOnOff':
            # 根据当前状态决定是开启还是关闭
            target_service = 'turn_off' if self._onOff else 'turn_on'
            
            _LOGGER.debug(f"call_service={target_service} {data}")  
            # 调用家庭自动化服务（修正可能的拼写错误）
            self._intre_ss.call_ha_service('switch', target_service, data) 
        

    def batch_service_prop_call_req(self,batch_service_prop_data:dict)->None:
        data={
            'entity_id':self._entity_id
        }
        for prop in batch_service_prop_data['propertyList']:
            if prop['propertyKey']=='onOff':
                service='turn_on'
                if prop['propertyValue']=='0':
                    service='turn_off'
                _LOGGER.debug("batch1_service=%s %s",service,data)  
                self._intre_ss.call_ha_service('switch',service,data)
        
        for service in batch_service_prop_data['serviceList']:
            if service['serviceKey']=='toggleOnOff':
                service='turn_on'
                if self._onOff==True:
                    service='turn_off'
                _LOGGER.debug("batch2_service=%s %s",service,data)  
                self._intre_ss.call_ha_service('switch',service,data)        
        
    def attr_change_req(self, properlist: list,msg_id: str) -> None:
        _LOGGER.debug(f"properlist: {properlist}")
        data={
            'entity_id':self._entity_id
        }
        service='turn_on'
        for prop in properlist:
            if prop['propertyKey']=='onOff':
                if prop['propertyValue']=='0':
                    service='turn_off'
                _LOGGER.debug("change_service=%s %s",service,data)  
                self._intre_ss.call_ha_service('switch',service,data)
        return

    


async def test_fun()->bool:
    _LOGGER.debug("test-switch")  