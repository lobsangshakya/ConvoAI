import React from 'react';
import ChatInterface from './ChatInterface';
import './App.css';

function App() {
  return (
    <div className="App">
      <header className="App-header">
        <h1>AI-Powered Chatbot</h1>
      </header>
      <main>
        <ChatInterface />
      </main>
    </div>
  );
}

export default App;