"Run macOS AppleScript from a solveit kernel through solvebridge"

__all__ = ['aosa', 'osa', 'aword', 'word', 'axl', 'xl', 'appt', 'ppt']

import asyncio,concurrent.futures
from contextlib import suppress
from fastcore.meta import delegates
from solvelink.core import Channel

async def _wait_hello(ch):
    while True:
        if (await ch.events.get()).get('event') == 'hello': return

async def _wait_bridge(ch, wait_connect=25, ping_interval=1.5):
    "Wait until a solvebridge peer answers `ping` or announces `hello` on `ch`"
    loop = asyncio.get_running_loop()
    deadline = loop.time() + wait_connect
    hello = asyncio.create_task(_wait_hello(ch))
    try:
        while (rem := deadline - loop.time()) > 0:
            ping = asyncio.create_task(ch.request(timeout=min(ping_interval, rem), cmd='ping'))
            done, _ = await asyncio.wait((hello, ping), return_when=asyncio.FIRST_COMPLETED)
            if hello in done:
                ping.cancel()
                with suppress(asyncio.CancelledError, TimeoutError): await ping
                return
            try:
                if (await ping).get('ok'): return
                await asyncio.sleep(min(ping_interval, max(0, deadline - loop.time())))
            except TimeoutError: pass
        raise TimeoutError(f"solvebridge is not connected on {ch.url}")
    finally:
        if not hello.done():
            hello.cancel()
            with suppress(asyncio.CancelledError): await hello

async def aosa(
    script:str, # AppleScript source to run on the connected Mac
    chan:str='mac', # Relay channel name `solvebridge` connects to
    url:str=None, # Full relay URL (defaults to `/api/wsx` on `JUPYGATE_URL`)
    token:str=None, # Optional bearer token for token-gated gateways
    timeout:float=60, # Seconds to wait for approval and execution
    wait_connect:float=25, # Seconds to wait for `solvebridge` to answer `ping` or `hello`
    ping_interval:float=1.5, # Seconds between `ping` probes while waiting for `solvebridge`
) -> str:
    "Run AppleScript `script` on the user's Mac through `solvebridge` and return stdout"
    ch = await Channel.connect(chan, url=url, token=token)
    try:
        await _wait_bridge(ch, wait_connect=wait_connect, ping_interval=ping_interval)
        res = await ch.request(timeout=timeout, cmd='osascript', script=script)
    finally: await ch.close()
    if (err := res.get('error')): raise RuntimeError(f"osascript: {err}")
    if (rc := res.get('returncode', 0)):
        msg = (res.get('stderr') or res.get('stdout') or '').strip()
        raise RuntimeError(f"osascript exited with status {rc}" + (f": {msg}" if msg else ''))
    return res.get('stdout', '')

def _run_sync(coro):
    try: asyncio.get_running_loop()
    except RuntimeError: return asyncio.run(coro)
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex: return ex.submit(asyncio.run, coro).result()

@delegates(aosa)
def osa(
    script:str, # AppleScript source to run on the connected Mac
    **kwargs
) -> str:
    "Run AppleScript `script` synchronously on the user's Mac through `solvebridge` and return stdout"
    return _run_sync(aosa(script, **kwargs))

def _tell(app, scr): return f'tell application "{app}"\n{scr}\nend tell'

@delegates(aosa)
async def aword(scr:str, **kwargs) -> str:
    "Run AppleScript `scr` in Microsoft Word through `solvebridge`"
    return await aosa(_tell("Microsoft Word", scr), **kwargs)

@delegates(osa)
def word(scr:str, **kwargs) -> str:
    "Run AppleScript `scr` synchronously in Microsoft Word through `solvebridge`"
    return osa(_tell("Microsoft Word", scr), **kwargs)

@delegates(aosa)
async def axl(scr:str, **kwargs) -> str:
    "Run AppleScript `scr` in Microsoft Excel through `solvebridge`"
    return await aosa(_tell("Microsoft Excel", scr), **kwargs)

@delegates(osa)
def xl(scr:str, **kwargs) -> str:
    "Run AppleScript `scr` synchronously in Microsoft Excel through `solvebridge`"
    return osa(_tell("Microsoft Excel", scr), **kwargs)

@delegates(aosa)
async def appt(scr:str, **kwargs) -> str:
    "Run AppleScript `scr` in Microsoft PowerPoint through `solvebridge`"
    return await aosa(_tell("Microsoft PowerPoint", scr), **kwargs)

@delegates(osa)
def ppt(scr:str, **kwargs) -> str:
    "Run AppleScript `scr` synchronously in Microsoft PowerPoint through `solvebridge`"
    return osa(_tell("Microsoft PowerPoint", scr), **kwargs)
