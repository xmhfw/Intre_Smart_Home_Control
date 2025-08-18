import asyncio
import base64
import logging
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntries
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import (Entity,DeviceInfo)
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from  .switch import async_setup_entry as switch_async_setup_entry
from  .singleColorTemperatureLight import async_setup_entry as singleColorTemperatureLight_async_setup_entry
from  .dualColorTemperatureLight import async_setup_entry as dualColorTemperatureLight_async_setup_entry
from  .RGBWLight import async_setup_entry as RGBWLight_async_setup_entry
from  .RGBCWLight import async_setup_entry as RGBCWLight_async_setup_entry
from  .event import async_setup_entry as event_async_setup_entry
from  .curtain import async_setup_entry as curtain_async_setup_entry
ALL_MODULE_MAP_DICT={
    "switch":switch_async_setup_entry,
    "singleColorTemperatureLight":singleColorTemperatureLight_async_setup_entry,
    "dualColorTemperatureLight":dualColorTemperatureLight_async_setup_entry,
    "RGBWLight":RGBWLight_async_setup_entry,
    "RGBCWLight":RGBCWLight_async_setup_entry,
    "event":event_async_setup_entry,
    "curtain":curtain_async_setup_entry,
}



_LOGGER = logging.getLogger(__name__)

@staticmethod
async def notify_async_forward_entry_setups(hass: HomeAssistant,
        config_entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback,
        moudle_list:list)->bool:
    for mudlue in moudle_list:
        if mudlue in ALL_MODULE_MAP_DICT:
            func=ALL_MODULE_MAP_DICT[mudlue]
            await func(hass=hass,config_entry=config_entry,async_add_entities=async_add_entities)



async def async_setup_entry(
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback,
) -> None:
    '''
    await notify_async_forward_entry_setups(hass=hass,
    config_entry=config_entry,
    async_add_entities=async_add_entities,
    moudle_list=['switch','curtain','singleColorTemperatureLight','dualColorTemperatureLight','RGBWLight','RGBCWLight','event']
    )
    '''


        

