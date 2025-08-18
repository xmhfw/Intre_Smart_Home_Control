import asyncio
import websockets
import json
import socket
import requests
import logging
from typing import Any, Callable, Optional, final
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry, entity_registry
from homeassistant.core import Event
from homeassistant.helpers.event import async_track_state_change_event
from .intreIot_module import (IntreIoTProduct)
from .const  import (DOMAIN, SUPPORTED_PLATFORMS)
_LOGGER = logging.getLogger(__name__)
class IntreIotHa():

    _main_loop: asyncio.AbstractEventLoop
    _hass:HomeAssistant
    _auto_sync:bool
    _hadevices:list
    _entity_ids:list
    _refresh_devices_timer: Optional[asyncio.TimerHandle]
    _devicecall:Callable[dict, None]
    def __init__(self,hass:HomeAssistant,auto_sync:bool,loop: Optional[asyncio.AbstractEventLoop] = None) -> None:
        self._hass=hass
        self._auto_sync = auto_sync
        self._main_loop = loop
        self._refresh_devices_timer = None
        self._subHanlder =None
        self._devicecall=None
        self._hadevices=[]
        
        if auto_sync:
            self.__request_refresh_devices_info(3600)

    def get_entity_state(self,entity_id:str)->dict:
        return self._hass.states.get(entity_id)

    def get_ha_devices(self)->list:
        ha_devices=[]
        dr = device_registry.async_get(self._hass)
        er = entity_registry.async_get(self._hass)
        # 遍历所有设备
        for device in dr.devices.values():
            entitys=[]
            for entry in er.entities.values():
                if entry.device_id == device.id:
                    if entry.entity_id.split(".")[0] in SUPPORTED_PLATFORMS:
                        entity={}
                        entity['entry']=entry
                        entity['state']=self.get_entity_state('entry.id')
                        entitys.append(entity)
            if entitys:
                if device.manufacturer!='INTRETECH':
                    ha_device={}
                    ha_device['deviceId'] = device.id               
                    ha_device['productManufacturer'] = device.manufacturer
                    ha_device['deviceName'] = device.name
                    ha_device['entitys']=entitys
                    ha_devices.append(ha_device)

        return ha_devices
    #返回HA 平台的所有设备列表
    def get_device_list(self)->list:
        self._hadevices=[]
        self._entity_ids=[]
    
        dr = device_registry.async_get(self._hass)
        er = entity_registry.async_get(self._hass)
        # 遍历所有设备
        for device in dr.devices.values():
            entitys=[]
            ha_device={}
            for entry in er.entities.values():
                if entry.device_id == device.id:
                    if entry.entity_id.split(".")[0] in SUPPORTED_PLATFORMS:
                        entity={}
                        entity['entry']=entry
                        entity['state']=self.get_entity_state('entry.id')
                        #_LOGGER.debug(entry.device_id+" "+entry.entity_id)
                        #_LOGGER.debug(self.get_entity_state('light.dim002_2'))
                        self._entity_ids.append(entry.entity_id)
                        entitys.append(entity)
            if entitys:
                product_info={}
                product_info['deviceId'] = device.id               
                product_info['productManufacturer'] = device.manufacturer
                product_info['deviceName'] = device.name
                if product_info['productManufacturer']!='INTRETECH':
                    product:IntreIoTProduct = IntreIoTProduct(product_info=product_info)
                    ha_device['product']=product
                    ha_device['entitys']=entitys
                    self._hadevices.append(ha_device)
        return self._hadevices


    def ha_call_service(self,domain:str,service:str,data:str)->None:
        self._main_loop.create_task(self._hass.services.async_call(
                    domain,
                    service,
                    data,
                    blocking=True
                ))
       
        #self._main_loop.call_soon_threadsafe(self.ha_call_service_soon(),domain,service,data)
        return
        

    def sub_device_state(self,handler: Callable[Event, None])->None:
        if self._subHanlder:
            self._subHanlder()
        self._subHanlder = async_track_state_change_event(self._hass,self._entity_ids,handler)
    
    def sub_entitys_state(self,entitys:[str],handler: Callable[Event, None])->None:
        if self._subHanlder:
            self._subHanlder()
        self._subHanlder = async_track_state_change_event(self._hass,entitys,handler)
    
    def sub_device_change(self,handler: Callable[dict, None])->None:
        self._devicecall = handler

    async def deinit_async(self) -> None:
        if self._refresh_devices_timer:
            self._refresh_devices_timer.cancel()
            self._refresh_devices_timer = None
        if self._subHanlder:
            self._subHanlder()
    
    @final
    async def refresh_devices_async(self) -> bool:
        _LOGGER.debug('refresh_devices_async_ha')
        self.get_device_list()
        self.__request_refresh_devices_info(3600)
        return True

    @final
    def __request_refresh_devices_info(self,delay_sec: int) -> None:
        if self._refresh_devices_timer:
            self._refresh_devices_timer.cancel()
            self._refresh_devices_timer = None
        
        self._refresh_devices_timer = self._main_loop.call_later(
            delay_sec, lambda: self._main_loop.create_task(
                self.refresh_devices_async()))

