import logging
import json
import threading
from typing import Dict, Any, Callable, Optional
from kafka import KafkaConsumer
from datetime import datetime
import time
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class KafkaDataProcessor:
    def __init__(self, bootstrap_servers: str = "localhost:9092", group_id: str = "chatbot_group"):
        """
        Initialize Kafka consumer for real-time data processing.
        Connects to Kafka cluster and sets up data processing pipeline.
        """
        self.bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", bootstrap_servers)
        self.group_id = os.getenv("KAFKA_GROUP_ID", group_id)
        self.consumer = None
        self.running = False
        self.data_cache = {}  # Cache for real-time data
        self.cache_ttl = 300  # Cache TTL in seconds (5 minutes)
        
        # Topics to subscribe to
        self.topics = os.getenv("KAFKA_TOPICS", "chat_updates,realtime_data").split(",")
        
        try:
            logger.info(f"Connecting to Kafka at {self.bootstrap_servers}")
            self.consumer = KafkaConsumer(
                *self.topics,
                bootstrap_servers=[self.bootstrap_servers],
                auto_offset_reset='latest',
                enable_auto_commit=True,
                group_id=self.group_id,
                value_deserializer=lambda x: json.loads(x.decode('utf-8')) if x else None,
                key_deserializer=lambda x: x.decode('utf-8') if x else None
            )
            logger.info(f"Kafka consumer initialized for topics: {self.topics}")
        except Exception as e:
            logger.error(f"Failed to initialize Kafka consumer: {e}")
            raise
    
    def start_consumer(self):
        """Start consuming messages from Kafka"""
        if self.consumer:
            self.running = True
            consumer_thread = threading.Thread(target=self._consume_messages, daemon=True)
            consumer_thread.start()
            logger.info("Kafka consumer started")
    
    def stop_consumer(self):
        """Stop consuming messages from Kafka"""
        self.running = False
        if self.consumer:
            self.consumer.close()
        logger.info("Kafka consumer stopped")
    
    def _consume_messages(self):
        """Internal method to consume messages from Kafka"""
        try:
            for message in self.consumer:
                if not self.running:
                    break
                
                try:
                    key = message.key
                    value = message.value
                    topic = message.topic
                    timestamp = datetime.fromtimestamp(message.timestamp / 1000.0)
                    
                    logger.debug(f"Received message from topic '{topic}': key={key}, value={value}")
                    
                    # Process the message based on topic
                    self._process_message(topic, key, value, timestamp)
                    
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    
        except Exception as e:
            logger.error(f"Error in Kafka consumer loop: {e}")
    
    def _process_message(self, topic: str, key: str, value: Dict[str, Any], timestamp: datetime):
        """Process incoming message from Kafka"""
        try:
            # Update cache with new data
            cache_key = f"{topic}:{key}" if key else topic
            
            # Add metadata to the cached value
            cached_value = {
                "data": value,
                "timestamp": timestamp.isoformat(),
                "received_at": datetime.utcnow().isoformat()
            }
            
            self.data_cache[cache_key] = cached_value
            logger.info(f"Updated cache with key '{cache_key}'")
            
            # Optionally trigger callbacks for specific topics
            self._trigger_callbacks(topic, key, value)
            
        except Exception as e:
            logger.error(f"Error processing message from topic {topic}: {e}")
    
    def _trigger_callbacks(self, topic: str, key: str, value: Dict[str, Any]):
        """Trigger callbacks for specific topics"""
        # This can be extended to trigger specific actions based on topic
        pass
    
    def get_realtime_data(self, topic: str, key: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get real-time data from cache"""
        cache_key = f"{topic}:{key}" if key else topic
        
        cached_item = self.data_cache.get(cache_key)
        if cached_item:
            # Check if cache is expired
            received_at = datetime.fromisoformat(cached_item["received_at"])
            if (datetime.utcnow() - received_at).seconds <= self.cache_ttl:
                return cached_item
            else:
                # Remove expired cache entry
                del self.data_cache[cache_key]
                logger.info(f"Removed expired cache entry: {cache_key}")
        
        return None
    
    def get_all_topic_data(self, topic: str) -> Dict[str, Any]:
        """Get all data for a specific topic"""
        topic_data = {}
        for cache_key, cached_value in self.data_cache.items():
            if cache_key.startswith(f"{topic}:") or cache_key == topic:
                # Check if cache is expired
                received_at = datetime.fromisoformat(cached_value["received_at"])
                if (datetime.utcnow() - received_at).seconds <= self.cache_ttl:
                    topic_data[cache_key] = cached_value
        
        return topic_data
    
    def enrich_prompt_with_data(self, prompt: str) -> str:
        """Enrich the prompt with real-time data from Kafka"""
        try:
            # Get recent data from Kafka topics
            realtime_data = self.get_all_topic_data("chat_updates")
            
            if realtime_data:
                # Create context from real-time data
                data_context = "\nRecent context from real-time data:\n"
                for key, value in list(realtime_data.items())[-5:]:  # Last 5 entries
                    data_str = json.dumps(value["data"], indent=2)[:200]  # Limit data size
                    data_context += f"- {data_str}\n"
                
                # Enrich the original prompt with real-time context
                enriched_prompt = f"{prompt}\n\n{data_context}"
                logger.info("Prompt enriched with real-time data")
                return enriched_prompt
            else:
                logger.info("No real-time data available for enrichment")
                return prompt
                
        except Exception as e:
            logger.error(f"Error enriching prompt with real-time data: {e}")
            return prompt

# Global instance to be used in the application
kafka_processor = None

def init_kafka_processor():
    """Initialize the Kafka processor"""
    global kafka_processor
    try:
        # Check if Kafka is enabled
        if os.getenv("ENABLE_KAFKA", "false").lower() == "true":
            kafka_processor = KafkaDataProcessor()
            kafka_processor.start_consumer()
        else:
            logger.info("Kafka integration is disabled")
    except Exception as e:
        logger.error(f"Failed to initialize Kafka processor: {e}")
        kafka_processor = None

def get_kafka_processor():
    """Get the global Kafka processor instance"""
    return kafka_processor