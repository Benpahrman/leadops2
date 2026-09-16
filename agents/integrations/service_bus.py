"""Azure Service Bus and local queue broker for asynchronous agent swarm coordination."""

import json
import logging
import os
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from queue import Empty, Queue
from typing import Any, Callable, Dict, Generator, List, Optional

logger = logging.getLogger("leadops.service_bus")

try:
    from azure.servicebus import ServiceBusClient, ServiceBusMessage
    HAS_AZURE_SERVICEBUS = True
except ImportError:
    HAS_AZURE_SERVICEBUS = False


class JobType(str, Enum):
    SCOUT_EVALUATION = "SCOUT_EVALUATION"
    BUILD_PLAN_EXECUTION = "BUILD_PLAN_EXECUTION"
    CODE_GENERATION = "CODE_GENERATION"
    SELECTOR_REPAIR = "SELECTOR_REPAIR"
    DRIFT_CHECK = "DRIFT_CHECK"
    LIFECYCLE_EMAIL = "LIFECYCLE_EMAIL"


@dataclass
class JobPayload:
    job_type: JobType
    lead_id: str = ""
    slug: str = ""
    params: Dict[str, Any] = field(default_factory=dict)
    job_id: str = field(default_factory=lambda: f"job_{uuid.uuid4().hex[:12]}")
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_json(self) -> str:
        data = asdict(self)
        data["job_type"] = self.job_type.value if hasattr(self.job_type, "value") else str(self.job_type)
        return json.dumps(data)

    @classmethod
    def from_json(cls, raw: str) -> "JobPayload":
        data = json.loads(raw)
        data["job_type"] = JobType(data["job_type"])
        return cls(**data)


class LocalQueueBroker:
    """In-memory thread-safe queue broker for local development and test execution."""

    def __init__(self) -> None:
        self._queues: Dict[str, Queue] = {}

    def _get_queue(self, queue_name: str) -> Queue:
        if queue_name not in self._queues:
            self._queues[queue_name] = Queue()
        return self._queues[queue_name]

    def publish_job(self, queue_name: str, payload: JobPayload) -> str:
        q = self._get_queue(queue_name)
        q.put(payload)
        logger.debug("LocalQueueBroker: Enqueued %s to %s", payload.job_id, queue_name)
        return payload.job_id

    def receive_jobs(self, queue_name: str, max_messages: int = 5, timeout_seconds: float = 1.0) -> List[JobPayload]:
        q = self._get_queue(queue_name)
        messages = []
        for _ in range(max_messages):
            try:
                msg = q.get(timeout=timeout_seconds if not messages else 0.1)
                messages.append(msg)
            except Empty:
                break
        return messages


class AzureServiceBusBroker:
    """Production Azure Service Bus broker with message sessions, dead-lettering, and KEDA scaling."""

    def __init__(self, connection_string: str) -> None:
        self.connection_string = connection_string
        self.client = ServiceBusClient.from_connection_string(connection_string)

    def publish_job(self, queue_name: str, payload: JobPayload) -> str:
        sender = self.client.get_queue_sender(queue_name=queue_name)
        with sender:
            message_body = payload.to_json()
            message = ServiceBusMessage(
                message_body,
                message_id=payload.job_id,
                content_type="application/json",
            )
            sender.send_messages(message)
            logger.info("ServiceBus: Published %s [%s] to %s", payload.job_id, payload.job_type.value, queue_name)
        return payload.job_id

    def receive_jobs(
        self,
        queue_name: str,
        max_messages: int = 5,
        timeout_seconds: float = 5.0,
        complete_immediately: bool = True,
    ) -> List[JobPayload]:
        receiver = self.client.get_queue_receiver(queue_name=queue_name, max_wait_time=timeout_seconds)
        results = []
        with receiver:
            received_msgs = receiver.receive_messages(max_message_count=max_messages, max_wait_time=timeout_seconds)
            for raw_msg in received_msgs:
                try:
                    body = str(raw_msg)
                    job = JobPayload.from_json(body)
                    results.append(job)
                    if complete_immediately:
                        receiver.complete_message(raw_msg)
                except Exception as e:
                    logger.error("Failed to parse Service Bus message: %s. Abandoning or dead-lettering.", e)
                    receiver.dead_letter_message(raw_msg, reason="DeserializationError", error_description=str(e))
        return results

    def close(self) -> None:
        self.client.close()


def create_queue_broker() -> Any:
    """Factory creating Azure Service Bus broker if connection string is configured, else local broker."""
    sb_conn = os.environ.get("AZURE_SERVICE_BUS_CONNECTION_STRING")
    if sb_conn and HAS_AZURE_SERVICEBUS:
        try:
            logger.info("Connecting to Azure Service Bus...")
            return AzureServiceBusBroker(connection_string=sb_conn)
        except Exception as e:
            logger.warning("Azure Service Bus connection failed (%s), falling back to LocalQueueBroker", e)
    return LocalQueueBroker()


# Default singleton broker
queue_broker = create_queue_broker()
