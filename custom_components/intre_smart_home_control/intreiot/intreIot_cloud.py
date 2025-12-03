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

IntreIoT http client.
"""
import asyncio
import base64
import socket
import json
import logging
import re
import time
import hmac
import hashlib
import paho.mqtt.client as mqtt
from typing import Any, Optional
from urllib.parse import urlencode
import aiohttp
from .const import (
    INTREIOT_HTTP_SERVER_URL,
    DEFAULT_OAUTH2_API_HOST,
    INTREHOME_HTTP_API_TIMEOUT,
    INTRE_HA_CONTROL_VERSION,
    INTRE_SECURE_KEY,
    OAUTH2_AUTH_URL)
from .intreIot_error import IntreIoTErrorCode, IntreIoTHttpError, IntreIoTOauthError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import aiohttp

# pylint: disable=relative-beyond-top-level

_LOGGER = logging.getLogger(__name__)

class IntreIotHttpClient:
    """Intre IOT http client."""
    # pylint: disable=inconsistent-quotes
    GET_PROP_AGGREGATE_INTERVAL: float = 0.2
    GET_PROP_MAX_REQ_COUNT = 150
    _main_loop: asyncio.AbstractEventLoop
    _session: aiohttp.ClientSession
    _base_url: str
    _access_token: str
    _lanip:str

    _get_prop_timer: Optional[asyncio.TimerHandle]
    _get_prop_list: dict[str, dict]

    def __init__(
            self, 
            loop: Optional[asyncio.AbstractEventLoop] = None
    ) -> None:
        #self._main_loop = loop or asyncio.get_running_loop()
        self._base_url = INTREIOT_HTTP_SERVER_URL
        self._session = aiohttp.ClientSession()
        self._lanip=self.get_local_ip()
        self._Device_id = None
          
    async def deinit_async(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    def __calculate_checksum(self, msg_id: str, timestamp: str, json_string: str) -> str:
        input_string = self._access_token + msg_id + timestamp + json_string
        hmac_sha1 = hmac.new(
            #key='A0123456789'.encode('utf-8'),  # 密钥
            key=INTRE_SECURE_KEY.encode('utf-8'),  # 密钥
            msg=input_string.encode('utf-8'),  # 输入字符串
            digestmod=hashlib.sha1  # 使用 SHA1 算法
        )
        desiget=hmac_sha1.hexdigest()
        return desiget
    @property
    def token(self) -> str:
        return self._access_token
        
    @property
    def __api_request_headers(self) -> dict:
        return {
            'Content-Type': 'application/json',
            'token': self._access_token,
        }
    def get_local_ip(self)->str:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except Exception as e:
            return '127.0.0.1'
    # pylint: disable=unused-private-member
    async def __intrehome_api_get_async(
        self, url_path: str, header:dict,params: dict,
        timeout: int = INTREHOME_HTTP_API_TIMEOUT
    ) -> dict:
        http_res = await self._session.get(
            url=f'{self._base_url}{url_path}',
            params=params,
            headers=header,
            timeout=timeout)
        if http_res.status == 401:
            raise IntreIoTHttpError(
                'intre api get failed, unauthorized(401)',
                IntreIoTErrorCode.CODE_HTTP_INVALID_ACCESS_TOKEN)
        if http_res.status != 200:
            raise IntreIoTHttpError(
                f'intre api get failed, {http_res.status}, '
                f'{url_path}, {params}')
        res_str = await http_res.text()
        res_obj: dict = json.loads(res_str)
        return res_obj
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        # 重点：在这里添加DNS错误和连接错误的捕获
        retry=retry_if_exception_type((
            TimeoutError,
            aiohttp.ClientConnectionError,
            asyncio.TimeoutError,
            ConnectionError,
            aiohttp.ClientConnectorError,  # 新增：捕获连接错误（包含DNS问题）
        )),
        reraise=True
    )

    async def __intrehome_api_post_async(
            self, url_path: str, header: dict, data: dict,
            timeout: int = INTREHOME_HTTP_API_TIMEOUT
        ) -> dict:
        
        # 拼接完整URL用于日志和错误信息
        url = f'{self._base_url}{url_path}'
        
        try:
            http_res = await self._session.post(
                url=url,
                json=data,
                headers=header,
                timeout=timeout
            )
            
            http_res.raise_for_status()
            res_str = await http_res.text()
            res_obj: dict = json.loads(res_str)
            return res_obj
            
        # 重点：在这里添加ClientConnectorError的区分处理
        except aiohttp.ClientConnectorError as e:
            error_msg = str(e)
            if any(keyword in error_msg for keyword in ["DNS", "Timeout while contacting DNS servers"]):
                _LOGGER.debug(f"DNS resolution failed for {url}: {error_msg}")
            else:
                _LOGGER.debug(f"Failed to connect to {url}: {error_msg}")
            # 不抛异常，返回None或自定义错误字典
            return None  # 或 return {"error": "connection_failed", "message": error_msg}

        # 处理HTTP响应错误（4xx/5xx状态码）
        except aiohttp.ClientResponseError as e:
            if 400 <= e.status < 500 and e.status != 429:
                _LOGGER.debug(f"Client error {e.status} for URL {url}")
            else:
                _LOGGER.debug(f"Server error {e.status} for URL {url}, will retry")
            return None  # 或根据状态码返回不同标识

        # 处理JSON解析错误
        except json.JSONDecodeError as e:
            _LOGGER.debug(f"Failed to parse JSON from {url}: {str(e)}")
            return None

        # 捕获其他所有异常
        except Exception as e:
            _LOGGER.debug(f"Request failed for {url}: {str(e)}, will retry")
            return None

    
    async def getToken(self,devicesn:str)-> None:
        rsp = await self.__intrehome_api_post_async(
            url_path='/device/v1/device/auth',
            header={},
            data={
                "appKey": "8069BB3019964B0B8F33E114A3B5FAFA",
                "appSecurity": "518E0DCF-27B2-4917-9761-AA47605FA718",
                "deviceSn": devicesn,
                "softVersionCode": INTRE_HA_CONTROL_VERSION,
                "lanIp": self._lanip,
                "productKey": "Intre.BGZ001"
            }
        )
        '''
        _LOGGER.debug(rsp)
        if rsp['code'] == 1:
            self._access_token = rsp['data']['token']
            return {
                'deviceId': rsp['data']['deviceId'],
                'token': rsp['data']['token']                  
            }
            return rsp['data']['deviceId']
        '''
        #_LOGGER.debug('111111111111111111111111111111111111111111')
        #_LOGGER.debug(rsp)
        if rsp['code'] == 1:
            self._access_token = rsp['data']['token']
            return rsp['data']

        return None

    async def getQRcode(self) -> dict:
        try:
            rsp = await self.__intrehome_api_post_async(
                url_path='/device/v1/device/login/qr-code/get',
                header=self.__api_request_headers({}),
                data={}
            )
        except Exception as e:
            _LOGGER.debug("获取二维码失败: %s", e)
            raise  # 或返回默认值 return {}

        _LOGGER.debug("API响应: %s", rsp)  # 改用debug级别记录正常日志‌:ml-citation{ref="2,7" data="citationList"}
        if rsp.get('code') == 1:  # 安全访问字典‌:ml-citation{ref="4,6" data="citationList"}
            return rsp['data']
        return {}  # 确保始终返回字典类型‌:ml-citation{ref="6,8" data="citationList"}
  
    async def updateToken(self)-> None:
        rsp = await self.__intrehome_api_post_async(
            url_path='/device/v1/device/token/prolong',
            header=self.__api_request_headers({}),
            data={}
        )
        _LOGGER.debug(rsp['msg'])

    def __api_request_headers(self,data:dict) -> dict:
        timestamp_ms = str(int(time.time() * 1000))
        return {
            'Content-Type': 'application/json',
            'token': self._access_token,
            'msgId':'1',
            'timestamp':timestamp_ms,
            'sign':self.__calculate_checksum('1',timestamp_ms,json.dumps(data))
        }

    def __md5_hash_password(self,password):
        md5 = hashlib.md5()
        md5.update(password.encode('utf-8'))
        return md5.hexdigest()

    async def get_mqtt_info(self,deviceSn:str)->dict:
        body={
            "deviceSn": deviceSn,
            "ipAddress": self._lanip
        }
        rsp = await self.__intrehome_api_post_async(
            url_path='/device/v1/device/mqtt-connect-info/get',
            header=self.__api_request_headers(data=body),
            data=body
        )
        _LOGGER.debug('get_mqtt_info')
        _LOGGER.debug(json.dumps(rsp))
        if rsp['code'] == 1:
            return rsp
        return None

    async def get_home_info(self,deviceId:str)->dict:
        body={
            "deviceId": deviceId
        }
        rsp = await self.__intrehome_api_post_async(
            url_path='/device/v1/device/home-info/get',
            header=self.__api_request_headers(data=body),
            data=body
        )

        _LOGGER.debug(json.dumps(rsp))
        if rsp['code'] == 1:
            return rsp['data']
        return None

    async def add_sub_device(self,product_info:dict)->None:
        rsp = await self.__intrehome_api_post_async(
            url_path='/device/v1/device/sub/add-without-bind-code',
            header=self.__api_request_headers(data=product_info),
            data=product_info
        )
        _LOGGER.debug('add_sub_device1111111111111111111111111111')
        _LOGGER.debug(json.dumps(rsp))
        if rsp['code'] == 1:
            return rsp['data']
        return None            

    async def add_dynamic_module(self,dynamic_info:str)->None:
        rsp = await self.__intrehome_api_post_async(
            url_path='/device/v1/dynamic-module/cover/add',
            header=self.__api_request_headers(data=dynamic_info),
            data=dynamic_info
        )
        _LOGGER.debug('add_dynamic_module1111111111111111111111111111')
        _LOGGER.debug(json.dumps(rsp))
        if rsp['code'] == 1:
            return rsp['data']
        return None 

    async def add_scene_module(self,scene_info:str)->None:
        rsp = await self.__intrehome_api_post_async(
            url_path='/device/v1/scene/association/add',
            header=self.__api_request_headers(data=scene_info),
            data=scene_info
        )
        #_LOGGER.debug('ADDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDD')
        #_LOGGER.debug(json.dumps(rsp))
        if rsp['code'] == 1:
            return rsp['data']
        return None

    async def get_scene_module(self)->None:
        rsp = await self.__intrehome_api_post_async(
            url_path='/device/v1/scene/association/get',
            header=self.__api_request_headers({}),
            data={}
        )
        #_LOGGER.debug(json.dumps(rsp))
        if rsp['code'] == 1:
            #_LOGGER.debug(json.dumps(rsp))
            return rsp['data']
        return None  

    async def delete_scene_module(self,identifier:str)->None:
        rsp = await self.__intrehome_api_post_async(
            url_path='/device/v1/scene/association/delete',
            header=self.__api_request_headers(data=identifier),
            data=identifier
        )
        #_LOGGER.debug("delete_scene_module: ")
        if rsp['code'] == 1:
            return rsp['data']
        return None 

    async def update_ha_product_version(self,haProVerInfo:str)->None:
        rsp = await self.__intrehome_api_post_async(
            url_path='/device/v1/device/ha/product-version/update',
            header=self.__api_request_headers(data=haProVerInfo),
            data=haProVerInfo
        )
        _LOGGER.debug('update_ha_product_version')
        _LOGGER.debug(json.dumps(rsp))
        if rsp['code'] == 1:
            return rsp['data']
        return None    

    async def update_device_version(self,deviceId:str,newVersionCode:str)->dict:
        body={
            "deviceId": deviceId,
            "productVersion": newVersionCode,
            "softVersionCode":INTRE_HA_CONTROL_VERSION,
            "lanIp": self._lanip,
            "gatewayProductKey": "Intre.BGZ001",
            "gatewaySoftVersionCode": INTRE_HA_CONTROL_VERSION,
            "gatewayDeviceId": deviceId
        }
        # 打印body内容（添加的日志）
        _LOGGER.debug(f"update_device_version 请求参数 body: {json.dumps(body, indent=2)}")
        rsp = await self.__intrehome_api_post_async(
            url_path='/device/v1/device/update',
            header=self.__api_request_headers(data=body),
            data=body
        )
        _LOGGER.debug('update_device_version')
        _LOGGER.debug(json.dumps(rsp))
        if rsp['code'] == 1:
            return rsp['data']
        return None

    async def device_sub_delete(self,deviceId:str)->None:
        body={
            "deviceId": deviceId,
            "deleteSub": 1
        }
        rsp = await self.__intrehome_api_post_async(
            url_path='/device/v1/device/sub/delete',
            header=self.__api_request_headers(data=body),
            data=body
        )
        _LOGGER.debug('device_sub_delete')
        _LOGGER.debug(json.dumps(rsp))
        if rsp['code'] == 1:
            return rsp['data']
        return None    
