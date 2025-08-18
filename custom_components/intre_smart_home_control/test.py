import asyncio
import websockets
import json
import socket
import requests
import qrcode
from intreiot.intreIot_cloud import IntreIotHttpClient

async def gettoken():
    client = IntreIotHttpClient()
    await client.getToken(devicesn='12345678912345678',version=10,lanip="10.136.6.19")


async def gettQRcode():
    client = IntreIotHttpClient()
    await client.getToken(devicesn='12345678912345678',version=10,lanip="10.136.6.19")
    await client.getQRcode()

async def gett_home_info():
    '''
    client = IntreIotHttpClient()
    deviceId=await client.getToken(devicesn='12345678912345678',version=10,lanip="10.136.6.19")
    await client.get_home_info(deviceId)
    '''
    client = IntreIotHttpClient()
    rsp=await client.getToken(devicesn='12345678912345678',version=1,lanip="10.136.6.19")
    DeviceId =rsp.get('deviceId',None)
    await client.get_home_info(deviceId = DeviceId)

asyncio.get_event_loop().run_until_complete(gett_home_info())