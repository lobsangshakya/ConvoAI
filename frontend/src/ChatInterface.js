import React, { useState, useEffect, useRef } from 'react';

const ChatInterface = () => {
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [sessionId, setSessionId] = useState('session_' + Date.now());
  const [userId, setUserId] = useState('user_' + Date.now());
  const [ws, setWs] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const messagesEndRef = useRef(null);

  // Connect to WebSocket on component mount
  useEffect(() => {
    const socket = new WebSocket('ws://localhost:8000/ws');
    
    socket.onopen = () => {
      console.log('Connected to WebSocket');
      setIsConnected(true);
    };
    
    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      // Add response to messages
      setMessages(prev => [
        ...prev,
        {
          id: Date.now(),
          text: data.llm_response || data.suggested_response,
          sender: 'bot',
          timestamp: new Date(data.timestamp * 1000).toLocaleTimeString()
        }
      ]);
    };
    
    socket.onclose = () => {
      console.log('Disconnected from WebSocket');
      setIsConnected(false);
    };
    
    setWs(socket);
    
    // Cleanup function
    return () => {
      socket.close();
    };
  }, []);
  
  // Scroll to bottom of messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = async () => {
    if (!inputValue.trim()) return;
    
    // Add user message to UI immediately
    const userMessage = {
      id: Date.now(),
      text: inputValue,
      sender: 'user',
      timestamp: new Date().toLocaleTimeString()
    };
    
    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    
    try {
      // Send message to backend
      const response = await fetch('http://localhost:8000/chat/send', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: userId,
          session_id: sessionId,
          message: inputValue
        })
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const result = await response.json();
      console.log('Message sent:', result);
    } catch (error) {
      console.error('Error sending message:', error);
      
      // Add error message to UI
      setMessages(prev => [
        ...prev,
        {
          id: Date.now(),
          text: 'Sorry, there was an error sending your message. Please try again.',
          sender: 'system',
          timestamp: new Date().toLocaleTimeString()
        }
      ]);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="chat-interface">
      <div className="chat-header">
        <h2>Chat with AI Assistant</h2>
        <div className={`connection-status ${isConnected ? 'connected' : 'disconnected'}`}>
          {isConnected ? '● Connected' : '○ Disconnected'}
        </div>
      </div>
      
      <div className="chat-messages">
        {messages.map((message) => (
          <div 
            key={message.id} 
            className={`message ${message.sender}-message`}
          >
            <div className="message-content">
              <span className="message-text">{message.text}</span>
              <span className="message-time">{message.timestamp}</span>
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>
      
      <div className="chat-input-area">
        <textarea
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="Type your message here..."
          rows="3"
        />
        <button onClick={sendMessage} disabled={!inputValue.trim()}>
          Send
        </button>
      </div>
    </div>
  );
};

export default ChatInterface;