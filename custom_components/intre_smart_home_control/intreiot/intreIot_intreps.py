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

IntreIoT Pub/Sub client.
"""
import asyncio
import json
import logging
import os
import queue
import random
import re
import ssl
import struct
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Callable, Optional, final
from .mqttMsgdef import (
    MQTT_SET_PROPERTY,
    MQTT_PROPERTY_REPORT,
    MQTT_EVENT_REPORT,
    MQTT_ONLINE_REPORT,
    MQTT_ONLINE_SET_WILL_REPORTT,
    MQTT_DATA_DEFINE_REPORT,
    MQTT_PROPERTY_SET_REPLY,
    MQTT_DEVICE_DOWN_TLS_LOG_REPORT,
    MQTT_DEVICE_TLS_LOG_REPORT,
    MQTT_BATCH_MODULE_PROP_REPORT,
    MQTT_BATCH_PROPERTY_SERVICE_REPLY,
    MQTT_SERVER_SET_REPLY)
from paho.mqtt.client import (
    MQTT_ERR_SUCCESS,
    MQTT_ERR_UNKNOWN,
    Client,
    MQTTv5)

# pylint: disable=relative-beyond-top-level
from .common import IntreIoTMatcher
from .const import (INTREHOME_MQTT_KEEPALIVE,MQTT_ToH)
from .intreIot_error import IntreIoTErrorCode, IntreIoTIntrepsError
from .intreIot_ev import IntreIoTEventLoop, TimeoutHandle

_LOGGER = logging.getLogger(__name__)


class IntrepsCmdType(Enum):
    """IntreIoT Pub/Sub command type."""
    CONNECT = 0
    DISCONNECT = auto()
    DEINIT = auto()
    SUB = auto()
    UNSUB = auto()
    CALL_API = auto()
    REG_BROADCAST = auto()
    UNREG_BROADCAST = auto()

    REG_INTREPS_STATE = auto()
    UNREG_INTREPS_STATE = auto()
    REG_DEVICE_STATE = auto()
    UNREG_DEVICE_STATE = auto()


@dataclass
class IntrepsCmd:
    """IntreIoT Pub/Sub command."""
    type_: IntrepsCmdType
    data: Any
    def __init__(self, type_: IntrepsCmdType, data: Any) -> None:
        self.type_ = type_
        self.data = data


@dataclass
class IntrepsRequest:
    """IntreIoT Pub/Sub request."""
    mid: int = None
    on_reply: Callable[[str, Any], None] = None
    on_reply_ctx: Any = None
    timer: TimeoutHandle = None


@dataclass
class IntrepsRequestData:
    """IntreIoT Pub/Sub request data."""
    topic: str = None
    payload: str = None
    on_reply: Callable[[str, Any], None] = None
    on_reply_ctx: Any = None
    timeout_ms: int = None
    
@dataclass
class IntrepsSendBroadcastData:
    """IntreIoT Pub/Sub send broadcast data."""
    topic: str = None
    payload: str = None


@dataclass
class IntrepsIncomingApiCall:
    """IntreIoT Pub/Sub incoming API call."""
    mid: int = None
    ret_topic: str = None
    timer: TimeoutHandle = None



@dataclass
class IntrepsBroadcast:
    """IntreIoT Pub/Sub broadcast."""
    topic: str = None
    handler: Callable[[str, str, Any], None] = None
    handler_ctx: Any = None

    def __str__(self) -> str:
        return f'{self.topic}, {id(self.handler)}, {id(self.handler_ctx)}'


class IntrepsRegBroadcast(IntrepsBroadcast):
    """IntreIoT Pub/Sub register broadcast."""


@dataclass
class IntrepsState:
    """IntreIoT Pub/Sub state."""
    key: str = None
    """
    str: key
    bool: intreps connect state
    """
    handler: Callable[[str, bool], asyncio.Future] = None


class IntrepsRegState(IntrepsState):
    """IntreIoT Pub/Sub register state."""


class IntreIoTDeviceState(Enum):
    """IntreIoT device state define."""
    DISABLE = 0
    OFFLINE = auto()
    ONLINE = auto()


@dataclass
class IntrepsDeviceState:
    """IntreIoT Pub/Sub device state."""
    did: str = None
    """handler
    str: did
    IntreIoTDeviceState: online/offline/disable
    Any: ctx
    """
    handler: Callable[[str, IntreIoTDeviceState, Any], None] = None
    handler_ctx: Any = None


class IntrepsRegDeviceState(IntrepsDeviceState):
    """IntreIoT Pub/Sub register device state."""


class IntrepsClient(ABC):
    """IntreIoT Pub/Sub client."""
    # pylint: disable=unused-argument
    MQTT_INTERVAL_MS = 1000
    INTREPS_QOS: int = 2
    UINT32_MAX: int = 0xFFFFFFFF
    INTREPS_RECONNECT_INTERVAL_MIN: int = 30000
    INTREPS_RECONNECT_INTERVAL_MAX: int = 600000
    INTREPS_SUB_PATCH: int = 300
    INTREPS_SUB_INTERVAL: int = 1000
    main_loop: asyncio.AbstractEventLoop
    _logger: logging.Logger
    _client_id: str
    _host: str
    _port: int
    _username: str
    _password: str
    _ca_file: str
    _cert_file: str
    _key_file: str

    _mqtt_logger: logging.Logger
    _mqtt: Client
    _mqtt_fd: int
    _mqtt_timer: TimeoutHandle
    _mqtt_state: bool

    _event_connect: asyncio.Event
    _event_disconnect: asyncio.Event
    _mev: IntreIoTEventLoop
    _intreps_thread: threading.Thread
    _intreps_queue: queue.Queue
    _cmd_event_fd: os.eventfd
    _intreps_reconnect_tag: bool
    _intreps_reconnect_interval: int
    _intreps_reconnect_timer: Optional[TimeoutHandle]
    _intreps_state_sub_map: dict[str, IntrepsState]
    _intreps_sub_pending_map: dict[str, int]
    _intreps_sub_pending_timer: Optional[TimeoutHandle]

    _on_intreps_cmd: Callable[[IntrepsCmd], None]
    _on_intreps_message: Callable[[str, bytes], None]
    _on_intreps_connect: Callable[[int, dict], None]
    _on_intreps_disconnect: Callable[[int, dict], None]

    def __init__(
            self, client_id: str, host: str, port: int,
            username: str = None, password: str = None,
            ca_file: str = None, cert_file: str = None, key_file: str = None,
            loop: Optional[asyncio.AbstractEventLoop] = None
    ) -> None:
        # MUST run with running loop
        self.main_loop = loop or asyncio.get_running_loop()
        self._logger = None
        self._client_id = client_id
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._ca_file = ca_file
        self._cert_file = cert_file
        self._key_file = key_file

        self._mqtt_logger = None
        self._mqtt_fd = -1
        self._mqtt_timer = None
        self._mqtt_state = False
        # mqtt init for API_VERSION2,
        # callback_api_version=CallbackAPIVersion.VERSION2,
        self._mqtt = Client(client_id=self._client_id, protocol=MQTTv5)
        
        self._mqtt.enable_logger(logger=self._mqtt_logger)

        # Intreps init
        self._event_connect = asyncio.Event()
        self._event_disconnect = asyncio.Event()
        self._intreps_reconnect_tag = False
        self._intreps_reconnect_interval = 0
        self._intreps_reconnect_timer = None
        self._intreps_state_sub_map = {}
        self._intreps_sub_pending_map = {}
        self._intreps_sub_pending_timer = None
        self._mev = IntreIoTEventLoop()
        self._intreps_queue = queue.Queue()
        self._cmd_event_fd = os.eventfd(0, os.O_NONBLOCK)
        self.mev_set_read_handler(
            self._cmd_event_fd, self.__intreps_cmd_read_handler, None)
        self._intreps_thread = threading.Thread(target=self.__intreps_loop_thread)
        self._intreps_thread.daemon = True
        self._intreps_thread.name = self._client_id
        self._intreps_thread.start()

        self._on_intreps_cmd = None
        self._on_intreps_message = None
        self._on_intreps_connect = None
        self._on_intreps_disconnect = None

    @property
    def client_id(self) -> str:
        return self._client_id

    @property
    def host(self) -> str:
        return self._host

    @property
    def port(self) -> int:
        return self._port

    @final
    @property
    def intreps_state(self) -> bool:
        """intreps connect state.

        Returns:
            bool: True: connected, False: disconnected
        """
        return self._mqtt and self._mqtt.is_connected()

    @final
    def intreps_deinit(self) -> None:
        self._intreps_send_cmd(type_=IntrepsCmdType.DEINIT, data=None)
        self._intreps_thread.join()
        self._intreps_thread = None

        self._logger = None
        self._client_id = None
        self._host = None
        self._port = None
        self._username = None
        self._password = None
        self._ca_file = None
        self._cert_file = None
        self._key_file = None
        self._mqtt_logger = None
        self._intreps_state_sub_map = None
        _LOGGER.debug("intreps_deinit")
        self._intreps_sub_pending_map = None
        self._intreps_sub_pending_timer = None

        self._event_connect = None
        self._event_disconnect = None

    def update_mqtt_password(self, password: str) -> None:
        self._password = password
        self._mqtt.username_pw_set(
            username=self._username, password=self._password)

    def log_debug(self, msg, *args, **kwargs) -> None:
        if self._logger:
            self._logger.debug(f'{self._client_id}, '+msg, *args, **kwargs)

    def log_info(self, msg, *args, **kwargs) -> None:
        if self._logger:
            self._logger.info(f'{self._client_id}, '+msg, *args, **kwargs)

    def log_error(self, msg, *args, **kwargs) -> None:
        if self._logger:
            self._logger.error(f'{self._client_id}, '+msg, *args, **kwargs)

    def enable_logger(self, logger: Optional[logging.Logger] = None) -> None:
        self._logger = logger

    def enable_mqtt_logger(
        self, logger: Optional[logging.Logger] = None
    ) -> None:
        if logger:
            self._mqtt.enable_logger(logger=logger)
        else:
            self._mqtt.disable_logger()

    @final
    def intreps_connect(self) -> None:
        """intreps connect."""
        return self._intreps_send_cmd(type_=IntrepsCmdType.CONNECT, data=None)

    @final
    async def intreps_connect_async(self) -> None:
        """intreps connect async."""
        self._intreps_send_cmd(type_=IntrepsCmdType.CONNECT, data=None)
        return await self._event_connect.wait()

    @final
    def intreps_disconnect(self) -> None:
        """intreps disconnect."""
        return self._intreps_send_cmd(type_=IntrepsCmdType.DISCONNECT, data=None)

    @final
    async def intreps_disconnect_async(self) -> None:
        """intreps disconnect async."""
        self._intreps_send_cmd(type_=IntrepsCmdType.DISCONNECT, data=None)
        return await self._event_disconnect.wait()

    @final
    def sub_intreps_state(
        self, key: str, handler: Callable[[str, bool], asyncio.Future]
    ) -> bool:
        _LOGGER.debug(f"sub_intreps_state: key={key}")
        """Subscribe intreps state.
        NOTICE: callback to main loop thread
        """
        _LOGGER.debug("REG_INTREPS_STATE")
        if isinstance(key, str) is False or handler is None:
            raise IntreIoTIntrepsError('invalid params')
        return self._intreps_send_cmd(
            type_=IntrepsCmdType.REG_INTREPS_STATE,
            data=IntrepsRegState(key=key, handler=handler))

    @final
    def unsub_intreps_state(self, key: str) -> bool:
        """Unsubscribe intreps state."""
        if isinstance(key, str) is False:
            raise IntreIoTIntrepsError('invalid params')
        return self._intreps_send_cmd(
            type_=IntrepsCmdType.UNREG_INTREPS_STATE, data=IntrepsRegState(key=key))

    @final
    def mev_set_timeout(
        self, timeout_ms: int, handler: Callable[[Any], None],
        handler_ctx: Any = None
    ) -> Optional[TimeoutHandle]:
        """set timeout.
        NOTICE: Internal function, only intreps threads are allowed to call
        """
        if self._mev is None:
            return None
        return self._mev.set_timeout(
            timeout_ms=timeout_ms,  handler=handler, handler_ctx=handler_ctx)

    @final
    def mev_clear_timeout(self, handle: TimeoutHandle) -> None:
        """clear timeout.
        NOTICE: Internal function, only intreps threads are allowed to call
        """
        if self._mev is None:
            return
        self._mev.clear_timeout(handle)

    @final
    def mev_set_read_handler(
        self, fd: int, handler: Callable[[Any], None], handler_ctx: Any
    ) -> bool:
        """set read handler.
        NOTICE: Internal function, only intreps threads are allowed to call
        """
        if self._mev is None:
            return False
        return self._mev.set_read_handler(
            fd=fd, handler=handler, handler_ctx=handler_ctx)

    @final
    def mev_set_write_handler(
        self, fd: int, handler: Callable[[Any], None], handler_ctx: Any
    ) -> bool:
        """set write handler.
        NOTICE: Internal function, only intreps threads are allowed to call
        """
        if self._mev is None:
            return False
        return self._mev.set_write_handler(
            fd=fd, handler=handler, handler_ctx=handler_ctx)

    @property
    def on_intreps_cmd(self) -> Callable[[IntrepsCmd], None]:
        return self._on_intreps_cmd

    @on_intreps_cmd.setter
    def on_intreps_cmd(self, handler: Callable[[IntrepsCmd], None]) -> None:
        """MUST set after __init__ done.
        NOTICE thread safe, this function will be called at the **intreps** thread
        """
        self._on_intreps_cmd = handler

    @property
    def on_intreps_message(self) -> Callable[[str, bytes], None]:
        return self._on_intreps_message

    @on_intreps_message.setter
    def on_intreps_message(self, handler: Callable[[str, bytes], None]) -> None:
        """MUST set after __init__ done.
        NOTICE thread safe, this function will be called at the **intreps** thread
        """
        self._on_intreps_message = handler

    @property
    def on_intreps_connect(self) -> Callable[[int, dict], None]:
        return self._on_intreps_connect

    @on_intreps_connect.setter
    def on_intreps_connect(self, handler: Callable[[int, dict], None]) -> None:
        """MUST set after __init__ done.
        NOTICE thread safe, this function will be called at the
        **main loop** thread
        """
        self._on_intreps_connect = handler

    @property
    def on_intreps_disconnect(self) -> Callable[[int, dict], None]:
        return self._on_intreps_disconnect

    @on_intreps_disconnect.setter
    def on_intreps_disconnect(self, handler: Callable[[int, dict], None]) -> None:
        """MUST set after __init__ done.
        NOTICE thread safe, this function will be called at the
        **main loop** thread
        """
        self._on_intreps_disconnect = handler

    @final
    def _intreps_sub_internal(self, topic: str) -> None:
        """intreps subscribe.
        NOTICE: Internal function, only intreps threads are allowed to call
        """
        self.__thread_check()
        if not self._mqtt or not self._mqtt.is_connected():
            return
        try:
            _LOGGER.debug('supcribeProp--->'+topic)
            if topic not in self._intreps_sub_pending_map:
                self._intreps_sub_pending_map[topic] = 0
            if not self._intreps_sub_pending_timer:
                self._intreps_sub_pending_timer = self.mev_set_timeout(
                    10, self.__intreps_sub_internal_pending_handler, topic)
        except Exception as err:  # pylint: disable=broad-exception-caught
            # Catch all exception
            self.log_error(f'intreps sub internal error, {topic}. {err}')

    @final
    def _intreps_unsub_internal(self, topic: str) -> None:
        """intreps unsubscribe.
        NOTICE: Internal function, only intreps threads are allowed to call
        """
        self.__thread_check()
        if not self._mqtt or not self._mqtt.is_connected():
            return
        try:
            result, mid = self._mqtt.unsubscribe(topic=topic)
            if result == MQTT_ERR_SUCCESS:
                self.log_debug(
                    f'intreps unsub internal success, {result}, {mid}, {topic}')
                return
            self.log_error(
                f'intreps unsub internal error, {result}, {mid}, {topic}')
        except Exception as err:  # pylint: disable=broad-exception-caught
            # Catch all exception
            self.log_error(f'intreps unsub internal error, {topic}, {err}')

    @final
    def _intreps_publish_internal(
        self, topic: str, payload: str | bytes,
        wait_for_publish: bool = False, timeout_ms: int = 10000
    ) -> bool:
        """intreps publish message.
        NOTICE: Internal function, only intreps threads are allowed to call

        """
        self.__thread_check()
        if not self._mqtt or not self._mqtt.is_connected():
            return False
        try:

            handle = self._mqtt.publish(
                topic=topic, payload=payload, qos=self.INTREPS_QOS)
            # self.log_debug(f'_intreps_publish_internal, {topic}, {payload}')
            if wait_for_publish is True:
                handle.wait_for_publish(timeout_ms/1000.0)
            return True
        except Exception as err:  # pylint: disable=broad-exception-caught
            # Catch other exception
            self.log_error(f'intreps publish internal error, {err}')
        return False

    @final
    def _intreps_send_cmd(self, type_: IntrepsCmdType, data: Any) -> bool:
        if self._intreps_queue is None or self._cmd_event_fd is None:
            raise IntreIoTIntrepsError('send intreps cmd disable')
        # Put data to queue
        self._intreps_queue.put(IntrepsCmd(type_=type_, data=data))
        # Write event fd
        os.eventfd_write(self._cmd_event_fd, 1)
        # self.log_debug(f'send intreps cmd, {type}, {data}')
        return True

    def __thread_check(self) -> None:
        if threading.current_thread() is not self._intreps_thread:
            raise IntreIoTIntrepsError('illegal call')

    def __intreps_cmd_read_handler(self, ctx: Any) -> None:
        fd_value = os.eventfd_read(self._cmd_event_fd)
        if fd_value == 0:
            return
        while self._intreps_queue.empty() is False:
            intreps_cmd: IntrepsCmd = self._intreps_queue.get(block=False)
            if intreps_cmd.type_ == IntrepsCmdType.CONNECT:
                self._intreps_reconnect_tag = True
                self.__intreps_try_reconnect(immediately=True)
            elif intreps_cmd.type_ == IntrepsCmdType.DISCONNECT:
                self._intreps_reconnect_tag = False
                self.__intreps_disconnect()
            elif intreps_cmd.type_ == IntrepsCmdType.DEINIT:
                self.log_info('intreps client recv deinit cmd')
                self.__intreps_disconnect()
                # Close cmd event fd
                if self._cmd_event_fd:
                    self.mev_set_read_handler(
                        self._cmd_event_fd, None, None)
                    os.close(self._cmd_event_fd)
                    self._cmd_event_fd = None
                if self._intreps_queue:
                    self._intreps_queue = None
                # ev loop stop
                if self._mev:
                    self._mev.loop_stop()
                    self._mev = None
                break
            elif intreps_cmd.type_ == IntrepsCmdType.REG_INTREPS_STATE:
                state: IntrepsState = intreps_cmd.data
                self._intreps_state_sub_map[state.key] = state
                self.log_debug(f'intreps register intreps state, {state.key}')
                _LOGGER.debug(f'intreps register intreps state, {state.key}')
            elif intreps_cmd.type_ == IntrepsCmdType.UNREG_INTREPS_STATE:
                state: IntrepsState = intreps_cmd.data
                del self._intreps_state_sub_map[state.key]
                self.log_debug(f'intreps unregister intreps state, {state.key}')
                _LOGGER.debug(f'intreps unregister intreps state, {state.key}')
            else:
                if self._on_intreps_cmd:
                    self._on_intreps_cmd(intreps_cmd=intreps_cmd)

    def __mqtt_read_handler(self, ctx: Any) -> None:
        self.__mqtt_loop_handler(ctx=ctx)

    def __mqtt_write_handler(self, ctx: Any) -> None:
        self.mev_set_write_handler(self._mqtt_fd, None, None)
        self.__mqtt_loop_handler(ctx=ctx)

    def __mqtt_timer_handler(self, ctx: Any) -> None:
        self.__mqtt_loop_handler(ctx=ctx)
        if self._mqtt:
            self._mqtt_timer = self.mev_set_timeout(
                self.MQTT_INTERVAL_MS, self.__mqtt_timer_handler, None)

    def __mqtt_loop_handler(self, ctx: Any) -> None:
        try:
            if self._mqtt:
                self._mqtt.loop_read()
            if self._mqtt:
                self._mqtt.loop_write()
            if self._mqtt:
                self._mqtt.loop_misc()
            if self._mqtt and self._mqtt.want_write():
                self.mev_set_write_handler(
                    self._mqtt_fd, self.__mqtt_write_handler, None)
        except Exception as err:  # pylint: disable=broad-exception-caught
            # Catch all exception
            self.log_error(f'__mqtt_loop_handler, {err}')
            raise err

    def __intreps_loop_thread(self) -> None:
        self.log_info('intreps_loop_thread start')
        # Set mqtt config
        if self._username:
            self._mqtt.username_pw_set(
                username=self._username, password=self._password)
        if (
            self._ca_file
            and self._cert_file
            and self._key_file
        ):
            self._mqtt.tls_set(
                tls_version=ssl.PROTOCOL_TLS_CLIENT,
                ca_certs=self._ca_file,
                certfile=self._cert_file,
                keyfile=self._key_file)
        else:
            self._mqtt.tls_set(ca_certs='/config/custom_components/intre_smart_home_control/intreiot/ca/service2.pem',tls_version=ssl.PROTOCOL_TLS_CLIENT)
        self._mqtt.tls_insecure_set(True)
        self._mqtt.on_connect = self.__on_connect
        self._mqtt.on_connect_fail = self.__on_connect_failed
        self._mqtt.on_disconnect = self.__on_disconnect
        self._mqtt.on_message = self.__on_message
        # Run event loop
        self._mev.loop_forever()
        self.log_info('intreps_loop_thread exit!')

    def __on_connect(self, client, user_data, flags, rc, props) -> None:
        if not self._mqtt.is_connected():
            return
        _LOGGER.debug(f"intreps connect, total items: {len(self._intreps_state_sub_map)}")
        self.log_info(f'intreps connect, {flags}, {rc}, {props}')
        self._mqtt_state = True
        if self._on_intreps_connect:
            self.mev_set_timeout(
                timeout_ms=0,
                handler=lambda ctx:
                    self._on_intreps_connect(rc, props))
        _LOGGER.debug(f"intreps connect111, total items: {len(self._intreps_state_sub_map)}")
        for item in self._intreps_state_sub_map.values():
            _LOGGER.debug("intreps connect333")
            _LOGGER.debug(item.key)
            if item.handler is None:
                continue
            _LOGGER.debug("intreps connect22222")
            self.main_loop.call_soon_threadsafe(
                self.main_loop.create_task,
                item.handler(item.key, True))
        # Resolve future
        self._event_connect.set()
        self._event_disconnect.clear()

    def __on_connect_failed(self, client, user_data, flags, rc) -> None:
        self.log_error(f'intreps connect failed, {flags}, {rc}')
        # Try to reconnect
        self.__intreps_try_reconnect()

    def __on_disconnect(self,  client, user_data, rc, props) -> None:
        _LOGGER.debug(f'intreps disconnect, {rc}, {props}')
        if self._mqtt_state:
            self.log_error(f'intreps disconnect, {rc}, {props}')
            self._mqtt_state = False
            _LOGGER.debug("self._mqtt_state = False")
            if self._mqtt_timer:
                self.mev_clear_timeout(self._mqtt_timer)
                self._mqtt_timer = None
                _LOGGER.debug("self._mqtt_timer")
            if self._mqtt_fd != -1:
                self.mev_set_read_handler(self._mqtt_fd, None, None)
                self.mev_set_write_handler(self._mqtt_fd, None, None)
                self._mqtt_fd = -1
                _LOGGER.debug("self._mqtt_fd")
            # Clear retry sub
            if self._intreps_sub_pending_timer:
                self.mev_clear_timeout(self._intreps_sub_pending_timer)
                self._intreps_sub_pending_timer = None
                _LOGGER.debug("self._intreps_sub_pending_timer")
            self._intreps_sub_pending_map = {}
            if self._on_intreps_disconnect:
                _LOGGER.debug("self._on_intreps_disconnect")
                self.mev_set_timeout(
                    timeout_ms=0,
                    handler=lambda ctx:
                        self._on_intreps_disconnect(rc, props))
            # Call state sub handler
            for item in self._intreps_state_sub_map.values():
                if item.handler is None:
                    continue
                _LOGGER.debug(f"item.key=: {item.key}")
                self.main_loop.call_soon_threadsafe(
                    self.main_loop.create_task,
                    item.handler(item.key, False))
        _LOGGER.debug("Call state sub handler")
        # Try to reconnect
        self.__intreps_try_reconnect()
        # Set event
        self._event_disconnect.set()
        self._event_connect.clear()

    def __on_message(self, client, user_data, msg) -> None:
        self._on_intreps_message(topic=msg.topic, payload=msg.payload)

    def __intreps_try_reconnect(self, immediately: bool = False) -> None:
        if self._intreps_reconnect_timer:
            self.mev_clear_timeout(self._intreps_reconnect_timer)
            self._intreps_reconnect_timer = None
        if not self._intreps_reconnect_tag:
            return
        interval: int = 0
        if not immediately:
            interval = self.__get_next_reconnect_time()
            self.log_error(
                'intreps try reconnect after %sms', interval)
        self._intreps_reconnect_timer = self.mev_set_timeout(
            interval, self.__intreps_connect, None)

    def __intreps_sub_internal_pending_handler(self, ctx: Any) -> None:
        subbed_count = 1
        for topic in list(self._intreps_sub_pending_map.keys()):
            if subbed_count > self.INTREPS_SUB_PATCH:
                break
            count = self._intreps_sub_pending_map[topic]
            if count > 3:
                self._intreps_sub_pending_map.pop(topic)
                self.log_error(f'retry intreps sub internal error, {topic}')
                continue
            subbed_count += 1
            _LOGGER.debug('supcribeProp->'+topic)
            result, mid = self._mqtt.subscribe(topic, qos=self.INTREPS_QOS)
            if result == MQTT_ERR_SUCCESS:
                self._intreps_sub_pending_map.pop(topic)
                self.log_debug(f'intreps sub internal success, {topic}')
                continue
            self._intreps_sub_pending_map[topic] = count+1
            self.log_error(
                f'retry intreps sub internal, {count}, {topic}, {result}, {mid}')

        if len(self._intreps_sub_pending_map):
            self._intreps_sub_pending_timer = self.mev_set_timeout(
                self.INTREPS_SUB_INTERVAL,
                self.__intreps_sub_internal_pending_handler, None)
        else:
            self._intreps_sub_pending_timer = None

    def __intreps_connect(self, ctx: Any = None) -> None:
        result = MQTT_ERR_UNKNOWN
        if self._intreps_reconnect_timer:
            self.mev_clear_timeout(self._intreps_reconnect_timer)
            self._intreps_reconnect_timer = None
        try:
            # Try clean mqtt fd before mqtt connect
            if self._mqtt_timer:
                self.mev_clear_timeout(self._mqtt_timer)
                self._mqtt_timer = None
            if self._mqtt_fd != -1:
                self.mev_set_read_handler(self._mqtt_fd, None, None)
                self.mev_set_write_handler(self._mqtt_fd, None, None)
                self._mqtt_fd = -1
            result = self._mqtt.connect(
                host=self._host, port=self._port,
                clean_start=True, keepalive=INTREHOME_MQTT_KEEPALIVE)
            _LOGGER.debug("INTREHOME_MQTT_KEEPALIVE")
            self.log_info(f'__intreps_connect success, {result}')
        except (TimeoutError, OSError) as error:
            self.log_error('__intreps_connect, connect error, %s', error)

        if result == MQTT_ERR_SUCCESS:
            self._mqtt_fd = self._mqtt.socket()
            self.log_debug(f'__intreps_connect, _mqtt_fd, {self._mqtt_fd}')
            self.mev_set_read_handler(
                self._mqtt_fd, self.__mqtt_read_handler, None)
            if self._mqtt.want_write():
                self.mev_set_write_handler(
                    self._mqtt_fd, self.__mqtt_write_handler, None)
            self._mqtt_timer = self.mev_set_timeout(
                self.MQTT_INTERVAL_MS, self.__mqtt_timer_handler, None)
        else:
            self.log_error(f'__intreps_connect error result, {result}')
            self.__intreps_try_reconnect()

    def __intreps_disconnect(self) -> None:
        if self._intreps_reconnect_timer:
            self.mev_clear_timeout(self._intreps_reconnect_timer)
            self._intreps_reconnect_timer = None
        if self._mqtt_timer:
            self.mev_clear_timeout(self._mqtt_timer)
            self._mqtt_timer = None
        if self._mqtt_fd != -1:
            self.mev_set_read_handler(self._mqtt_fd, None, None)
            self.mev_set_write_handler(self._mqtt_fd, None, None)
            self._mqtt_fd = -1
        self._mqtt.disconnect()

    def __get_next_reconnect_time(self) -> int:
        if self._intreps_reconnect_interval == 0:
            self._intreps_reconnect_interval = self.INTREPS_RECONNECT_INTERVAL_MIN
        else:
            self._intreps_reconnect_interval = min(
                self._intreps_reconnect_interval*2,
                self.INTREPS_RECONNECT_INTERVAL_MAX)
        return self._intreps_reconnect_interval


class IntrepsCloudClient(IntrepsClient):
    """IntreIoT Pub/Sub Cloud Client."""
    # pylint: disable=unused-argument
    # pylint: disable=inconsistent-quotes
    _msg_matcher: IntreIoTMatcher

    def __init__(
            self, uuid: str, host: str, username: str,
            password: str, port: int = 8883,
            loop: Optional[asyncio.AbstractEventLoop] = None
    ) -> None:
        self._msg_matcher = IntreIoTMatcher()
        super().__init__(
            client_id=uuid, host=host,
            port=port, username=username, password=password, loop=loop)
        self.on_intreps_cmd = self.__on_intreps_cmd_handler
        self.on_intreps_message = self.__on_intreps_message_handler
        self.on_intreps_connect = self.__on_intreps_connect_handler
        self.on_intreps_disconnect = self.__on_intreps_disconnect_handler

    def deinit(self) -> None:
        self.intreps_deinit()
        self._msg_matcher = None
        self.on_intreps_cmd = None
        self.on_intreps_message = None
        self.on_intreps_connect = None

    def set_will_news(self,token:str,productkey:str,deviceid:str)->None:
        mqttmsg=MQTT_ONLINE_SET_WILL_REPORTT(token=token,productkey=productkey,deviceid=deviceid,onlinestatus=0)
        self._mqtt.will_set(
            topic=mqttmsg['topic'],
            payload=json.dumps(mqttmsg['payload']),
            qos=1,
            retain=True
        )
        _LOGGER.debug('set_will_news')
    @final
    def connect(self) -> None:
        self.intreps_connect()

    @final
    async def connect_async(self) -> None:
        await self.intreps_connect_async()

    @final
    def disconnect(self) -> None:
        self.intreps_disconnect()
        self._msg_matcher = IntreIoTMatcher()

    @final
    async def disconnect_async(self) -> None:
        await self.intreps_disconnect_async()
        self._msg_matcher = IntreIoTMatcher()

    def update_access_token(self, access_token: str) -> bool:
        if not isinstance(access_token, str):
            raise IntreIoTIntrepsError('invalid token')
        return self.update_mqtt_password(password=access_token)



    @final
    def sub_mqtt_prop_set(
        self, topic: str, handler: Callable[[dict, Any], None],handler_ctx: Any = None
    ) -> bool:
        def sub_callback(topic: str, payload: str, ctx: Any) -> bool:
            try:
                msg: dict = json.loads(payload)
            except json.JSONDecodeError:
                self.log_error(
                    f'on_prop_msg, invalid msg, {topic}, {payload}')
                return
            if handler:
                self.log_error('on properties_changed, %s', payload)
                handler(data=msg)
        return self.__reg_broadcast(
            topic=topic, handler=sub_callback, handler_ctx=handler_ctx)
    
    @final
    def sub_mqtt_service_call(
        self, topic: str, handler: Callable[[dict, Any], None],handler_ctx: Any = None
    ) -> bool:
        def sub_callback(topic: str, payload: str, ctx: Any) -> bool:
            try:
                msg: dict = json.loads(payload)
            except json.JSONDecodeError:
                self.log_error(
                    f'on_prop_msg, invalid msg, {topic}, {payload}')
                return
            if handler:
                self.log_error('on properties_changed, %s', payload)
                handler(data=msg)
        return self.__reg_broadcast(
            topic=topic, handler=sub_callback, handler_ctx=handler_ctx)

    @final
    def sub_mqtt_bacth_service_prop(    
        self, topic: str, handler: Callable[[dict, Any], None],handler_ctx: Any = None
    ) -> bool:
        def sub_callback(topic: str, payload: str, ctx: Any) -> bool:
            try:
                msg: dict = json.loads(payload)
            except json.JSONDecodeError:
                self.log_error(
                    f'on_prop_msg, invalid msg, {topic}, {payload}')
                return
            if handler:
                self.log_error('on properties_changed, %s', payload)
                handler(data=msg['data'])
        return self.__reg_broadcast(
            topic=topic, handler=sub_callback, handler_ctx=handler_ctx)
    @final
    def sub_mqtt_down_online_report_reply(    
        self, topic: str, handler: Callable[[dict, Any], None],handler_ctx: Any = None
    ) -> bool:
        def sub_callback(topic: str, payload: str, ctx: Any) -> bool:
            try:
                msg: dict = json.loads(payload)
            except json.JSONDecodeError:
                self.log_error(
                    f'on_prop_msg, invalid msg, {topic}, {payload}')
                return
            if handler:
                self.log_error('on properties_changed, %s', payload)
                handler(data=msg)
        return self.__reg_broadcast(
            topic=topic, handler=sub_callback, handler_ctx=handler_ctx)
    @final
    def sub_mqtt_down_data_define_report_reply(    
        self, topic: str, handler: Callable[[dict, Any], None],handler_ctx: Any = None
    ) -> bool:
        def sub_callback(topic: str, payload: str, ctx: Any) -> bool:
            try:
                msg: dict = json.loads(payload)
            except json.JSONDecodeError:
                self.log_error(
                    f'on_prop_msg, invalid msg, {topic}, {payload}')
                return
            if handler:
                self.log_error('on properties_changed, %s', payload)
                handler(data=msg)
        return self.__reg_broadcast(
            topic=topic, handler=sub_callback, handler_ctx=handler_ctx)

    @final
    def sub_mqtt_down_tls_event_report_reply(      
        self, topic: str, handler: Callable[[dict, Any], None],handler_ctx: Any = None
    ) -> bool:
        def sub_callback(topic: str, payload: str, ctx: Any) -> bool:
            try:
                msg: dict = json.loads(payload)
            except json.JSONDecodeError:
                self.log_error(
                    f'on_prop_msg, invalid msg, {topic}, {payload}')
                return
            if handler:
                self.log_error('on properties_changed, %s', payload)
                handler(data=msg)
        return self.__reg_broadcast(
            topic=topic, handler=sub_callback, handler_ctx=handler_ctx)

    @final
    def sub_mqtt_down_tls_property_report_reply(      
        self, topic: str, handler: Callable[[dict, Any], None],handler_ctx: Any = None
    ) -> bool:
        def sub_callback(topic: str, payload: str, ctx: Any) -> bool:
            try:
                msg: dict = json.loads(payload)
            except json.JSONDecodeError:
                self.log_error(
                    f'on_prop_msg, invalid msg, {topic}, {payload}')
                return
            if handler:
                self.log_error('on properties_changed, %s', payload)
                handler(data=msg)
        return self.__reg_broadcast(
            topic=topic, handler=sub_callback, handler_ctx=handler_ctx) 

    def __intreps_publish(
            self, topic: str, payload: str | bytes, wait_for_publish: bool = False,
            timeout_ms: int = 10000
    ) -> bool:
        return self._intreps_publish_internal(
            topic=topic.strip(), payload=payload,
            wait_for_publish=wait_for_publish, timeout_ms=timeout_ms)

    def __request(
            self, topic: str, payload: str,
            on_reply: Callable[[str, Any], None],
            on_reply_ctx: Any = None, timeout_ms: int = 10000
    ) -> bool:
        if topic is None or payload is None:
            raise IntreIoTIntrepsError('invalid params')
        req_data: IntrepsRequestData = IntrepsRequestData()
        req_data.topic = topic
        req_data.payload = payload
        req_data.on_reply = on_reply
        req_data.on_reply_ctx = on_reply_ctx
        req_data.timeout_ms = timeout_ms
        return self._intreps_send_cmd(type_=IntrepsCmdType.CALL_API, data=req_data)

    @final
    async def __request_async(
        self, topic: str, payload: str, timeout_ms: int = 10000
    ) -> bool:
        return self.__request(
                topic=topic,
                payload=payload,
                on_reply=None,
                timeout_ms=timeout_ms)
    async def report_online_async(self, token:str,productkey:str,deviceid: str)->dict:   
        _LOGGER.debug('report_online_async'+token)
        mqttmsg=MQTT_ONLINE_REPORT(token=token,productkey=productkey,deviceid=deviceid,onlinestatus=1)

        result_obj = await self.__request_async(
            topic=mqttmsg['topic'],
            payload=json.dumps(mqttmsg['payload']),
            timeout_ms=10000)
    @final
    async def data_define_report_async(self, token:str,productkey:str,deviceid:str,data_define:list)->dict:   
        
        mqttmsg=MQTT_DATA_DEFINE_REPORT(token=token,productkey=productkey,deviceid=deviceid,data_define=data_define)

        result_obj = await self.__request_async(
            topic=mqttmsg['topic'],
            payload=json.dumps(mqttmsg['payload']),
            timeout_ms=10000)
        # 打印MQTT请求结果对象
        _LOGGER.debug(f"data_define_report_async MQTT属性上报返回结果: {result_obj}") 
    @final
    async def set_prop_async(
        self, token,deviceid: str, moduleKey: str, propKey: str, propValue: str,timeout_ms: int = 10000) -> dict:
        _LOGGER.debug('setProperty'+token)
        mqttmsg=MQTT_SET_PROPERTY(token=token,deviceid=deviceid,moduleKey=moduleKey,propKey=propKey,propValue=propValue)

        result_obj = await self.__request_async(
            topic=mqttmsg['topic'],
            payload=json.dumps(mqttmsg['payload']),
            timeout_ms=timeout_ms)
    
    @final
    async def report_batch_module_prop_async(self, token,productkey:str,deviceid: str,batch_modules:list) -> dict:
        mqttmsg=MQTT_BATCH_MODULE_PROP_REPORT(token=token,productkey=productkey,deviceid=deviceid,batch_modules=batch_modules)

        result_obj = await self.__request_async(
            topic=mqttmsg['topic'],
            payload=json.dumps(mqttmsg['payload']),
            timeout_ms=10000)
        # 打印MQTT请求结果对象
        _LOGGER.debug(f"report_batch_module_prop_async MQTT属性上报返回结果: {result_obj}") 

    @final
    async def report_device_tsl_log_async(self, token,productkey:str,deviceid: str,tls_logs:list) -> dict:
        mqttmsg=MQTT_DEVICE_TLS_LOG_REPORT(token=token,productkey=productkey,deviceid=deviceid,tls_logs=tls_logs)

        result_obj = await self.__request_async(
            topic=mqttmsg['topic'],
            payload=json.dumps(mqttmsg['payload']),
            timeout_ms=10000)
        # 打印MQTT请求结果对象
        _LOGGER.debug(f"report_device_tsl_log_async MQTT属性上报返回结果: {result_obj}")

    @final
    async def report_device_down_tsl_log_async(self, token,productkey:str,deviceid: str) -> dict:
        mqttmsg=MQTT_DEVICE_DOWN_TLS_LOG_REPORT(token=token,productkey=productkey,deviceid=deviceid)

        result_obj = await self.__request_async(
            topic=mqttmsg['topic'],
            payload=json.dumps(mqttmsg['payload']),
            timeout_ms=10000)
        # 打印MQTT请求结果对象
        _LOGGER.debug(f"report_device_down_tsl_log_async MQTT属性上报返回结果: {result_obj}")      

    @final
    async def report_prop_async(self, token,productkey:str,deviceid: str, modulekey:str,propkey:str,prop_value:str) -> dict:
        mqttmsg=MQTT_PROPERTY_REPORT(token=token,productkey=productkey,deviceid=deviceid,modulekey=modulekey,propkey=propkey,prop_value=prop_value)

        result_obj = await self.__request_async(
            topic=mqttmsg['topic'],
            payload=json.dumps(mqttmsg['payload']),
            timeout_ms=10000)
        # 打印MQTT请求结果对象
        _LOGGER.debug(f"propkey MQTT属性上报返回结果: {result_obj}") 

    @final
    async def report_event_async(self, token,productkey:str,deviceid: str, modulekey:str,eventkey:str,event_value:str) -> dict:
        mqttmsg=MQTT_EVENT_REPORT(token=token,productkey=productkey,deviceid=deviceid,modulekey=modulekey,eventkey=eventkey,event_value=event_value)

        result_obj = await self.__request_async(
            topic=mqttmsg['topic'],
            payload=json.dumps(mqttmsg['payload']),
            timeout_ms=10000)
        # 打印MQTT请求结果对象
        _LOGGER.debug(f"eventkey MQTT属性上报返回结果: {result_obj}")     
    
    @final
    async def prop_set_reply_async(self, token,productkey:str,deviceid: str,msgid:str,code:str) -> dict:
        mqttmsg=MQTT_PROPERTY_SET_REPLY(token=token,productkey=productkey,deviceid=deviceid,msgid=msgid,code=code)
        result_obj = await self.__request_async(
            topic=mqttmsg['topic'],
            payload=json.dumps(mqttmsg['payload']),
            timeout_ms=10000)
    
    @final  
    async def prop_service_set_reply_async(self, token,productkey:str,deviceid: str,msgid:str,code:str) -> dict:
        mqttmsg=MQTT_BATCH_PROPERTY_SERVICE_REPLY(token=token,productkey=productkey,deviceid=deviceid,msgid=msgid,code=code)
        result_obj = await self.__request_async(
            topic=mqttmsg['topic'],
            payload=json.dumps(mqttmsg['payload']),
            timeout_ms=10000)   
            
    @final
    async def service_set_reply_async(self, token,productkey:str,deviceid: str,moduleKey: str,serviceKey: str,msgid:str,code:str) -> dict:
        mqttmsg=MQTT_SERVER_SET_REPLY(token=token,productkey=productkey,deviceid=deviceid,moduleKey=moduleKey,serviceKey=serviceKey,msgid=msgid,code=code)
        result_obj = await self.__request_async(
            topic=mqttmsg['topic'],
            payload=json.dumps(mqttmsg['payload']),
            timeout_ms=10000)     
            
    @final
    def __on_intreps_cmd_handler(self, intreps_cmd: IntrepsCmd) -> None:
        if intreps_cmd.type_ == IntrepsCmdType.CALL_API:
            req_data: IntrepsRequestData = intreps_cmd.data
            pub_topic: str = f'{MQTT_ToH}{req_data.topic}'
            _LOGGER.debug(f"9999999999999999999999999: {pub_topic}")  # 打印订阅的 topic
            _LOGGER.debug(f"11111111111111111111: {req_data.payload}")  # 打印订阅的 topic
            result = self.__intreps_publish(topic=pub_topic, payload=req_data.payload)  
        elif intreps_cmd.type_ == IntrepsCmdType.REG_BROADCAST:
            reg_bc: IntrepsRegBroadcast = intreps_cmd.data
            if not self._msg_matcher.get(topic=reg_bc.topic):
                sub_bc: IntrepsBroadcast = IntrepsBroadcast(
                    topic=reg_bc.topic, handler=reg_bc.handler,
                    handler_ctx=reg_bc.handler_ctx)
                self._msg_matcher[reg_bc.topic] = sub_bc
                self._intreps_sub_internal(topic=reg_bc.topic)
            else:
                self.log_debug(f'intreps cloud re-reg broadcast, {reg_bc.topic}')
        elif intreps_cmd.type_ == IntrepsCmdType.UNREG_BROADCAST:
            unreg_bc: IntrepsRegBroadcast = intreps_cmd.data
            if self._msg_matcher.get(topic=unreg_bc.topic):
                del self._msg_matcher[unreg_bc.topic]
                self._intreps_unsub_internal(topic=unreg_bc.topic)
        else:
            self.log_error(
                f'intreps local recv unknown cmd, {intreps_cmd.type_}, '
                f'{intreps_cmd.data}')


    def __reg_broadcast(
        self, topic: str, handler: Callable[[str, str, Any], None],
        handler_ctx: Any = None
    ) -> bool:
        return self._intreps_send_cmd(
            type_=IntrepsCmdType.REG_BROADCAST,
            data=IntrepsRegBroadcast(
                topic=topic, handler=handler, handler_ctx=handler_ctx))

    def __unreg_broadcast(self, topic: str) -> bool:
        return self._intreps_send_cmd(
            type_=IntrepsCmdType.UNREG_BROADCAST,
            data=IntrepsRegBroadcast(topic=topic))

    def __on_intreps_connect_handler(self, rc, props) -> None:
        """sub topic."""
        for topic, _ in list(
                self._msg_matcher.iter_all_nodes()):
            self._intreps_sub_internal(topic=topic)

    def __on_intreps_disconnect_handler(self, rc, props) -> None:
        """unsub topic."""
        pass

    def __on_intreps_message_handler(self, topic: str, payload) -> None:
        """
        NOTICE thread safe, this function will be called at the **intreps** thread
        """
        # broadcast
        bc_list: list[IntrepsBroadcast] = list(
            self._msg_matcher.iter_match(topic))
        if not bc_list:
            return
        # self.log_debug(f"on broadcast, {topic}, {payload}")
        for item in bc_list or []:
            if item.handler is None:
                continue
            # NOTICE: call threadsafe
            self.main_loop.call_soon_threadsafe(
                item.handler, topic, payload, item.handler_ctx)


