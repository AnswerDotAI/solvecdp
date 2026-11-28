---
title: API Reference
description: Chrome DevTools Protocol relay, duplex WebSocket channels, and macOS AppleScript helpers
module: solvelink.core
---

`solvelink` relays Chrome DevTools Protocol (CDP) frames and macOS AppleScript commands from a remote Solveit kernel through Rustygate's `/api/wsx` WebSocket channel.

## Driving Chrome

`JsCDP` subclasses `fastcdp.ext.ExtCDP` and connects over `/api/wsx?chan=cdp` to the `solveit-chrome` browser extension. Every `fastcdp` helper (`new_page`, `ax_tree`, `fill_text`, `click`, `screenshot`, `cdp_search`) works through the returned client.

```python
cdp = await JsCDP.connect()
page = await cdp.new_page()
await page.goto("https://example.com")
title = await page.eval("document.title")
await page.close()
await cdp.close()
```

{{< doc JsCDP >}}

{{< doc JsCDP.connect >}}

## WebSocket relay channels

`Channel` manages a duplex JSON connection to `{JUPYGATE_URL}/api/wsx?chan={chan}` (`JUPYGATE_URL` defaults to `http://127.0.0.1:8787`). `send(**msg)` broadcasts a JSON object to other peers on the channel, `request(timeout=15, **msg)` attaches a UUID `id` and awaits the matching reply, and unmatched incoming frames are placed on `events`.

```python
ch = await Channel.connect("my-channel")
reply = await ch.request(cmd="ping")
await ch.close()
```

{{< doc Channel >}}

{{< doc Channel.connect >}}

{{< doc Channel.send >}}

{{< doc Channel.request >}}

{{< doc Channel.close >}}

{{< doc Channel.is_open >}}

## macOS AppleScript via solvebridge

`solvelink.mac` executes AppleScript on a Mac connected to `/api/wsx?chan=mac` via `solvebridge`. Each call waits up to `wait_connect` seconds for `solvebridge` to answer a `ping` probe or emit `hello`, returns standard output, and raises `RuntimeError` if the request is denied or `osascript` exits nonzero.

```python
osa('tell application "Finder" to get name of front window')
word("activate\nmake new document")
```

{{< doc solvelink.mac.aosa >}}

{{< doc solvelink.mac.osa >}}

`word`, `xl`, and `ppt` (and their async variants `aword`, `axl`, `appt`) wrap your script in a `tell application "Microsoft ..."` block.

{{< doc solvelink.mac.aword >}}

{{< doc solvelink.mac.word >}}

{{< doc solvelink.mac.axl >}}

{{< doc solvelink.mac.xl >}}

{{< doc solvelink.mac.appt >}}

{{< doc solvelink.mac.ppt >}}

## Helpers

Call `link_yolo()` inside a Solveit kernel to register `JsCDP`, `fastcdp` helpers, and all `solvelink.mac` functions with `pyskills.allow` for `safepyrun`.

{{< doc link_yolo >}}
