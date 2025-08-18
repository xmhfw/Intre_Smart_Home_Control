"""Platform for light integration.
from __future__ import annotations
# Import the device class from the component that you want to support
import homeassistant.helpers.config_validation as cv
from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_RGB_COLOR,
    ATTR_EFFECT,
    LightEntity,
    LightEntityFeature,
    ColorMode
)
from homeassistant.util.color import (
    value_to_brightness,
    brightness_to_value
)
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
"""
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
            entity_entry = entity.get('entry')
            entity_id = entity_entry.entity_id
            #_LOGGER.debug('light create11111'+entity['entry'].entity_id)
            if entity_id.split(".")[0]== 'light':
                
                #_LOGGER.debug(f"entity_id: {entity_id}")
                state = hass.states.get(entity_id)
                #_LOGGER.debug("Brightness light.")
                #_LOGGER.debug(state)
                if state is not None:
                    attributes = state.attributes
                    supported_color_modes = attributes.get('supported_color_modes', 'N/A')
                    if 'color_brightness' in supported_color_modes:# 判断是否双色温灯
                
                        module_info={}
                        _LOGGER.debug('singleColorTemperatureLight create')
                        module_info['moduleCode']='singleColorTemperatureLight'
                        module_info['moduleKey']=entity['entry'].entity_id
                        module_info['moduleName']= entity['entry'].name
                        module_info['entity_id']= entity['entry'].entity_id
                        light :IntreBrightnessLight = IntreBrightnessLight(hass=hass,intre_ss=intre_ss,product=product,module_info=module_info)
                        product.add_modules(light)


class IntreBrightnessLight(IntreIoTModule):
    _product:IntreIoTProduct
    _intre_ss:IntreManagementEngine
    _hass:HomeAssistant
    def __init__(self,hass,intre_ss:IntreManagementEngine,product:IntreIoTProduct,module_info:dict) -> None:
        super().__init__(module_info=module_info)
        _LOGGER.debug('Initializing singleColorTemperatureLight...')
        self._hass=hass
        self._intre_ss=intre_ss
        self._product=product
        self.state = None
        self.attributes = dict
        self.module_info={}
        self._intre_ss.sub_entity(self._entity_id,self._entity_state_notify)
        self._product.sub_prop_set(self._module_key,self.attr_change_req)
        self._product.sub_service_call(self._module_key,self.service_call_req)

        #state = self._hass.states.get(self._entity_id)
    @final
    def get_module_prop_json(self)->dict:
        timestamp_ms = str(int(time.time() * 1000))
        return {
            "moduleKey":self._module_key,
            "propertyList": [
                {
                "propertyKey": "onOff",
                "propertyValue": str(int(self._onOff)),  
                "timestamp": timestamp_ms
                },
                {
                "propertyKey": "brightness",
                "propertyValue": str(self._brightness),
                "timestamp": timestamp_ms
                } 
            ]
        }
    @final
    def get_module_json(self)->dict:
        timestamp_ms = str(int(time.time() * 1000))
        _LOGGER.debug('Initializing111111111111111111111111111...')
        match = re.search(r'_(\d+)$', self._module_key)
        if match:
            index = match.group(1)
            instance_module_name = f"单色温{index}"
        else:
            # 匹配失败时使用默认名称
            instance_module_name = "未知设备"
        return {
            "templateModuleKey":'singleColorTemperatureLight_1',
            "instanceModuleKey": self._module_key,
            "instanceModuleName": instance_module_name,  # 动态生成的名称
            "propertyList": [
                {
                "propertyKey": "onOff",
                "propertyValue": "1",
                "timestamp": timestamp_ms
                },
                {
                "propertyKey": "brightness",
                "propertyValue": "0",
                "timestamp": timestamp_ms
                }                          
            ]
        }   

    async def _entity_state_notify(self,newstate)->None:
        _LOGGER.debug(newstate)
        attributes = newstate.attributes
        brightness = attributes.get('brightness', 'N/A')

        _LOGGER.debug(
            f"Light Current state: {newstate.state}, Entity ID: {newstate.entity_id}"
            f"Brightness: {brightness}"         
        )

        #_LOGGER.debug(f"Light Current state: {newstate.state,newstate.entity_id,newstate.attributes['brightness'],newstate.attributes['color_temp'],newstate.attributes['max_color_temp_kelvin']}")   
        #OnOff
        if newstate.state =='on':
            await self._intre_ss.report_prop_async(self._product.productKey,self._product.deviceId,self._module_key,'onOff','1')
        else:
            await self._intre_ss.report_prop_async(self._product.productKey,self._product.deviceId,self._module_key,'onOff','0')
        #brightness
        if 'brightness' not in newstate.attributes:
            _LOGGER.debug("Brightness key not found in state attributes.")
        else:
            # 获取 brightness 值并检查类型
            brightness_value = newstate.attributes['brightness']
            if not isinstance(brightness_value, (int, float)):
                _LOGGER.debug("Brightness value is not a number.")
            else:
                brightness_normalized = int(brightness_value / 2.55)
            # 调用报告属性方法
            await self._intre_ss.report_prop_async(
                self._product.productKey,
                self._product.deviceId,
                self._module_key,
                'brightness',
                brightness_normalized
            )
        #await self._intre_ss.report_prop_async(self._product.productKey,self._product.deviceId,self._module_key,'colorTemperature',int((int(10 ** 6 /float(newstate.attributes['color_temp']))) / 50) * 50)
        return                      

    def service_call_req(self,serice_call_data:list)->None:
        data={
            'entity_id':self._entity_id
        }
        _LOGGER.debug(f"serice_call_data: {serice_call_data}") 
        service_input_value = serice_call_data['module']['service']['serviceInputValue']
        input_data = json.loads(service_input_value)
        brightness_data  = input_data.get('brightness')
        colorTemperature_data = input_data.get('colorTemperature')

        if 'brightness' in input_data:
            data['brightness'] = float(brightness_data * 2.55)
            self._intre_ss.call_ha_service('light','turn_on',data)
            _LOGGER.debug("BRIGHTNESS888888888888=   %d", brightness_data)
            _LOGGER.debug(data['brightness'])
        elif 'colorTemperature' in input_data:
            result = 10 ** 6
            data['color_temp'] =float (result /colorTemperature_data)
            _LOGGER.debug(data['color_temp'])
            self._intre_ss.call_ha_service('light','turn_on',data)
            _LOGGER.debug("colorTemperature999999999=  %d",colorTemperature_data)    
        
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
                _LOGGER.debug("onOffservice=%s %s",service,data)  
                self._intre_ss.call_ha_service('light',service,data)
            elif prop.get('propertyKey') == 'brightness':
                data['brightness'] = int(prop.get('propertyValue', 255))
                _LOGGER.debug("brightservice=%d ",data)  
                self._intre_ss.call_ha_service('light','brightness',data)
            elif prop.get('propertyKey') == 'colorTemperature':
                data['color_temp'] = int(prop.get('propertyValue', 255))
                _LOGGER.debug("brightservice=%d ",data)  
                self._intre_ss.call_ha_service('light','color_temp',data)    
        return

async def test_fun()->bool:
    _LOGGER.debug("test-light")  
