# -*- coding: utf-8 -*-
"""
Copyright (C) 2024 Intretech Corporation.

The ownership and intellectual property rights of Intretech Home Assistant
Integration and related Intretech cloud service API interface provided under this
license, including source code and object code (collectively, "Licensed Work"),
are owned by Intretech. Subject to the terms and conditions of this License, Intretech
hereby grants you a personal, limited, non-exclusive, non-transferable,
non-sublicensable, and royalty-free license to reproduce, use, modify, and
distribute the Licensed Work only for your use of Home Assistant for
non-commercial purposes. For the avoidance of doubt, Intretech does not authorize
you to use the Licensed Work for any other purpose, including but not limited
to use Licensed Work to develop applications (APP), Web services, and other
forms of software.

You may reproduce and distribute copies of the Licensed Work, with or without
modifications, whether in source or object form, provided that you must give
any other recipients of the Licensed Work a copy of this License and retain all
copyright and disclaimers.

Intretech provides the Licensed Work on an "AS IS" BASIS, WITHOUT WARRANTIES OR
CONDITIONS OF ANY KIND, either express or implied, including, without
limitation, any warranties, undertakes, or conditions of TITLE, NO ERROR OR
OMISSION, CONTINUITY, RELIABILITY, NON-INFRINGEMENT, MERCHANTABILITY, or
FITNESS FOR A PARTICULAR PURPOSE. In any event, you are solely responsible
for any direct, indirect, special, incidental, or consequential damages or
losses arising from the use or inability to use the Licensed Work.

Intretech reserves all rights not expressly granted to you in this License.
Except for the rights expressly granted by Intretech under this License, Intretech
does not authorize you in any form to use the trademarks, copyrights, or other
forms of intellectual property rights of Intretech and its affiliates, including,
without limitation, without obtaining other written permission from Intretech, you
shall not use "Intretech", "Mijia" and other words related to Intretech or words that
may make the public associate with Intretech in any form to publicize or promote
the software or hardware devices that use the Licensed Work.

Intretech has the right to immediately terminate all your authorization under this
License in the event:
1. You assert patent invalidation, litigation, or other claims against patents
or other intellectual property rights of Intretech or its affiliates; or,
2. You make, have made, manufacture, sell, or offer to sell products that knock
off Intretech or its affiliates' products.

IntreIoT client instance.
"""
from copy import deepcopy
from typing import Any, Callable, Optional, final
import asyncio
import json
import logging
import time
import traceback
from dataclasses import dataclass
from enum import Enum, auto

from homeassistant.core import HomeAssistant
from homeassistant.components import zeroconf
from .intreIot_network import IntreIoTNetwork
from .intreIot_storage import IntreIoTStorage
# pylint: disable=relative-beyond-top-level
from homeassistant.config_entries import ConfigEntry
from homeassistant.components import persistent_notification
from homeassistant.core import HomeAssistant

from .const import (
    DEFAULT_CTRL_MODE, DEFAULT_INTEGRATION_LANGUAGE, DEFAULT_NICK_NAME, DOMAIN,
    NETWORK_REFRESH_INTERVAL,OAUTH2_CLIENT_ID, SUPPORT_CENTRAL_GATEWAY_CTRL)
from .intreIot_cloud import IntreIotHttpClient
from .intreIot_error import IntreIoTHttpError, IntreIoTErrorCode
from .intreIot_intreps import (IntrepsCloudClient)
from .common import IntreIoTMatcher
from .const  import (DOMAIN, SUPPORTED_PLATFORMS,MODULE_PRIORITY_DB,PRODUCT_KEY_DB,NETWORK_REFRESH_INTERVAL,MQTT_ToH,INTRE_HA_PRODUCT_KEY)
_LOGGER = logging.getLogger(__name__)


@dataclass
class IntreIoTClientSub:
    """IntreIoT client subscription."""
    topic: Optional[str]
    handler: Callable[[dict, Any], None]
    handler_ctx: Any = None

    def __str__(self) -> str:
        return f'{self.topic}, {id(self.handler)}, {id(self.handler_ctx)}'

class IntreIoTClient:
    """IntreIoT client instance."""
    _main_loop: asyncio.AbstractEventLoop
    _uid: str
    _entry_id: str
    _entry_data: dict
    _mqtt_user_name:str
    _mqtt_user_password:str
    _http_client:IntreIotHttpClient
    _network: IntreIoTNetwork
    _home_select:list
    _mqttStatusflag:bool
    # Cloud intreps client
    _mqtt_cloud:IntrepsCloudClient
    _refresh_token_timer: Optional[asyncio.TimerHandle]
    _sub_tree: IntreIoTMatcher

    _sub_prop_tree:dict[str,list[Callable[str, None]]]

    _home_sub_tree:dict[str,Callable[dict, None]]
    
    def __init__(
            self,
            entry_id: str,
            entry_data: dict,
            network: IntreIoTNetwork,
            hass: HomeAssistant, 
            config_entry: ConfigEntry,
            loop: Optional[asyncio.AbstractEventLoop] = None) -> None:
        # MUST run in a running event loop
        self._main_loop = loop or asyncio.get_running_loop()
        self._mqttStatusflag = False
        self._entry_id = entry_id
        self._entry_data = entry_data
        self.hass = hass
        self.config_entry = config_entry
        self._cloud_server='cn'
        self._mqtt_cloud = None
        self._home_sub_tree={}
        self._sub_tree = IntreIoTMatcher()
        self._sub_prop_tree={}
        self._device_id = None
        self._refresh_token_timer = None
        # Check params
        if not isinstance(entry_data, dict):
            raise IntreIoTClientError('invalid entry data')
        if not isinstance(network, IntreIoTNetwork):
            raise IntreIoTClientError('invalid  network')

        self._network = network

    async def init_async(self) -> None:
        self._http_client = IntreIotHttpClient()
        
        # 1. 获取token和device_id，并验证有效性
        # 重试配置（无限制次数，仅设置间隔）
        retry_interval = 5  # 重试间隔(秒)，可根据需求调整
        retry_count = 0     # 仅用于日志记录重试次数
        
        # 无限循环重试，直到成功获取deviceId
        while True:
            retry_count += 1
            try:
                rsp = await self._http_client.getToken(devicesn=self._entry_data['devicesn'])
                self._device_id = rsp.get('deviceId')
                
                if self._device_id:
                    _LOGGER.debug(f"第{retry_count}次尝试成功,获取到deviceId: {self._device_id}")
                    break  # 获取成功，退出循环
                else:
                    _LOGGER.warning(f"第{retry_count}次尝试失败:获取到token,但未包含deviceId,{retry_interval}秒后重试...")
                    await asyncio.sleep(retry_interval)
                    
            except Exception as e:
                _LOGGER.error(f"第{retry_count}次尝试失败:获取token时发生错误 - {str(e)}", exc_info=True)
                _LOGGER.info(f"{retry_interval}秒后进行下一次重试...")
                await asyncio.sleep(retry_interval)

        # 2. 获取MQTT连接信息
        try:
            logintInfo = await self._http_client.get_mqtt_info(deviceSn=self._entry_data['devicesn'])
            if not logintInfo:
                _LOGGER.error("获取MQTT连接信息失败")
                return
        except Exception as e:
            _LOGGER.error(f"获取MQTT信息失败: {str(e)}", exc_info=True)
            return

        # 3. 创建MQTT客户端实例
        self._mqtt_cloud = IntrepsCloudClient(
            uuid=logintInfo['data']['mqttClientId'],
            host=logintInfo['data']['mqttServerHost'],
            username=logintInfo['data']['mqttUsername'],
            password=logintInfo['data']['mqttPassword'],
            loop=self._main_loop)

        # 4. 订阅业务主题（与遗嘱无关，正常设置）
        down_online_report_reply_topic = f'{MQTT_ToH}device/{INTRE_HA_PRODUCT_KEY}/{self._device_id}/down/online/report-reply'
        self.down_online_report_reply(
            topic=down_online_report_reply_topic,
            handler=self.down_online_report_reply_topic_callback
        )
        _LOGGER.debug(f"已订阅业务主题: {down_online_report_reply_topic}")

        # 5. 关键：在连接前设置遗嘱消息（确保参数有效）
        try:
            # 验证遗嘱所需参数
            if not all([self._http_client.token, INTRE_HA_PRODUCT_KEY, self._device_id]):
                _LOGGER.error("遗嘱消息参数不完整(token/productkey/deviceid)")
                return

            self._mqtt_cloud.set_will_news(
                token=self._http_client.token,
                productkey=INTRE_HA_PRODUCT_KEY,
                deviceid=self._device_id
            )
            _LOGGER.debug("遗嘱消息已设置,准备连接MQTT服务器")
        except Exception as e:
            _LOGGER.error(f"设置遗嘱消息失败: {str(e)}", exc_info=True)
            return

        # 6. 订阅客户端状态变化
        self._uid = logintInfo['data']['mqttClientId']
        self._mqtt_cloud.sub_intreps_state(
            key=f'{self._uid}-{self._cloud_server}',
            handler=self.__on_intreps_cloud_state_changed
        )

        # 7. 最后一步：建立MQTT连接（确保遗嘱已设置）
        try:
            _LOGGER.debug("MQTT连接ing...")
            await self._mqtt_cloud.intreps_connect_async()
            _LOGGER.debug("MQTT连接成功,遗嘱消息已被服务器记录")
        except Exception as e:
            _LOGGER.error(f"MQTT连接失败: {str(e)}", exc_info=True)
            return

        # 后续其他初始化操作（网络订阅、刷新token等）
        self._network.sub_network_status(
            key=f'{self._entry_id}-{self._cloud_server}',
            handler=self.__on_network_status_changed)

        await self.__on_network_status_changed(
            status=self._network.network_status)

        self.__request_refresh_token_info(3600)


    def down_online_report_reply_topic_callback(self,data:dict)->bool:
        _LOGGER.debug(data)
        _LOGGER.debug('down_online_report_reply_topic_callback')
        
    async def get_homes_devices(self)->dict:
        return None

    def reload_home(self, homeid:str) -> None:
        _LOGGER.debug("reload_home %s",homeid)

    async def connect_Intre_Cloud(self)->None:
        _LOGGER.debug('connect_Intre_Cloud1111')
        if self._http_client:
            await self._http_client.deinit_async()
  
        _LOGGER.debug('connect_Intre_Cloud222')
        self._http_client = IntreIotHttpClient()
        # 先清理可能存在的旧MQTT连接（添加检查）
        if self._mqtt_cloud is not None:
            try:
                self._mqtt_cloud.intreps_deinit()  
                _LOGGER.debug('connect_Intre_Cloud555555')
            except Exception as e:
                _LOGGER.error(f"关闭旧MQTT连接时出错: {str(e)}")
            self._mqtt_cloud = None  # 显式设为None，避免后续混淆
            _LOGGER.debug('connect_Intre_Cloud66666')
        # 重试配置（无限制次数，仅设置间隔）
        retry_interval = 5  # 重试间隔(秒)，可根据需求调整
        retry_count = 0     # 仅用于日志记录重试次数
        
        # 无限循环重试，直到成功获取deviceId
        while True:
            retry_count += 1
            try:
                rsp = await self._http_client.getToken(devicesn=self._entry_data['devicesn'])
                self._device_id = rsp.get('deviceId')
                
                if self._device_id:
                    _LOGGER.debug(f"第{retry_count}次尝试成功,获取到deviceId: {self._device_id}")
                    break  # 获取成功，退出循环
                else:
                    _LOGGER.warning(f"第{retry_count}次尝试失败:获取到token,但未包含deviceId,{retry_interval}秒后重试...")
                    await asyncio.sleep(retry_interval)
                    
            except Exception as e:
                _LOGGER.error(f"第{retry_count}次尝试失败:获取token时发生错误 - {str(e)}", exc_info=True)
                _LOGGER.info(f"{retry_interval}秒后进行下一次重试...")
                await asyncio.sleep(retry_interval)

        logintInfo=await self._http_client.get_mqtt_info(deviceSn=self._entry_data['devicesn'])
        _LOGGER.debug(f"connect_Intre_Cloud4444: {logintInfo}")  
        if logintInfo['code']==1:
            # IntreIoT cloud intreps client
            self._mqtt_cloud = IntrepsCloudClient(
                uuid=logintInfo['data']['mqttClientId'],
                host=logintInfo['data']['mqttServerHost'],
                username=logintInfo['data']['mqttUsername'],
                password=logintInfo['data']['mqttPassword'],
                loop=self._main_loop)
            
            # 4. 订阅业务主题（与遗嘱无关，正常设置）
            down_online_report_reply_topic = f'{MQTT_ToH}device/{INTRE_HA_PRODUCT_KEY}/{self._device_id}/down/online/report-reply'
            self.down_online_report_reply(
                topic=down_online_report_reply_topic,
                handler=self.down_online_report_reply_topic_callback
            )
            _LOGGER.debug(f"已订阅业务主题: {down_online_report_reply_topic}")
            self._mqtt_cloud.set_will_news(token=self._http_client.token,productkey=INTRE_HA_PRODUCT_KEY,deviceid=self._device_id)
            # 6. 订阅客户端状态变化
            self._uid = logintInfo['data']['mqttClientId']
            self._mqtt_cloud.sub_intreps_state(
                key=f'{self._uid}-{self._cloud_server}',
                handler=self.__on_intreps_cloud_state_changed
            )

            # 7. 最后一步：建立MQTT连接（确保遗嘱已设置）
            try:
                await self._mqtt_cloud.intreps_connect_async()
                _LOGGER.debug("MQTT连接成功,遗嘱消息已被服务器记录")
            except Exception as e:
                _LOGGER.error(f"MQTT连接失败: {str(e)}", exc_info=True)
                return

            # 后续其他初始化操作（网络订阅、刷新token等）
            self._network.sub_network_status(
                key=f'{self._entry_id}-{self._cloud_server}',
                handler=self.__on_network_status_changed)

            await self.__on_network_status_changed(
                status=self._network.network_status)
  
            self.__request_refresh_token_info(3600)
    
        

    async def deinit_async(self) -> None:
        await self._http_client.deinit_async()

        # Cloud mips
        self._mips_cloud.unsub_mips_state(
            key=f'{self._uid}-{self._cloud_server}')
        self._mips_cloud.disconnect()

        # Cancel refresh auth info
        if self._refresh_token_timer:
            self._refresh_token_timer.cancel()
            self._refresh_token_timer = None

    @property
    def intreiot_network(self) -> IntreIoTNetwork:
        return self._network

    @final
    async def refresh_token_async(self) -> bool:
        _LOGGER.debug('__request_refresh_token_info')
        await self._http_client.updateToken()
        self.__request_refresh_token_info(3600)
        return True

    @final
    def __request_refresh_token_info(self,delay_sec: int) -> None:
        if self._refresh_token_timer:
            self._refresh_token_timer.cancel()
            self._refresh_token_timer = None
        
        self._refresh_token_timer = self._main_loop.call_later(
            delay_sec, lambda: self._main_loop.create_task(
                self.refresh_token_async()))


    @final
    async def __on_intreps_cloud_state_changed(
        self, key: str, state: bool
    ) -> None:
        _LOGGER.debug('cloud intreps state changed, %s, %s,%s', key, state,self._mqttStatusflag)
        if not state:
            if self._mqttStatusflag:
                self._mqttStatusflag=False
                _LOGGER.debug('cloud intreps state changed111111111, %s, %s,%s', key, state,self._mqttStatusflag)
                await self.connect_Intre_Cloud()
        else:
            await self.report_online_async(INTRE_HA_PRODUCT_KEY,self._device_id)
            self._mqttStatusflag=True
            from .engine_manager import EngineManager
            from .intre_manage_engine import IntreManagementEngine  # 导入引擎类
            # 核心：通过全局管理器获取引擎实例并调用方法
            try:
                # 从全局管理器获取IntreManagementEngine实例
                engine = EngineManager.get_instance("intre_manage_engine")

                if not engine:
                    _LOGGER.error("Failed to get IntreManagementEngine instance (not registered)")
                    return

                # 验证实例类型，确保调用安全
                if not isinstance(engine, IntreManagementEngine):
                    _LOGGER.error("Retrieved instance is not IntreManagementEngine")
                    return

                # 调用引擎的同步方法（示例：调用subscribe_device）
                sync_result = await engine.subscribe_device()
                _LOGGER.debug(f"Sync completed, result: {sync_result}")

                # 如需调用其他方法，直接通过engine实例调用
                # 例如：await engine.other_method(param1, param2)

            except Exception as e:
                _LOGGER.error(
                    f"Error while calling IntreManagementEngine method: {str(e)}",
                    exc_info=True  # 记录完整堆栈，便于调试
                )
            _LOGGER.debug('cloud intreps state changed1111')
        

    @final
    async def __on_network_status_changed(self, status: bool) -> None:
        _LOGGER.debug('network status changed, %s', status)
        
    def sub_prop_set(self,topic:str,handler: Callable[[dict, Any],None])->None:
        self._mqtt_cloud.sub_mqtt_prop_set(topic=topic, handler=handler)
    
    def sub_service_call(self,topic:str,handler: Callable[[dict, Any],None])->None: 
        self._mqtt_cloud.sub_mqtt_service_call(topic=topic, handler=handler)
    
    def sub_bacth_service_prop(self,topic:str,handler: Callable[[dict, Any],None])->None:
        self._mqtt_cloud.sub_mqtt_bacth_service_prop(topic=topic, handler=handler)
    
    def down_online_report_reply(self,topic:str,handler: Callable[[dict, Any],None])->None:
        self._mqtt_cloud.sub_mqtt_down_online_report_reply(topic=topic, handler=handler)  

    def down_data_define_report_reply(self,topic:str,handler: Callable[[dict, Any],None])->None:  
        self._mqtt_cloud.sub_mqtt_down_data_define_report_reply(topic=topic, handler=handler)

    def down_tls_event_report_reply(self,topic:str,handler: Callable[[dict, Any],None])->None:  
        self._mqtt_cloud.sub_mqtt_down_tls_event_report_reply(topic=topic, handler=handler)

    def down_tls_property_report_reply(self,topic:str,handler: Callable[[dict, Any],None])->None:  
        self._mqtt_cloud.sub_mqtt_down_tls_property_report_reply(topic=topic, handler=handler)

    async def report_online_async(self,productkey:str,deviceid:str)->None:
        await self._mqtt_cloud.report_online_async(token=self._http_client.token,productkey=productkey,deviceid=deviceid)
    
    async def report_batch_module_prop_async(self,productkey:str,deviceid:str,batch_modules:list)->None:
        await self._mqtt_cloud.report_batch_module_prop_async(token=self._http_client.token,productkey=productkey,deviceid=deviceid,batch_modules=batch_modules)

    async def data_define_report_async(self,productkey:str,deviceid:str,data_define:list)->None:
        await self._mqtt_cloud.data_define_report_async(token=self._http_client.token,productkey=productkey,deviceid=deviceid,data_define=data_define)

    async def report_prop_async(self,productkey:str,deviceid:str,modulekey:str,propkey:str,prop_value:str)->None:
        await self._mqtt_cloud.report_prop_async(token=self._http_client.token,productkey=productkey,deviceid=deviceid,modulekey=modulekey,propkey=propkey,prop_value=prop_value)

    async def report_device_tsl_log_async(self,productkey:str,deviceid:str,tls_logs:list)->None: 
        await self._mqtt_cloud.report_device_tsl_log_async(token=self._http_client.token,productkey=productkey,deviceid=deviceid,tls_logs=tls_logs)  

    async def report_device_down_tsl_log_async(self,productkey:str,deviceid:str)->None: 
        await self._mqtt_cloud.report_device_down_tsl_log_async(token=self._http_client.token,productkey=productkey,deviceid=deviceid,)    
    
    async def report_event_async(self,productkey:str,deviceid:str,modulekey:str,eventkey:str,event_value:str)->None:
        await self._mqtt_cloud.report_event_async(token=self._http_client.token,productkey=productkey,deviceid=deviceid,modulekey=modulekey,eventkey=eventkey,event_value=event_value)
    
    async def prop_set_reply_async(self,productkey:str,deviceid:str,msgid:str,code:str)->None:
        await self._mqtt_cloud.prop_set_reply_async(token=self._http_client.token,productkey=productkey,deviceid=deviceid,msgid=msgid,code=code)
    
    async def prop_service_set_reply_async(self,productkey:str,deviceid:str,msgid:str,code:str)->None:
        await self._mqtt_cloud.prop_service_set_reply_async(productkey=productkey,deviceid=deviceid,msgid=msgid,code=code)

    async def service_set_reply_async(self,productkey:str,deviceid:str,moduleKey:str,serviceKey: str,msgid:str,code:str)->None:
        await self._mqtt_cloud.service_set_reply_async(token=self._http_client.token,productkey=productkey,deviceid=deviceid,moduleKey=moduleKey,serviceKey=serviceKey,msgid=msgid,code=code)
    