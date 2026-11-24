import asyncio

from wattou_sim.__main__ import BatchingPublisher


class SlowClient:
    def __init__(self):
        self.sent = []

    async def publish(self, topic, payload, qos=0, retain=False):
        await asyncio.sleep(0.01)
        self.sent.append((topic, payload, qos, retain))


async def test_batching_publisher_sends_all_concurrently():
    client = SlowClient()
    pub = BatchingPublisher(client, batch=100)
    loop = asyncio.get_running_loop()
    t0 = loop.time()
    for i in range(250):
        await pub.publish(f"t/{i}", "x")
    await pub.flush()
    assert len(client.sent) == 250 and all(q == 1 for _, _, q, _ in client.sent)
    assert loop.time() - t0 < 1.0  # 250 × 10 ms en série = 2,5 s
