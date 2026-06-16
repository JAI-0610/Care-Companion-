import React, { useState, useRef, useEffect } from 'react';
import { useChat } from '../../context/ChatContext';
import MessageBubble from './MessageBubble';
import ChatInput from './ChatInput';
import ChatHistory from './ChatHistory';
import { Bot, User, Plus } from 'lucide-react';
import './ChatInterface.css';

const ChatInterface = () => {
  const { messages, isLoading, sendMessage, startNewSession, currentSession } = useChat();
  const [showHistory, setShowHistory] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleNewChat = () => {
    startNewSession();
    setShowHistory(false);
  };

  return (
    <div className="chat-interface">
      <div className="chat-sidebar">
        <button className="new-chat-btn" onClick={handleNewChat}>
          <Plus size={20} />
          New Chat
        </button>
        <ChatHistory />
      </div>

      <div className="chat-main">
        <div className="chat-header">
          <div className="chat-title">
            <Bot size={24} />
            <h2>Health Assistant</h2>
          </div>
          <button 
            className="history-toggle"
            onClick={() => setShowHistory(!showHistory)}
          >
            History
          </button>
        </div>

        <div className="messages-container">
          {messages.length === 0 ? (
            <div className="empty-state">
              <Bot size={64} className="empty-icon" />
              <h3>Welcome to Care Companion</h3>
              <p>Describe your symptoms and I'll help you find appropriate OTC medications.</p>
              <div className="example-prompts">
                <p>Try asking:</p>
                <ul>
                  <li>"I have a headache and fever"</li>
                  <li>"What can I take for seasonal allergies?"</li>
                  <li>"I need something for muscle pain"</li>
                </ul>
              </div>
            </div>
          ) : (
            <>
              {messages.map((message) => (
                <MessageBubble key={message.id} message={message} />
              ))}
              {isLoading && (
                <div className="loading-message">
                  <div className="typing-indicator">
                    <span></span>
                    <span></span>
                    <span></span>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </>
          )}
        </div>

        <ChatInput onSendMessage={sendMessage} isLoading={isLoading} />
      </div>

      {showHistory && (
        <div className="chat-history-mobile">
          <div className="history-header">
            <h3>Chat History</h3>
            <button onClick={() => setShowHistory(false)}>Close</button>
          </div>
          <ChatHistory />
        </div>
      )}
    </div>
  );
};

export default ChatInterface;