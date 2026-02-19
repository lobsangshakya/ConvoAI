import React, { useState, useRef, useEffect } from 'react';
import './App.css';

function App() {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState([
    { id: 1, text: "Hello! I'm your AI assistant. How can I help you today?", sender: 'ai', timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) }
  ]);
  const [loading, setLoading] = useState(false);
  const [selectedProject, setSelectedProject] = useState('default');
  const [provider, setProvider] = useState('local_llm'); // Default provider
  const [model, setModel] = useState('microsoft/DialoGPT-medium'); // Default model
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
      // Determine if we should use streaming based on provider
      const useStreaming = provider === 'ollama';
      const endpoint = useStreaming ? '/api/chat/stream' : '/api/chat';
      
      if (useStreaming) {
        // For streaming, we'll make a special request
        const response = await fetch(`${process.env.REACT_APP_BACKEND_URL || 'http://localhost:8000'}${endpoint}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ 
            message: input,
            sessionId: getCurrentSessionId()
          })
        });

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let aiMessageText = '';
        let aiMessage = { 
          id: Date.now() + 1, 
          text: '', 
          sender: 'ai',
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        };

        // Add empty AI message to be updated progressively
        setMessages(prev => [...prev, aiMessage]);

        try {
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value, { stream: true });
            const lines = chunk.split('\n');

            for (const line of lines) {
              if (line.startsWith('data: ')) {
                const dataStr = line.slice(6); // Remove 'data: ' prefix
                if (dataStr.trim() && dataStr !== '[DONE]') {
                  try {
                    const data = JSON.parse(dataStr);
                    if (data.content) {
                      aiMessageText += data.content;
                      
                      // Update the AI message with new content
                      setMessages(prev => {
                        const newMessages = [...prev];
                        const aiMsgIndex = newMessages.findIndex(msg => msg.id === aiMessage.id);
                        if (aiMsgIndex !== -1) {
                          newMessages[aiMsgIndex] = {
                            ...newMessages[aiMsgIndex],
                            text: aiMessageText
                          };
                        }
                        return newMessages;
                      });
                    } else if (data.error) {
                      // Handle error case
                      aiMessageText = `Error: ${data.error}`;
                      setMessages(prev => {
                        const newMessages = [...prev];
                        const aiMsgIndex = newMessages.findIndex(msg => msg.id === aiMessage.id);
                        if (aiMsgIndex !== -1) {
                          newMessages[aiMsgIndex] = {
                            ...newMessages[aiMsgIndex],
                            text: aiMessageText
                          };
                        }
                        return newMessages;
                      });
                    }
                  } catch (e) {
                    console.error('Error parsing SSE data:', e);
                  }
                }
              }
            }
          }
        } finally {
          reader.releaseLock();
        }
      } else {
        // For non-streaming requests
        const response = await fetch(`${process.env.REACT_APP_BACKEND_URL || 'http://localhost:8000'}${endpoint}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ 
            message: input,
            sessionId: getCurrentSessionId()
          })
        });

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        // Add AI response
        const aiMessage = { 
          id: Date.now() + 1, 
          text: data.reply, 
          sender: 'ai',
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          sources: data.sources || [] // Store sources if available
        };
        setMessages(prev => [...prev, aiMessage]);
      }
    } catch (error) {
      console.error('Error:', error);
      const errorMessage = { 
        id: Date.now() + 1, 
        text: `Sorry, there was an error: ${error.message || 'Please try again.'}`, 
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
          <div className="project-selector">
            <select 
              value={selectedProject} 
              onChange={(e) => setSelectedProject(e.target.value)}
              className="project-dropdown"
            >
              <option value="default">Default Project</option>
              <option value="ollama-project">Local Ollama</option>
              <option value="local-llm">Local LLM</option>
            </select>
            
            <select 
              value={provider} 
              onChange={(e) => {
                setProvider(e.target.value);
                // Update model based on provider
                if (e.target.value === 'ollama') {
                  setModel('qwen2.5:3b');
                } else if (e.target.value === 'local_llm') {
                  setModel('microsoft/DialoGPT-medium');
                }
              }}
              className="provider-dropdown"
            >
              <option value="local_llm">Local LLM</option>
              <option value="ollama">Local Ollama</option>
            </select>
            
            <input
              type="text"
              value={model}
              onChange={(e) => setModel(e.target.value)}
              placeholder="Model name"
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