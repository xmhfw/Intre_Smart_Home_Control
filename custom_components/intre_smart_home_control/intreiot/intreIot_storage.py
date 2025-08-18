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

IntreIoT storage and certificate management.
"""
import os
import asyncio
import binascii
import json
import shutil
import time
import traceback
import hashlib
from datetime import datetime, timezone
from enum import Enum, auto
from pathlib import Path
from typing import Any, Optional, Union
import logging
from urllib.request import Request, urlopen
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from cryptography.x509.oid import NameOID
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ed25519

# pylint: disable=relative-beyond-top-level
from .common import load_json_file

from .intreIot_error import IntreIoTCertError, IntreIoTError, IntreIoTStorageError

_LOGGER = logging.getLogger(__name__)


class IntreIoTStorageType(Enum):
    LOAD = auto()
    LOAD_FILE = auto()
    SAVE = auto()
    SAVE_FILE = auto()
    DEL = auto()
    DEL_FILE = auto()
    CLEAR = auto()


class IntreIoTStorage:
    """File management.

    User data will be stored in the `.storage` directory of Home Assistant.
    """
    _main_loop: asyncio.AbstractEventLoop = None
    _file_future: dict[str, tuple[IntreIoTStorageType, asyncio.Future]]

    _root_path: str = None

    def __init__(
        self, root_path: str,
        loop: Optional[asyncio.AbstractEventLoop] = None
    ) -> None:
        """Initialize with a root path."""
        self._main_loop = loop or asyncio.get_running_loop()
        self._file_future = {}

        self._root_path = os.path.abspath(root_path)
        os.makedirs(self._root_path, exist_ok=True)

        _LOGGER.debug('root path, %s', self._root_path)

    def __get_full_path(self, domain: str, name: str, suffix: str) -> str:
        return os.path.join(
            self._root_path, domain, f'{name}.{suffix}')

    def __add_file_future(
        self, key: str, op_type: IntreIoTStorageType, fut: asyncio.Future
    ) -> None:
        def fut_done_callback(fut: asyncio.Future):
            del fut
            self._file_future.pop(key, None)

        fut.add_done_callback(fut_done_callback)
        self._file_future[key] = op_type, fut

    def __load(
        self, full_path: str, type_: type = bytes, with_hash_check: bool = True
    ) -> Union[bytes, str, dict, list, None]:
        if not os.path.exists(full_path):
            _LOGGER.debug('load error, file does not exist, %s', full_path)
            return None
        if not os.access(full_path, os.R_OK):
            _LOGGER.debug('load error, file not readable, %s', full_path)
            return None
        try:
            with open(full_path, 'rb') as r_file:
                r_data: bytes = r_file.read()
                if r_data is None:
                    _LOGGER.debug('load error, empty file, %s', full_path)
                    return None
                data_bytes: bytes = None
                # Hash check
                if with_hash_check:
                    if len(r_data) <= 32:
                        return None
                    data_bytes = r_data[:-32]
                    hash_value = r_data[-32:]
                    if hashlib.sha256(data_bytes).digest() != hash_value:
                        _LOGGER.debug(
                            'load error, hash check failed, %s', full_path)
                        return None
                else:
                    data_bytes = r_data
                if type_ == bytes:
                    return data_bytes
                if type_ == str:
                    return str(data_bytes, 'utf-8')
                if type_ in [dict, list]:
                    return json.loads(data_bytes)
                _LOGGER.debug(
                    'load error, unsupported data type, %s', type_.__name__)
                return None
        except (OSError, TypeError) as e:
            _LOGGER.debug('load error, %s, %s', e, traceback.format_exc())
            return None

    def load(
        self, domain: str, name: str, type_: type = bytes
    ) -> Union[bytes, str, dict, list, None]:
        full_path = self.__get_full_path(
            domain=domain, name=name, suffix=type_.__name__)
        return self.__load(full_path=full_path, type_=type_)

    async def load_async(
        self, domain: str, name: str, type_: type = bytes
    ) -> Union[bytes, str, dict, list, None]:
        full_path = self.__get_full_path(
            domain=domain, name=name, suffix=type_.__name__)
        if full_path in self._file_future:
            # Waiting for the last task to be completed
            op_type, fut = self._file_future[full_path]
            if op_type == IntreIoTStorageType.LOAD:
                if not fut.done():
                    return await fut
            else:
                await fut
        fut = self._main_loop.run_in_executor(
            None, self.__load, full_path, type_)
        if not fut.done():
            self.__add_file_future(full_path, IntreIoTStorageType.LOAD, fut)
        return await fut

    def __save(
        self, full_path: str, data: Union[bytes, str, dict, list, None],
        cover: bool = True, with_hash: bool = True
    ) -> bool:
        if data is None:
            _LOGGER.debug('save error, save data is None')
            return False
        if os.path.exists(full_path):
            if not cover:
                _LOGGER.debug('save error, file exists, cover is False')
                return False
            if not os.access(full_path, os.W_OK):
                _LOGGER.debug('save error, file not writeable, %s', full_path)
                return False
        else:
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
        try:
            type_: type = type(data)
            w_bytes: bytes = None
            if type_ == bytes:
                w_bytes = data
            elif type_ == str:
                w_bytes = data.encode('utf-8')
            elif type_ in [dict, list]:
                w_bytes = json.dumps(data).encode('utf-8')
            else:
                _LOGGER.debug(
                    'save error, unsupported data type, %s', type_.__name__)
                return False
            with open(full_path, 'wb') as w_file:
                w_file.write(w_bytes)
                if with_hash:
                    w_file.write(hashlib.sha256(w_bytes).digest())
            return True
        except (OSError, TypeError) as e:
            _LOGGER.debug('save error, %s, %s', e, traceback.format_exc())
            return False

    def save(
        self, domain: str, name: str, data: Union[bytes, str, dict, list, None]
    ) -> bool:
        full_path = self.__get_full_path(
            domain=domain, name=name, suffix=type(data).__name__)
        return self.__save(full_path=full_path, data=data)

    async def save_async(
        self, domain: str, name: str, data: Union[bytes, str, dict, list, None]
    ) -> bool:
        full_path = self.__get_full_path(
            domain=domain, name=name, suffix=type(data).__name__)
        if full_path in self._file_future:
            # Waiting for the last task to be completed
            fut = self._file_future[full_path][1]
            await fut
        fut = self._main_loop.run_in_executor(
            None, self.__save, full_path, data)
        if not fut.done():
            self.__add_file_future(full_path, IntreIoTStorageType.SAVE, fut)
        return await fut

    def __remove(self, full_path: str) -> bool:
        item = Path(full_path)
        if item.is_file() or item.is_symlink():
            item.unlink()
        return True

    def remove(self, domain: str, name: str, type_: type) -> bool:
        full_path = self.__get_full_path(
            domain=domain, name=name, suffix=type_.__name__)
        return self.__remove(full_path=full_path)

    async def remove_async(self, domain: str, name: str, type_: type) -> bool:
        full_path = self.__get_full_path(
            domain=domain, name=name, suffix=type_.__name__)
        if full_path in self._file_future:
            # Waiting for the last task to be completed
            op_type, fut = self._file_future[full_path]
            if op_type == IntreIoTStorageType.DEL:
                if not fut.done():
                    return await fut
            else:
                await fut
        fut = self._main_loop.run_in_executor(None, self.__remove, full_path)
        if not fut.done():
            self.__add_file_future(full_path, IntreIoTStorageType.DEL, fut)
        return await fut

    def __remove_domain(self, full_path: str) -> bool:
        path_obj = Path(full_path)
        if path_obj.exists():
            # Recursive deletion
            shutil.rmtree(path_obj)
        return True

    def remove_domain(self, domain: str) -> bool:
        full_path = os.path.join(self._root_path, domain)
        return self.__remove_domain(full_path=full_path)

    async def remove_domain_async(self, domain: str) -> bool:
        full_path = os.path.join(self._root_path, domain)
        if full_path in self._file_future:
            # Waiting for the last task to be completed
            op_type, fut = self._file_future[full_path]
            if op_type == IntreIoTStorageType.DEL:
                if not fut.done():
                    return await fut
            else:
                await fut
        # Waiting domain tasks finish
        for path, value in self._file_future.items():
            if path.startswith(full_path):
                await value[1]
        fut = self._main_loop.run_in_executor(
            None, self.__remove_domain, full_path)
        if not fut.done():
            self.__add_file_future(full_path, IntreIoTStorageType.DEL, fut)
        return await fut

    def get_names(self, domain: str, type_: type) -> list[str]:
        path: str = os.path.join(self._root_path, domain)
        type_str = f'.{type_.__name__}'
        names: list[str] = []
        for item in Path(path).glob(f'*{type_str}'):
            if not item.is_file() and not item.is_symlink():
                continue
            names.append(item.name.replace(type_str, ''))
        return names

    def file_exists(self, domain: str, name_with_suffix: str) -> bool:
        return os.path.exists(
            os.path.join(self._root_path, domain, name_with_suffix))

    def save_file(
        self, domain: str, name_with_suffix: str, data: bytes
    ) -> bool:
        if not isinstance(data, bytes):
            _LOGGER.debug('save file error, file must be bytes')
            return False
        full_path = os.path.join(self._root_path, domain, name_with_suffix)
        return self.__save(full_path=full_path, data=data,  with_hash=False)

    async def save_file_async(
        self, domain: str, name_with_suffix: str, data: bytes
    ) -> bool:
        if not isinstance(data, bytes):
            _LOGGER.debug('save file error, file must be bytes')
            return False
        full_path = os.path.join(self._root_path, domain, name_with_suffix)
        if full_path in self._file_future:
            # Waiting for the last task to be completed
            fut = self._file_future[full_path][1]
            await fut
        fut = self._main_loop.run_in_executor(
            None, self.__save, full_path, data, True, False)
        if not fut.done():
            self.__add_file_future(full_path, IntreIoTStorageType.SAVE_FILE, fut)
        return await fut

    def load_file(self, domain: str, name_with_suffix: str) -> Optional[bytes]:
        full_path = os.path.join(self._root_path, domain, name_with_suffix)
        return self.__load(
            full_path=full_path, type_=bytes, with_hash_check=False)

    async def load_file_async(
        self, domain: str, name_with_suffix: str
    ) -> Optional[bytes]:
        full_path = os.path.join(self._root_path, domain, name_with_suffix)
        if full_path in self._file_future:
            # Waiting for the last task to be completed
            op_type, fut = self._file_future[full_path]
            if op_type == IntreIoTStorageType.LOAD_FILE:
                if not fut.done():
                    return await fut
            else:
                await fut
        fut = self._main_loop.run_in_executor(
            None, self.__load, full_path, bytes, False)
        if not fut.done():
            self.__add_file_future(full_path, IntreIoTStorageType.LOAD_FILE, fut)
        return await fut

    def remove_file(self, domain: str, name_with_suffix: str) -> bool:
        full_path = os.path.join(self._root_path, domain, name_with_suffix)
        return self.__remove(full_path=full_path)

    async def remove_file_async(
        self, domain: str, name_with_suffix: str
    ) -> bool:
        full_path = os.path.join(self._root_path, domain, name_with_suffix)
        if full_path in self._file_future:
            # Waiting for the last task to be completed
            op_type, fut = self._file_future[full_path]
            if op_type == IntreIoTStorageType.DEL_FILE:
                if not fut.done():
                    return await fut
            else:
                await fut
        fut = self._main_loop.run_in_executor(None, self.__remove, full_path)
        if not fut.done():
            self.__add_file_future(full_path, IntreIoTStorageType.DEL_FILE, fut)
        return await fut

    def clear(self) -> bool:
        root_path = Path(self._root_path)
        for item in root_path.iterdir():
            if item.is_file() or item.is_symlink():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)
        return True

    async def clear_async(self) -> bool:
        if self._root_path in self._file_future:
            op_type, fut = self._file_future[self._root_path]
            if op_type == IntreIoTStorageType.CLEAR and not fut.done():
                return await fut
        # Waiting all future resolve
        for value in self._file_future.values():
            await value[1]

        fut = self._main_loop.run_in_executor(None, self.clear)
        if not fut.done():
            self.__add_file_future(
                self._root_path, IntreIoTStorageType.CLEAR, fut)
        return await fut

    def update_user_config(
        self, uid: str, cloud_server: str, config: Optional[dict[str, Any]],
        replace: bool = False
    ) -> bool:
        if config is not None and len(config) == 0:
            # Do nothing
            return True

        config_domain = 'IntreIot_config'
        config_name = f'{uid}_{cloud_server}'
        if config is None:
            # Remove config file
            return self.remove(
                domain=config_domain, name=config_name, type_=dict)
        if replace:
            # Replace config file
            return self.save(
                domain=config_domain, name=config_name, data=config)
        local_config = (self.load(domain=config_domain,
                        name=config_name, type_=dict)) or {}
        local_config.update(config)
        return self.save(
            domain=config_domain, name=config_name, data=local_config)

    async def update_user_config_async(
        self, uid: str, cloud_server: str, config: Optional[dict[str, Any]],
        replace: bool = False
    ) -> bool:
        """Update user configuration.

        Args:
            uid (str): user_id
            config (Optional[dict[str]]):
                remove config file if config is None
            replace (bool, optional):
                replace all config item. Defaults to False.

        Returns:
            bool: result code
        """
        if config is not None and len(config) == 0:
            # Do nothing
            return True

        config_domain = 'IntreIot_config'
        config_name = f'{uid}_{cloud_server}'
        if config is None:
            # Remove config file
            return await self.remove_async(
                domain=config_domain, name=config_name, type_=dict)
        if replace:
            # Replace config file
            return await self.save_async(
                domain=config_domain, name=config_name, data=config)
        local_config = (await self.load_async(
            domain=config_domain, name=config_name, type_=dict)) or {}
        local_config.update(config)
        return await self.save_async(
            domain=config_domain, name=config_name, data=local_config)

    def load_user_config(
        self, uid: str, cloud_server: str, keys: Optional[list[str]] = None
    ) -> dict[str, Any]:
        if keys is not None and len(keys) == 0:
            # Do nothing
            return {}
        config_domain = 'IntreIot_config'
        config_name = f'{uid}_{cloud_server}'
        local_config = (self.load(domain=config_domain,
                        name=config_name, type_=dict)) or {}
        if keys is None:
            return local_config
        return {key: local_config.get(key, None) for key in keys}

    async def load_user_config_async(
        self, uid: str, cloud_server: str, keys: Optional[list[str]] = None
    ) -> dict[str, Any]:
        """Load user configuration.

        Args:
            uid (str): user id
            keys (list[str]):
                query key list, return all config item if keys is None

        Returns:
            dict[str, Any]: query result
        """
        if keys is not None and len(keys) == 0:
            # Do nothing
            return {}
        config_domain = 'IntreIot_config'
        config_name = f'{uid}_{cloud_server}'
        local_config = (await self.load_async(
            domain=config_domain, name=config_name, type_=dict)) or {}
        if keys is None:
            return local_config
        return {
            key: local_config[key] for key in keys
            if key in local_config}

    def gen_storage_path(
        self, domain: str = None, name_with_suffix: str = None
    ) -> str:
        """Generate file path."""
        result = self._root_path
        if domain:
            result = os.path.join(result, domain)
            if name_with_suffix:
                result = os.path.join(result, name_with_suffix)
        return result
