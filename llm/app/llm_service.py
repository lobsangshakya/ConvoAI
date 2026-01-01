import json
import logging
import os
from kafka import KafkaConsumer, KafkaProducer
from typing import Dict, Any
import time
from .model_handler import ModelHandler

logger = logging.getLogger(__name__)


class LLMService:
    def __init__(self, kafka_bootstrap_servers: str = 'kafka:9092'):
        self.kafka_bootstrap_servers = kafka_bootstrap_servers
        self.consumer = None
        self.producer = None
        self.model_handler = ModelHandler()
        
    def start_listening(self):
        """Start listening for messages from Kafka"""
        self.consumer = KafkaConsumer(
            'chat-messages',
            bootstrap_servers=self.kafka_bootstrap_servers,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='earliest',
            group_id='llm_service_group'
        )
        
        self.producer = KafkaProducer(
            bootstrap_servers=self.kafka_bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        
        logger.info('LLM Service started listening for messages')
        
        for message in self.consumer:
            try:
                data = message.value
                logger.info(f'LLM Service received message: {data}')
                
                # Generate response using the LLM
                response = self.model_handler.generate_response(data.get('message', ''))
                
                # Prepare response data
                response_data = {
                    'user_id': data.get('user_id', 'unknown'),
                    'session_id': data.get('session_id', 'unknown'),
                    'original_message': data.get('message'),
                    'llm_response': response,
                    'timestamp': time.time(),
                    'source': 'llm'
                }
                
                # Send response to the appropriate topic
                self.producer.send('llm-responses', value=response_data)
                logger.info(f'LLM Service sent response: {response[:50]}...')
                
            except Exception as e:
                logger.error(f'Error in LLM service processing: {str(e)}')


if __name__ == '__main__':
    service = LLMService()
    service.start_listening()