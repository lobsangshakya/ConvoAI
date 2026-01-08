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
        # Attempt to connect to Kafka with retries
        max_retries = 30
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                self.consumer = KafkaConsumer(
                    'chat-messages',
                    bootstrap_servers=os.getenv('KAFKA_BOOTSTRAP_SERVERS', self.kafka_bootstrap_servers),
                    value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                    auto_offset_reset='earliest',
                    group_id='llm_service_group',
                    consumer_timeout_ms=10000,
                    request_timeout_ms=30000,
                    max_poll_interval_ms=300000  # 5 minutes
                )
                
                self.producer = KafkaProducer(
                    bootstrap_servers=os.getenv('KAFKA_BOOTSTRAP_SERVERS', self.kafka_bootstrap_servers),
                    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                    request_timeout_ms=30000
                )
                
                logger.info('LLM Service successfully connected to Kafka')
                break
            except Exception as e:
                retry_count += 1
                logger.warning(f'Failed to connect to Kafka (attempt {retry_count}/{max_retries}): {str(e)}')
                if retry_count >= max_retries:
                    logger.error('Max retries reached. Attempting to reconnect indefinitely...')
                    # Enter indefinite reconnection loop
                    while True:
                        try:
                            logger.info('Attempting to connect to Kafka...')
                            self.consumer = KafkaConsumer(
                                'chat-messages',
                                bootstrap_servers=os.getenv('KAFKA_BOOTSTRAP_SERVERS', self.kafka_bootstrap_servers),
                                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                                auto_offset_reset='earliest',
                                group_id='llm_service_group',
                                consumer_timeout_ms=10000,
                                request_timeout_ms=30000,
                                max_poll_interval_ms=300000  # 5 minutes
                            )
                            
                            self.producer = KafkaProducer(
                                bootstrap_servers=os.getenv('KAFKA_BOOTSTRAP_SERVERS', self.kafka_bootstrap_servers),
                                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                                request_timeout_ms=30000
                            )
                            
                            logger.info('LLM Service successfully connected to Kafka')
                            break  # Break the reconnection loop
                        except Exception as e:
                            logger.error(f'Failed to connect to Kafka: {str(e)}. Retrying in 30 seconds...')
                            time.sleep(30)  # Wait 30 seconds before retrying
                time.sleep(10)  # Wait 10 seconds before retry
        
        logger.info('LLM Service started listening for messages')
        
        while True:  # Keep the service running indefinitely
            try:
                # Poll for messages with timeout
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
                        
            except Exception as e:
                logger.error(f'Error in Kafka consumer: {str(e)}')
                time.sleep(5)  # Wait a bit before retrying to consume messages


if __name__ == '__main__':
    service = LLMService()
    service.start_listening()