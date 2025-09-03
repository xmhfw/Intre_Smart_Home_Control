import asyncio
import websockets
import json
import socket
import requests
from typing import Any, Callable, Optional, final
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry, entity_registry
from homeassistant.core import Event

class IntreIotHa():

    _main_loop: asyncio.AbstractEventLoop
    _hass:HomeAssistant
    _auto_sync:bool
    _products:list
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
        if auto_sync:
            self.__request_refresh_devices_info(3600)

    def get_entity_state(self,entity_id:str)->dict:
        return self._hass.states.get(entity_id)
        
    def get_device_list(self)->list:
        self._products=[]
        self._entity_ids=[]

        dr = device_registry.async_get(self._hass)
        er = entity_registry.async_get(self._hass)
        # 遍历所有设备
        for device in dr.devices.values():
            entitys=[]
            product={}
            for entry in er.entities.values():
                if entry.device_id == device.id:
                    if entry.platform in SUPPORTED_PLATFORMS:
                        self._entity_ids.append(entry.id)
                        entitys.append(entry)
            if entitys:
                product['device_info']=device
                product['entitys']=entitys
                self._products.append(product)
        return self._products

    async def state_changed_callback(event):
        old_state = event.data.get("old_state")
        new_state = event.data.get("new_state")
        if not (old_state and new_state):
            return

        _LOGGER.error(f"实体 {event.data['entity_id']} 的状态发生变化:")
        _LOGGER.error(f"  旧状态: {old_state.state}")
        _LOGGER.error(f"  新状态: {new_state.state}")

    def sub_device_state(self,handler: Callable[Event, None])->None:
        self._subHanlder = async_track_state_change_event(self._hass,self._entity_ids,handler)
    
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
        _LOGGER.error('refresh_devices_async')
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

