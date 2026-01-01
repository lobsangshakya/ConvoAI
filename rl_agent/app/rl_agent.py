import json
import logging
from kafka import KafkaConsumer, KafkaProducer
import numpy as np
import tensorflow as tf
from tensorflow import keras
from typing import Dict, Any
import threading
import time
from .reward_calculator import RewardCalculator

logger = logging.getLogger(__name__)


class RLAgent:
    def __init__(self, kafka_bootstrap_servers: str = 'kafka:9092'):
        self.kafka_bootstrap_servers = kafka_bootstrap_servers
        self.consumer = None
        self.producer = None
        self.reward_calculator = RewardCalculator()
        self.model = self._build_model()
        
    def _build_model(self):
        """Simple neural network for processing chat interactions"""
        model = keras.Sequential([
            keras.layers.Dense(64, activation='relu', input_shape=(10,)),  # Input: various features
            keras.layers.Dense(32, activation='relu'),
            keras.layers.Dense(16, activation='relu'),
            keras.layers.Dense(1, activation='sigmoid')  # Output: quality score
        ])
        model.compile(optimizer='adam', loss='mse', metrics=['mae'])
        return model
    
    def start_listening(self):
        """Start listening for messages from Kafka"""
        self.consumer = KafkaConsumer(
            'chat-messages',
            bootstrap_servers=self.kafka_bootstrap_servers,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='earliest',
            group_id='rl_agent_group'
        )
        
        self.producer = KafkaProducer(
            bootstrap_servers=self.kafka_bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        
        logger.info('RL Agent started listening for messages')
        
        for message in self.consumer:
            try:
                data = message.value
                logger.info(f'RL Agent received message: {data}')
                
                # Calculate reward based on the message
                reward = self.reward_calculator.calculate_reward(data)
                
                # Prepare response suggestion
                response_suggestion = self.generate_response_suggestion(data, reward)
                
                # Send reward and response suggestion to the response topic
                response_data = {
                    'user_id': data.get('user_id', 'unknown'),
                    'session_id': data.get('session_id', 'unknown'),
                    'original_message': data.get('message'),
                    'reward': reward,
                    'suggested_response': response_suggestion,
                    'timestamp': time.time()
                }
                
                self.producer.send('rl-responses', value=response_data)
                logger.info(f'RL Agent sent response with reward: {reward}')
                
            except Exception as e:
                logger.error(f'Error in RL agent processing: {str(e)}')
    
    def generate_response_suggestion(self, message_data: Dict[str, Any], reward: float):
        """Generate a response suggestion based on the message and reward"""
        # In a real implementation, this would use the model to generate a more sophisticated response
        message_text = message_data.get('message', '').lower()
        
        if 'hello' in message_text or 'hi' in message_text:
            return "Hello there! How can I assist you today?"
        elif 'thank' in message_text:
            return "You're welcome! Is there anything else I can help with?"
        elif 'help' in message_text:
            return "I'd be happy to help. What do you need assistance with?"
        else:
            if reward > 0.7:
                return "That's interesting. Tell me more about that."
            else:
                return "I'm not sure I understand. Could you rephrase that?"


if __name__ == '__main__':
    agent = RLAgent()
    agent.start_listening()