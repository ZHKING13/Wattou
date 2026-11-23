import asyncio
import contextlib
import logging

import aiomqtt
from fastapi import FastAPI

from ..config import get_settings
from ..control import MqttPublisher
from . import routes_alerts, routes_auth, routes_devices, routes_foyer

log = logging.getLogger("wattou.api")


async def _mqtt_loop(app: FastAPI) -> None:
    st = get_settings()
    while True:
        try:
            async with aiomqtt.Client(st.mqtt_host, st.mqtt_port, username=st.mqtt_user,
                                      password=st.mqtt_password) as client:
                app.state.publisher = MqttPublisher(client)
                await asyncio.Future()  # garde la connexion ouverte
        except aiomqtt.MqttError as e:
            app.state.publisher = None
            log.warning("MQTT indisponible (%s), nouvel essai dans 5 s", e)
            await asyncio.sleep(5)


def create_app(with_mqtt: bool = True) -> FastAPI:
    @contextlib.asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.publisher = None
        task = asyncio.create_task(_mqtt_loop(app)) if with_mqtt else None
        yield
        if task:
            task.cancel()

    app = FastAPI(title="Wattou", lifespan=lifespan)
    for r in (routes_auth, routes_foyer, routes_devices, routes_alerts):
        app.include_router(r.router, prefix="/api/v1")

    @app.get("/health")
    async def health():
        return {"ok": True}

    return app
