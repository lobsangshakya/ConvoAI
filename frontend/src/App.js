import React, { useState, useRef, useEffect } from 'react';
import './App.css';

function App() {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState([
    { id: 1, text: "Hello! I'm your AI assistant. How can I help you today?", sender: 'ai', timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) }
  ]);
  const [loading, setLoading] = useState(false);
  const [selectedProject, setSelectedProject] = useState('default');
  const [provider, setProvider] = useState('ollama'); // Default provider
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
      // Determine if we should use streaming based on provider
      const useStreaming = provider === 'ollama';
      const endpoint = useStreaming ? '/api/chat/stream' : '/api/chat';
      const backendUrl = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8000';
      
      // Add timeout support
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 second timeout
      
      if (useStreaming) {
        // For streaming, we'll make a special request
        const response = await fetch(`${backendUrl}${endpoint}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ 
            message: input,
            sessionId: getCurrentSessionId(),
            project_id: selectedProject,
            provider: provider,
            model: model
          }),
          signal: controller.signal
        });

        clearTimeout(timeoutId);

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        if (!response.body) {
          throw new Error('ReadableStream not supported in this browser');
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        
        // Create initial AI message
        const aiMessageId = Date.now() + 1;
        const initialAiMessage = { 
          id: aiMessageId, 
          text: '', 
          sender: 'ai',
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        };

        // Add empty AI message to be updated progressively
        setMessages(prev => [...prev, initialAiMessage]);

        try {
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value, { stream: true });
            const lines = chunk.split('\n');

            for (let i = 0; i < lines.length; i++) {
              const line = lines[i];
              
              if (line.startsWith('data: ')) {
                const dataStr = line.slice(6); // Remove 'data: ' prefix
                if (dataStr.trim() && dataStr !== '[DONE]') {
                  try {
                    const data = JSON.parse(dataStr);
                    
                    if (data.content) {
                      // Update the AI message by appending the new content
                      setMessages(prev => {
                        const newMessages = [...prev];
                        const aiMsgIndex = newMessages.findIndex(msg => msg.id === aiMessageId);
                        if (aiMsgIndex !== -1) {
                          // Append the new content to the existing text
                          const currentText = newMessages[aiMsgIndex].text;
                          newMessages[aiMsgIndex] = {
                            ...newMessages[aiMsgIndex],
                            text: currentText + data.content
                          };
                        }
                        return newMessages;
                      });
                    } else if (data.error) {
                      // Handle error case
                      setMessages(prev => {
                        const newMessages = [...prev];
                        const aiMsgIndex = newMessages.findIndex(msg => msg.id === aiMessageId);
                        if (aiMsgIndex !== -1) {
                          newMessages[aiMsgIndex] = {
                            ...newMessages[aiMsgIndex],
                            text: `Error: ${data.error}`
                          };
                        }
                        return newMessages;
                      });
                      break; // Exit the streaming loop on error
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
        const response = await fetch(`${backendUrl}${endpoint}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ 
            message: input,
            sessionId: getCurrentSessionId(),
            project_id: selectedProject,
            provider: provider,
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
          text: data.reply, 
          sender: 'ai',
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          sources: data.sources || [] // Store sources if available
        };
        setMessages(prev => [...prev, aiMessage]);
      }
    } catch (error) {
      console.error('Error:', error);
      let errorMessageText = `Sorry, there was an error: `;
      
      if (error.name === 'AbortError') {
        errorMessageText += 'Request timed out. Please try again.';
      } else if (error.message.includes('Failed to fetch')) {
        errorMessageText += 'Unable to connect to the server. Make sure the backend is running.';
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
              <option value="ollama">Local Ollama</option>
              <option value="local_llm">Local LLM</option>
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