"""
Example Kafka producer to send real-time data to the chatbot
"""
import json
from kafka import KafkaProducer
import time
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

def create_kafka_producer():
    """Create a Kafka producer instance"""
    bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    try:
        producer = KafkaProducer(
            bootstrap_servers=[bootstrap_servers],
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            key_serializer=lambda k: k.encode('utf-8') if k else None
        )
        return producer
    except Exception as e:
        print(f"Error creating Kafka producer: {e}")
        return None

def send_sample_data():
    """Send sample real-time data to Kafka"""
    producer = create_kafka_producer()
    if not producer:
        print("Failed to create Kafka producer")
        return
    
    try:
        # Send some sample real-time updates
        sample_updates = [
            {
                "type": "news_update",
                "title": "Breaking News",
                "summary": "New developments in AI research announced today",
                "timestamp": datetime.utcnow().isoformat()
            },
            {
                "type": "weather_update", 
                "location": "San Francisco",
                "temperature": "72°F",
                "conditions": "Sunny",
                "timestamp": datetime.utcnow().isoformat()
            },
            {
                "type": "system_status",
                "status": "operational",
                "service": "chatbot_backend",
                "uptime": "99.9%",
                "timestamp": datetime.utcnow().isoformat()
            }
        ]
        
        for i, update in enumerate(sample_updates):
            key = f"update_{i}"
            topic = "chat_updates"
            
            producer.send(topic, key=key, value=update)
            print(f"Sent to topic '{topic}' with key '{key}': {update}")
            time.sleep(1)  # Small delay between messages
        
        # Send periodic updates
        print("Sending periodic updates... Press Ctrl+C to stop")
        counter = len(sample_updates)
        while True:
            periodic_update = {
                "type": "periodic_info",
                "message": f"This is periodic update #{counter}",
                "timestamp": datetime.utcnow().isoformat(),
                "counter": counter
            }
            
            producer.send("chat_updates", key=f"periodic_{counter}", value=periodic_update)
            print(f"Sent periodic update: {periodic_update}")
            counter += 1
            time.sleep(10)  # Send every 10 seconds
            
    except KeyboardInterrupt:
        print("\nStopping producer...")
    except Exception as e:
        print(f"Error sending data: {e}")
    finally:
        producer.close()

if __name__ == "__main__":
    send_sample_data()