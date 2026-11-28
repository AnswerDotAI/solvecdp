# solvelink

`solvelink` is [fastcdp](https://github.com/AnswerDotAI/fastcdp) for Solveit, plus macOS AppleScript helpers for `solvebridge`. A Solveit kernel runs in a remote container and cannot open a local WebSocket directly to your computer, so `solvelink` relays JSON frames through Rustygate's `/api/wsx` WebSocket channel (exposed to external clients at `/rusty/api/wsx`).

## Installation

Install [solveit-chrome](https://github.com/AnswerDotAI/solveit-chrome) to drive Chrome, and `solvebridge` to run AppleScript on your Mac.

Solveit containers ship with `solvelink` pre-installed. To install or upgrade from PyPI:

```bash
pip install solvelink
```

## Driving Chrome (`JsCDP`)

`JsCDP` subclasses `fastcdp.ext.ExtCDP` and connects over Rustygate's `/api/wsx?chan=cdp` channel to the `solveit-chrome` extension. All `fastcdp` features work unchanged: auto-generated CDP domain methods, `cdp_search`, `ax_tree`, form helpers, and console/network/dialog buffers.

```python
from solvelink import *

cdp_search('screenshot')

cdp = await JsCDP.connect()
page = await cdp.new_page()
await page.goto('https://httpbingo.org/forms/post')
await page.eval('document.title')
await page.wait_for('document.title')
img = await page.screenshot()
```

Use `ax_tree` and `find_id` to locate and drive form controls:

```python
root = await page.ax_tree()
nmid = root.find_id('textbox', 'Customer name')
await page.fill_text(nmid, 'Jeremy Howard')
await page.click(root.find_id('radio', 'Large'))
await page.js_node_run('this.value = "18:30"', root.find_id('InputTime', 'delivery time'))
await page.click_and_wait(root.find_id('button', 'Submit order'))

await page.close()
await cdp.close()
```

## Relay channel (`Channel`)

`Channel.connect(chan, url=None, token=None)` connects to `{JUPYGATE_URL}/api/wsx?chan={chan}` (defaulting `JUPYGATE_URL` to `http://127.0.0.1:8787`, with an optional `Authorization: Bearer` `token` for token-gated gateways). `send(**msg)` broadcasts a JSON dict to other peers on the channel, `request(timeout=15, **msg)` adds a UUID `id` and waits for a reply with the same `id`, and unmatched frames arrive in `events`.

```python
ch1, ch2 = await Channel.connect('test'), await Channel.connect('test')
await ch1.send(hello='world')
msg = await ch2.events.get()
await ch1.close()
await ch2.close()
```

## Running AppleScript on your Mac (`solvelink.mac`)

With `solvebridge` connected to your Solveit instance, `osa` (and async `aosa`) runs AppleScript over `/api/wsx?chan=mac` and returns standard output. Before sending a script, `aosa` waits for `solvebridge` to reply to a `ping` probe or announce `hello` on connect, and raises `RuntimeError` if the user denies the request or `osascript` exits nonzero.

```python
osa('tell application "Microsoft Word" to activate')
```

`word`, `xl`, and `ppt` (and async `aword`, `axl`, `appt`) wrap your script in `tell application "Microsoft Word"`, `"Microsoft Excel"`, or `"Microsoft PowerPoint"`:

```python
word('''
activate
set doc to make new document
set tr to text object of doc
set content of tr to "hello from solveit"
set style of tr to style heading1
''')
```

## Allowing LLM access in Solveit

Call `link_yolo()` to register `JsCDP` and all `solvelink.mac` helpers with `pyskills.allow` for Solveit's `safepyrun`:

```python
link_yolo()
```

For browser tasks, a prompt such as the following works well:

> Try using python to connect a `cdp_` JsCDP object and open a `page_` tab with `new_page`, then goto `<url>`, fill it out, read it to check it's filled correctly, then submit it, and see what you get back. Don't use find_id - you can get all the ids at once with ax_tree (don't truncate the result of it). Don't add extra waits etc - solvelink handles it automatically. IDs can change so be sure to use the ax_tree IDs you read.

## Development

```bash
pip install -e '.[dev]'
pytest -q
```
