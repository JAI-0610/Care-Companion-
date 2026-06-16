import React, { createContext, useState, useContext, useEffect } from 'react';
import axios from 'axios';

const ChatContext = createContext();

export const useChat = () => {
  const context = useContext(ChatContext);
  if (!context) {
    throw new Error('useChat must be used within a ChatProvider');
  }
  return context;
};

// Heuristic parser to extract structured recommendations from raw chat replies
const parseRecommendations = (text) => {
  const recommendations = [];
  const lowerText = text.toLowerCase();
  
  if (lowerText.includes('ibuprofen')) {
    recommendations.push({
      name: 'Ibuprofen',
      reason: 'Pain and inflammation relief',
      dosage: '200-400mg every 4-6 hours as needed',
      warnings: ['Take with food to avoid stomach upset', 'Do not take if allergic to NSAIDs', 'Consult doctor if history of kidney/stomach issues']
    });
  }
  if (lowerText.includes('acetaminophen') || lowerText.includes('paracetamol')) {
    recommendations.push({
      name: 'Acetaminophen (Paracetamol)',
      reason: 'Fever and pain relief',
      dosage: '325-650mg every 4-6 hours as needed',
      warnings: ['Do not exceed 4000mg per day', 'Avoid alcohol to prevent liver toxicity', 'Check other OTC labels for acetaminophen']
    });
  }
  if (lowerText.includes('antihistamine') || lowerText.includes('cetirizine') || lowerText.includes('loratadine') || lowerText.includes('diphenhydramine') || lowerText.includes('allergy')) {
    recommendations.push({
      name: 'Antihistamines (e.g. Cetirizine, Loratadine)',
      reason: 'Allergy symptoms (sneezing, runny nose, itching)',
      dosage: '10mg once daily or as directed on package',
      warnings: ['Some types may cause drowsiness', 'Avoid driving if drowsy', 'Do not mix with alcohol or other sedatives']
    });
  }
  if (lowerText.includes('aspirin')) {
    recommendations.push({
      name: 'Aspirin',
      reason: 'Pain, inflammation, and fever relief',
      dosage: '325-650mg every 4 hours as needed',
      warnings: ['Do not give to children/teenagers due to Reye\'s syndrome risk', 'Can cause stomach bleeding', 'Take with food or milk']
    });
  }
  
  return recommendations.length > 0 ? recommendations : null;
};

export const ChatProvider = ({ children }) => {
  const [currentSession, setCurrentSession] = useState(null);
  const [messages, setMessages] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [isLoading, setIsLoading] = useState(false);

  // Load chat sessions from localStorage or backend
  useEffect(() => {
    const storedSessions = localStorage.getItem('health_insight_sessions');
    if (storedSessions) {
      const parsed = JSON.parse(storedSessions);
      setSessions(parsed);
      if (parsed.length > 0) {
        // Load the most recent session
        setCurrentSession(parsed[0]);
        const storedMsgs = localStorage.getItem(`health_insight_messages_${parsed[0].id}`);
        if (storedMsgs) {
          setMessages(JSON.parse(storedMsgs));
        }
      }
    }
  }, []);

  const startNewSession = () => {
    const newSession = {
      id: Date.now().toString(),
      title: 'New Chat Session',
      createdAt: new Date().toISOString(),
      symptoms: []
    };
    
    setCurrentSession(newSession);
    setMessages([]);
    
    const updatedSessions = [newSession, ...sessions];
    setSessions(updatedSessions);
    localStorage.setItem('health_insight_sessions', JSON.stringify(updatedSessions));
    
    return newSession;
  };

  const sendMessage = async (message) => {
    let activeSession = currentSession;
    if (!activeSession) {
      activeSession = startNewSession();
    }

    const userMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: message,
      timestamp: new Date().toISOString()
    };

    const updatedMessages = [...messages, userMessage];
    setMessages(updatedMessages);
    localStorage.setItem(`health_insight_messages_${activeSession.id}`, JSON.stringify(updatedMessages));
    setIsLoading(true);

    try {
      // API call to local Flask backend chatbot endpoint
      const response = await axios.post('/api/chatbot/v2/message', {
        message: message,
        session_id: activeSession.id,
        language: 'en'
      });
      
      const replyText = response.data.reply;
      const aiMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: replyText,
        timestamp: new Date().toISOString(),
        recommendations: parseRecommendations(replyText)
      };
      
      const finalMessages = [...updatedMessages, aiMessage];
      setMessages(finalMessages);
      localStorage.setItem(`health_insight_messages_${activeSession.id}`, JSON.stringify(finalMessages));
      
      // Update session title based on user message if it's the first message
      if (messages.length === 0) {
        const updatedSessions = sessions.map(s => 
          s.id === activeSession.id 
            ? { ...s, title: message.slice(0, 30) + (message.length > 30 ? '...' : '') }
            : s
        );
        setSessions(updatedSessions);
        localStorage.setItem('health_insight_sessions', JSON.stringify(updatedSessions));
      }
    } catch (error) {
      console.error("Chat API error:", error);
      const errorMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: 'Sorry, I encountered an error communicating with the server. Please check that the server is running.',
        timestamp: new Date().toISOString(),
        isError: true
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const loadSession = (sessionId) => {
    const session = sessions.find(s => s.id === sessionId);
    if (session) {
      setCurrentSession(session);
      const storedMsgs = localStorage.getItem(`health_insight_messages_${sessionId}`);
      setMessages(storedMsgs ? JSON.parse(storedMsgs) : []);
    }
  };

  const value = {
    currentSession,
    messages,
    sessions,
    isLoading,
    sendMessage,
    startNewSession,
    loadSession
  };

  return (
    <ChatContext.Provider value={value}>
      {children}
    </ChatContext.Provider>
  );
};