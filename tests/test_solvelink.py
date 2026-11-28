import asyncio, threading
from collections import defaultdict
from urllib.parse import parse_qs, urlparse
import pytest, websockets
from solvelink import Channel, aosa, osa


@pytest.fixture
def relay():
    "Background-thread `/api/wsx?chan=...` broadcast relay matching Rustygate's wire contract"
    chans, auth_seen, ready, stop_ev = defaultdict(set), [], threading.Event(), None
    port_box, loop_box = [], []

    async def _run():
        nonlocal stop_ev
        stop_ev = asyncio.Event()
        loop_box.append(asyncio.get_running_loop())
        async def handler(ws):
            auth_seen.append(ws.request.headers.get('Authorization'))
            chan = (parse_qs(urlparse(ws.request.path).query).get('chan') or [''])[0]
            if not chan: return await ws.close(4000, 'chan required')
            peers = chans[chan]
            peers.add(ws)
            try:
                async for frame in ws:
                    for p in list(peers - {ws}):
                        try: await p.send(frame)
                        except Exception: pass
            finally:
                peers.discard(ws)
                if not peers: chans.pop(chan, None)

        async with websockets.serve(handler, '127.0.0.1', 0) as srv:
            port_box.append(srv.sockets[0].getsockname()[1])
            ready.set()
            await stop_ev.wait()

    t = threading.Thread(target=asyncio.run, args=(_run(),), daemon=True)
    t.start()
    assert ready.wait(5)
    try: yield (lambda chan: f'ws://127.0.0.1:{port_box[0]}/api/wsx?chan={chan}'), auth_seen
    finally:
        loop_box[0].call_soon_threadsafe(stop_ev.set)
        t.join(5)


async def test_channel_relay_and_token(relay):
    ws_url, auth_seen = relay
    ch1 = await Channel.connect('demo', url=ws_url('demo'), token='secret')
    ch2 = await Channel.connect('demo', url=ws_url('demo'))
    try:
        assert ch1.is_open and auth_seen[:2] == ['Bearer secret', None]
        await ch1.send(hello='world')
        assert (await ch2.events.get()).hello == 'world'

        async def responder():
            msg = await ch2.events.get()
            await ch2.send(id=msg.id, result=msg.x * 2)
        t = asyncio.create_task(responder())
        assert (await ch1.request(x=21)).result == 42
        await t
    finally:
        await ch1.close()
        await ch2.close()
    assert not ch1.is_open


async def _fake_bridge(url, delay=0, limit=1):
    if delay: await asyncio.sleep(delay)
    ch = await Channel.connect('mac', url=url)
    try:
        await ch.send(event='hello', platform='macos', app='solvebridge')
        seen = 0
        while seen < limit:
            msg = await ch.events.get()
            if msg.get('cmd') == 'ping': await ch.send(id=msg.id, ok=True, platform='macos')
            elif msg.get('cmd') == 'osascript':
                seen += 1
                s = msg.script
                if s == 'deny': await ch.send(id=msg.id, error='denied by user')
                elif s == 'fail': await ch.send(id=msg.id, stdout='', stderr='syntax error', returncode=1)
                else: await ch.send(id=msg.id, stdout=f'ran: {s}\n', stderr='', returncode=0)
    finally: await ch.close()


async def test_mac_handshake_errors_and_sync(relay):
    ws_url, _ = relay
    u = ws_url('mac-test')
    bridge = asyncio.create_task(_fake_bridge(u, delay=0.06, limit=3))
    assert await aosa('activate', url=u, ping_interval=0.05) == 'ran: activate\n'
    with pytest.raises(RuntimeError, match='denied by user'): await aosa('deny', url=u, ping_interval=0.05)
    with pytest.raises(RuntimeError, match='syntax error'): await aosa('fail', url=u, ping_interval=0.05)
    await bridge

    with pytest.raises(TimeoutError, match='not connected'):
        await aosa('noop', url=ws_url('mac-empty'), wait_connect=0.12, ping_interval=0.04)

    us = ws_url('mac-sync')
    t = threading.Thread(target=asyncio.run, args=(_fake_bridge(us, delay=0.04, limit=1),))
    t.start()
    try: assert osa('tell Word', url=us, ping_interval=0.04) == 'ran: tell Word\n'
    finally:
        t.join(2)
        assert not t.is_alive()
