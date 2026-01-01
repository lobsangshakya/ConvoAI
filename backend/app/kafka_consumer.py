from kafka import KafkaConsumer
import json
import logging
from typing import Dict, Any, Callable
import threading

logger = logging.getLogger(__name__)


class KafkaConsumerService:
    def __init__(self, bootstrap_servers: str = 'kafka:9092', group_id: str = 'chatbot_group'):
        self.consumer = KafkaConsumer(
            bootstrap_servers=bootstrap_servers,
            group_id=group_id,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='earliest',
            api_version=(0, 10, 1)
        )
        self.running = False
        self.thread = None

    def start_consuming(self, topics: list, message_handler: Callable[[Dict[str, Any]], None]):
        self.consumer.subscribe(topics=topics)
        self.running = True
        
        def consume_loop():
            logger.info(f'Starting to consume messages from topics: {topics}')
            for message in self.consumer:
                if not self.running:
                    break
                try:
                    logger.info(f'Received message from topic {message.topic}: {message.value}')
                    message_handler(message.value)
                except Exception as e:
                    logger.error(f'Error processing message: {str(e)}')
        
        self.thread = threading.Thread(target=consume_loop)
        self.thread.start()

    def stop_consuming(self):
        self.running = False
        if self.thread:
            self.thread.join()
        self.consumer.close()