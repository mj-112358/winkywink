import os
import json
import logging
import time
from typing import List, Dict
from datetime import datetime
import requests

logger = logging.getLogger(__name__)


class EdgeClient:
    def __init__(self, api_base: str, token: str, org_id: str, store_id: str, camera_id: str):
        self.api_base = api_base.rstrip("/")
        self.token = token
        self.org_id = org_id
        self.store_id = store_id
        self.camera_id = camera_id

        self.offline_queue = []
        self.max_queue_size = 1000

        logger.info(f"EdgeClient initialized for {camera_id}")

    def _headers(self):
        return {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}

    def heartbeat(self):
        try:
            payload = {
                "org_id": self.org_id,
                "store_id": self.store_id,
                "camera_id": self.camera_id
            }
            resp = requests.post(
                f"{self.api_base}/api/ingest/heartbeat",
                json=payload,
                headers=self._headers(),
                timeout=5
            )
            if resp.status_code == 200:
                logger.debug(f"Heartbeat sent for {self.camera_id}")
                return True
            else:
                logger.warning(f"Heartbeat failed: {resp.status_code}")
                return False
        except Exception as e:
            logger.warning(f"Heartbeat exception: {e}")
            return False

    def send_events(self, events: List[Dict]):
        if not events:
            return

        batch = {
            "org_id": self.org_id,
            "store_id": self.store_id,
            "camera_id": self.camera_id,
            "events": events
        }

        try:
            resp = requests.post(
                f"{self.api_base}/api/ingest/events",
                json=batch,
                headers=self._headers(),
                timeout=10
            )
            if resp.status_code == 200:
                logger.info(f"Sent {len(events)} events for {self.camera_id}")
                self.flush_offline_queue()
            else:
                logger.error(f"Event send failed: {resp.status_code}")
                self.queue_offline(events)
        except Exception as e:
            logger.error(f"Event send exception: {e}")
            self.queue_offline(events)

    def queue_offline(self, events: List[Dict]):
        for evt in events:
            if len(self.offline_queue) < self.max_queue_size:
                self.offline_queue.append(evt)
        logger.warning(f"Queued {len(events)} events offline, total: {len(self.offline_queue)}")

    def flush_offline_queue(self):
        if not self.offline_queue:
            return

        to_send = self.offline_queue[:100]
        batch = {
            "org_id": self.org_id,
            "store_id": self.store_id,
            "camera_id": self.camera_id,
            "events": to_send
        }

        try:
            resp = requests.post(
                f"{self.api_base}/api/ingest/events",
                json=batch,
                headers=self._headers(),
                timeout=10
            )
            if resp.status_code == 200:
                logger.info(f"Flushed {len(to_send)} offline events")
                self.offline_queue = self.offline_queue[len(to_send):]
        except Exception as e:
            logger.warning(f"Offline flush failed: {e}")
