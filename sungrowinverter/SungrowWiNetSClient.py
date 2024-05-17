import json
import time
from typing import Optional, Dict, Tuple

import aiohttp
import websockets
from aiohttp import ClientSession
from websockets import WebSocketClientProtocol

class ModbusResponse:
    def __init__(self, data: Dict):
        self._data = data

        # define registers only if avail, caller checks with hasattr
        if not self.isError():
            b_strs = tuple(data['result_data']['param_value'].strip().split(' '))
            self.registers: Tuple[int, ...] = tuple(int("".join(t), 16) for t in zip(b_strs[::2], b_strs[1::2]))

    def isError(self):
        """ modbus like """
        return not self._data['result_code']

class SungrowWinNetSClient:
    def __init__(self, ip, ws_port):
        self.inverter_ip = ip
        self.ws_port = ws_port

        self.ws_session: Optional[WebSocketClientProtocol] = None
        self.http_session: Optional[ClientSession] = None

        # startup results
        self.token = None
        self.dev_id = None
        self.dev_type = None
        self.dev_code = None

    async def read_input_registers(self, start, count, slave) -> ModbusResponse:
        if self.ws_session is None:
            await self._startup()

        data = await self._http_req(start +1, count, 0)
        resp = ModbusResponse(data)
        return resp

    async def read_holding_registers(self, start, count, slave):
        if self.ws_session is None:
            await self._startup()

        data = await self._http_req(start +1, count, 1)
        resp = ModbusResponse(data)
        return resp

    def connect(self):
        """ dummy modbus connection """
        return self

    def close(self):
        """ dummy modbus close """
        return

    async def _http_req(self, address, count, param_type):
        http_req = (f'http://{self.inverter_ip}/device/getParam?'
                    f'dev_id={self.dev_id}&dev_type={str(self.dev_type)}&dev_code={str(self.dev_code)}&type=3&'
                    f'param_addr={address}&param_num={count}&param_type={str(param_type)}&'
                    f'token={self.token}&lang=en_us&time123456={str(int(time.time()))}')

        response = await self.http_session.get(http_req)
        async with response:
            assert response.status == 200, response
            data = json.loads(await response.text())

        return data

    async def _startup(self):
        ws_uri = f'ws://{self.inverter_ip}:{self.ws_port}/ws/home/overview'
        self.ws_session = await websockets.connect(ws_uri)

        connect_resp = await self._ws_req(self.ws_session, "", "connect")
        self.token = connect_resp['token']

        device_resp = await self._ws_req(self.ws_session, self.token, 'devicelist', type='0', is_check_token='0')
        device = device_resp['list'][0]
        self.dev_id, self.dev_type, self.dev_code = (device[k] for k in ('dev_id', 'dev_type', 'dev_code'))

        print(device_resp)

        self.http_session = aiohttp.ClientSession()

    @staticmethod
    async def _ws_req(ws: WebSocketClientProtocol, token: str, service: str, **kwargs):
        await ws.send(json.dumps(dict(lang='en_us', token=token, service=service, **kwargs)))
        resp = json.loads(await ws.recv())
        assert resp['result_code'] == 1
        return resp['result_data']


    async def close_winets(self):
        if self.http_session:
            await self.http_session.close()
            self.http_session = None

        if self.ws_session:
            await self.ws_session.close()
            self.ws_session = None