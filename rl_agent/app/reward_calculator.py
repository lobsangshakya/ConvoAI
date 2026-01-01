import re
from typing import Dict, Any


class RewardCalculator:
    def __init__(self):
        # Define positive and negative keywords for reward calculation
        self.positive_keywords = [
            'thank', 'please', 'help', 'appreciate', 'good', 'great', 'excellent',
            'nice', 'wonderful', 'amazing', 'perfect', 'love', 'like', 'awesome'
        ]
        
        self.negative_keywords = [
            'hate', 'bad', 'terrible', 'awful', 'stupid', 'idiot', 'worst',
            'annoying', 'frustrating', 'useless', 'hurt', 'angry', 'mad'
        ]
    
    def calculate_reward(self, message_data: Dict[str, Any]) -> float:
        """Calculate reward based on message content and context"""
        message_text = message_data.get('message', '')
        
        # Calculate base reward
        base_reward = self._calculate_base_reward(message_text)
        
        # Adjust reward based on context
        context_bonus = self._calculate_context_bonus(message_data)
        
        # Final reward with bounds between 0 and 1
        final_reward = max(0.0, min(1.0, base_reward + context_bonus))
        
        return final_reward
    
    def _calculate_base_reward(self, message: str) -> float:
        """Calculate base reward based on message content"""
        score = 0.5  # Base score
        
        # Check for positive keywords
        message_lower = message.lower()
        for keyword in self.positive_keywords:
            if keyword in message_lower:
                score += 0.1
        
        # Check for negative keywords
        for keyword in self.negative_keywords:
            if keyword in message_lower:
                score -= 0.1
        
        # Check for question marks (engagement)
        if '?' in message:
            score += 0.05
        
        # Check for greetings
        greeting_patterns = [r'\bhi\b', r'\bhello\b', r'\bhey\b']
        for pattern in greeting_patterns:
            if re.search(pattern, message_lower):
                score += 0.05
        
        # Normalize score between 0 and 1
        return max(0.0, min(1.0, score))
    
    def _calculate_context_bonus(self, message_data: Dict[str, Any]) -> float:
        """Calculate context-based bonus"""
        bonus = 0.0
        
        # Check if this is a follow-up message in a conversation
        if 'session_id' in message_data and message_data.get('session_id'):
            bonus += 0.05
        
        # Check for user engagement (length of message)
        message_text = message_data.get('message', '')
        if len(message_text) > 50:
            bonus += 0.05
        
        # Check for specific user indicators
        if 'user_id' in message_data and message_data.get('user_id') != 'unknown':
            bonus += 0.03
        
        return bonus