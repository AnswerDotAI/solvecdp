"Drive the user's Chrome and Mac from a Solveit kernel"

__all__ = ['Channel', 'JsCDP', 'link_yolo']

from fastcore.utils import *
import asyncio,json,uuid,websockets
from fastcdp.ext import *
import fastcdp.ext

class Channel:
    "Duplex JSON messaging with the other peers on a named `/api/wsx` relay channel"
    def __init__(self, chan, url=None):
        base = os.environ.get('JUPYGATE_URL', 'http://127.0.0.1:8787').rstrip('/')
        self.url = url or f"{re.sub('^http', 'ws', base)}/api/wsx?chan={chan}"
        self._replies,self.events = {},asyncio.Queue()

    @classmethod
    async def connect(cls,
        chan, # Channel name; peers connecting to the same name hear each other
        url=None, # Full relay url (defaults to `/api/wsx` on `JUPYGATE_URL`)
        token=None # Optional bearer token for token-gated gateways
    ):
        "Connect to `chan` and start reading frames"
        self = cls(chan, url=url)
        headers = {'Authorization': f'Bearer {token}'} if token else None
        self._ws = await websockets.connect(self.url, additional_headers=headers)
        self._reader = asyncio.create_task(self._read_loop())
        return self

    async def _read_loop(self):
        async for frame in self._ws:
            msg = dict2obj(json.loads(frame))
            if (f := self._replies.pop(msg.get('id'), None)):
                if not f.done(): f.set_result(msg)
            else: await self.events.put(msg)

    async def send(self, **msg): await self._ws.send(json.dumps(msg))

    async def request(self, timeout=15, **msg):
        "Send `msg` with a unique `id` and wait for a reply with that `id`"
        mid = msg['id'] = str(uuid.uuid4())
        f = asyncio.get_running_loop().create_future()
        self._replies[mid] = f
        try:
            await self._ws.send(json.dumps(msg))
            return await asyncio.wait_for(f, timeout)
        finally: self._replies.pop(mid, None)

    async def close(self):
        self._reader.cancel()
        await self._ws.close()

    @property
    def is_open(self): return self._ws.state.name == 'OPEN'

class JsCDP(ExtCDP):
    "CDP over the solveit-chrome extension: frames relayed via rustygate's `/api/wsx` channel"
    @classmethod
    async def connect(cls,
        chan='cdp', # Relay channel name the extension serves
        debug=None # Print events as they arrive?
    ):
        "Connect to channel"
        return await super().connect(await Channel.connect(chan), debug=debug)

def link_yolo():
    "Allow all CDP classes and macOS bridge helpers in safepyrun"
    from pyskills import allow
    import solvelink.mac as _mac
    fastcdp.ext.cdp_yolo()
    allow({JsCDP:...}, *(_mac.__dict__[n] for n in _mac.__all__))
