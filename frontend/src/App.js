import React, { useState, useRef, useEffect } from 'react';
import './App.css';

function App() {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState([
    { id: 1, text: "Hello! I'm your AI assistant. How can I help you today?", sender: 'ai', timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) }
  ]);
  const [loading, setLoading] = useState(false);
  const [model, setModel] = useState('qwen2.5:3b'); // Default model
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const sendMessage = async () => {
    if (!input.trim()) return;

    // Add user message
    const userMessage = { 
      id: Date.now(), 
      text: input, 
      sender: 'user',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const backendUrl = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8000';
      
      // Add timeout support
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 second timeout
      
      // Simple non-streaming request
      const response = await fetch(`${backendUrl}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          message: input,
          sessionId: getCurrentSessionId(),
          model: model
        }),
        signal: controller.signal
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      
      // Add AI response
      const aiMessage = { 
        id: Date.now() + 1, 
        text: data.response || data.reply || 'Sorry, I could not process your request.', 
        sender: 'ai',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        sources: data.sources || []
      };
      setMessages(prev => [...prev, aiMessage]);
      
    } catch (error) {
      console.error('Error:', error);
      let errorMessageText = `Sorry, there was an error: `;
      
      if (error.name === 'AbortError') {
        errorMessageText += 'Request timed out. Please try again.';
      } else if (error.message.includes('Failed to fetch')) {
        errorMessageText += 'Unable to connect to server. Make sure backend is running.';
      } else {
        errorMessageText += error.message || 'Please try again.';
      }
      
      const errorMessage = { 
        id: Date.now() + 1, 
        text: errorMessageText, 
        sender: 'ai',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  // Helper function to get or create session ID
  const getCurrentSessionId = () => {
    if (!window.currentSessionId) {
      window.currentSessionId = Math.random().toString(36).substring(2, 15);
    }
    return window.currentSessionId;
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="App">
      <div className="chat-container">
        <div className="chat-header">
          <h2>ConvoAI</h2>
          <div className="model-selector">
            <input
              type="text"
              value={model}
              onChange={(e) => setModel(e.target.value)}
              placeholder="Model name (e.g., qwen2.5:3b)"
              className="model-input"
            />
          </div>
          <div className="status-indicator">
            <span className="status-dot online"></span>
            <span>Online</span>
          </div>
        </div>
        
        <div className="messages">
          {messages.map((msg) => (
            <div key={msg.id} className={`message ${msg.sender}`}>
              <div className="message-content">
                {msg.text}
              </div>
              <div className="message-timestamp">
                {msg.timestamp}
              </div>
            </div>
          ))}
          {loading && (
            <div className="message ai">
              <div className="message-content">
                <div className="typing-indicator">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
        
        <div className="input-area">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Type your message here..."
            rows="1"
            className="chat-input"
          />
          <button 
            onClick={sendMessage} 
            disabled={loading}
            className="send-button"
          >
            {loading ? 'Sending...' : 'Send'}
          </button>
        </div>
      </div>
    </div>
  );
}

export default App;
