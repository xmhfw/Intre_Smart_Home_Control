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

IntreIoT error code and exception.
"""
from enum import Enum
from typing import Any


class IntreIoTErrorCode(Enum):
    """IntreIoT error code."""
    # Base error code
    CODE_UNKNOWN = -10000
    CODE_UNAVAILABLE = -10001
    CODE_INVALID_PARAMS = -10002
    CODE_RESOURCE_ERROR = -10003
    CODE_INTERNAL_ERROR = -10004
    CODE_UNAUTHORIZED_ACCESS = -10005
    CODE_TIMEOUT = -10006
    # OAuth error code
    CODE_OAUTH_UNAUTHORIZED = -10020
    # Http error code
    CODE_HTTP_INVALID_ACCESS_TOKEN = -10030
    # IntreIoT intreps error code
    CODE_INTREPS_INVALID_RESULT = -10040
    # IntreIoT cert error code
    CODE_CERT_INVALID_CERT = -10050
    # IntreIoT spec error code, -10060
    # IntreIoT storage error code, -10070
    # IntreIoT ev error code, -10080
    # Intreps service error code, -10090
    # Config flow error code, -10100
    # Options flow error code , -10110
    # IntreIoT lan error code, -10120
    CODE_LAN_UNAVAILABLE = -10120


class IntreIoTError(Exception):
    """IntreIoT error."""
    code: IntreIoTErrorCode
    message: Any

    def __init__(
        self,  message: Any, code: IntreIoTErrorCode = IntreIoTErrorCode.CODE_UNKNOWN
    ) -> None:
        self.message = message
        self.code = code
        super().__init__(self.message)

    def to_str(self) -> str:
        return f'{{"code":{self.code.value},"message":"{self.message}"}}'

    def to_dict(self) -> dict:
        return {"code": self.code.value, "message": self.message}


class IntreIoTOauthError(IntreIoTError):
    ...


class IntreIoTHttpError(IntreIoTError):
    ...


class IntreIoTIntrepsError(IntreIoTError):
    ...


class IntreIoTDeviceError(IntreIoTError):
    ...


class IntreIoTSpecError(IntreIoTError):
    ...


class IntreIoTStorageError(IntreIoTError):
    ...


class IntreIoTCertError(IntreIoTError):
    ...


class IntreIoTClientError(IntreIoTError):
    ...


class IntreIoTEvError(IntreIoTError):
    ...


class IntrepsServiceError(IntreIoTError):
    ...


class IntreIoTConfigError(IntreIoTError):
    ...


class IntreIoTOptionsError(IntreIoTError):
    ...


class IntreIoTLanError(IntreIoTError):
    ...
