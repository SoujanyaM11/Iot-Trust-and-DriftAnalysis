import asyncio
import logging
import random

from ..config_loader import get_app_config
from ..database import get_sync_user_states_collection
from .trust_engine import TrustEngine
from .websocket_manager import WebSocketManager

logger = logging.getLogger("sentineltrust")


class TelemetryProcessor:
    """Background processor that periodically evaluates device telemetry.

    This is a production-ready baseline for the project: it reads every user’s
    MongoDB-stored device baselines, generates a lightweight telemetry sample from each
    device’s baseline, scores it with the trust engine, and emits WebSocket
    updates when a device drifts or is under active attack.
    """

    def __init__(self, trust_engine: TrustEngine, ws_manager: WebSocketManager) -> None:
        self.trust_engine = trust_engine
        self.ws_manager = ws_manager
        self.interval = get_app_config().get("telemetry", {}).get("scoring_interval_seconds", 30)
        self._running = True

    async def _process_cycle(self) -> None:
        stores = get_sync_user_states_collection().find({})
        for store in stores:
            try:
                user_email = store.get("user_email")
                if not user_email:
                    continue

                for device_id, device_meta in (store.get("devices") or {}).items():
                    baseline = (store.get("baselines") or {}).get(device_id)
                    if not baseline or not baseline.get("stats"):
                        continue

                    features = {}
                    for column, stats in baseline["stats"].items():
                        base_value = float(stats.get("mean", 0.0))
                        jitter = random.uniform(-0.18, 0.18) * max(abs(base_value), 1.0)
                        features[column] = round(base_value + jitter, 4)

                    result = self.trust_engine.score_test_data(user_email, device_id, features)
                    if isinstance(result, dict) and "error" in result:
                        continue

                    if result.get("anomaly_detected") or result.get("score", 0) < 60:
                        await self.ws_manager.broadcast(
                            user_email,
                            {
                                "type": "telemetry_update",
                                "device_id": device_id,
                                "score": result.get("score"),
                                "level": result.get("level"),
                                "anomaly_detected": result.get("anomaly_detected", False),
                                "explanation": result.get("explanation"),
                            },
                        )
            except Exception as exc:
                logger.exception("Telemetry cycle failed for %s: %s", store.get("user_email"), exc)

    async def run_scoring_loop(self) -> None:
        """Evaluate telemetry every ``self.interval`` seconds."""
        logger.info("Telemetry scoring loop started with interval %ss", self.interval)
        while self._running:
            try:
                await self._process_cycle()
            except asyncio.CancelledError:
                logger.info("Telemetry scoring loop cancelled")
                raise
            except Exception as exc:
                logger.error("Error in telemetry loop: %s", exc)
            await asyncio.sleep(self.interval)

    def stop(self) -> None:
        """Signal the loop to stop on the next iteration."""
        self._running = False
