from kafka import KafkaProducer
import json
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class KafkaProducerService:
    def __init__(self, bootstrap_servers: str = 'kafka:9092'):
        self.producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            security_protocol='PLAINTEXT',
            api_version_auto=True,
            retries=3
        )

    def send_message(self, topic: str, message: Dict[str, Any]):
        try:
            future = self.producer.send(topic, value=message)
            result = future.get(timeout=10)
            logger.info(f'Message sent to topic {topic}, partition {result.partition}, offset {result.offset}')
            return result
        except Exception as e:
            logger.error(f'Error sending message to topic {topic}: {str(e)}')
            raise

    def close(self):
        self.producer.close()


# Global producer instance
kafka_producer = None


def get_kafka_producer():
    global kafka_producer
    if kafka_producer is None:
        kafka_producer = KafkaProducerService()
    return kafka_producer