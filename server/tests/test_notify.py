import json

import httpx

from wattou.notify import ExpoNotifier


async def test_expo_payload():
    seen = {}

    def handler(request: httpx.Request):
        seen["url"] = str(request.url)
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"data": []})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    await ExpoNotifier(client).send(["ExponentPushToken[a]", "ExponentPushToken[b]"], "Wattou", "Crédit bas")
    assert seen["url"] == "https://exp.host/--/api/v2/push/send"
    assert seen["body"] == [
        {"to": "ExponentPushToken[a]", "title": "Wattou", "body": "Crédit bas", "sound": "default",
         "channelId": "alertes", "priority": "high"},
        {"to": "ExponentPushToken[b]", "title": "Wattou", "body": "Crédit bas", "sound": "default",
         "channelId": "alertes", "priority": "high"},
    ]


async def test_expo_no_tokens_no_call():
    client = httpx.AsyncClient(transport=httpx.MockTransport(lambda r: 1 / 0))
    await ExpoNotifier(client).send([], "t", "b")
