import React, { useState, useRef, useEffect } from 'react';
import { sendChatMessage, fetchChatHistory } from '../../services/api';

export default function ChatWidget({ slug = 'lead-apex-roofing' }) {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([
    {
      sender: 'alex',
      text: "Hi! I'm Alex, Lead Automation Architect. Need custom county fields, webhook specs, or escrow details? Ask me anything!",
    },
  ]);
  const [inputVal, setInputVal] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const chatEndRef = useRef(null);

  // Load persistent running conversation log on open
  useEffect(() => {
    if (isOpen) {
      fetchChatHistory(slug).then((res) => {
        if (res?.messages && res.messages.length > 0) {
          const formatted = res.messages.map((m) => ({
            sender: m.sender,
            text: m.message,
          }));
          setMessages(formatted);
        }
      }).catch(() => {});
    }
  }, [isOpen, slug]);

  useEffect(() => {
    if (isOpen) {
      chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isOpen]);

  const handleSend = async (textToSend) => {
    const msg = textToSend || inputVal.trim();
    if (!msg) return;

    const userMsg = { sender: 'user', text: msg };
    const currentList = [...messages, userMsg];
    setMessages(currentList);
    setInputVal('');
    setIsTyping(true);

    try {
      const data = await sendChatMessage(slug, msg, messages);
      const replyText = data?.reply || "I've noted that requirement! Our autonomous dev swarm will verify the selectors before deployment.";
      setMessages([...currentList, { sender: 'alex', text: replyText }]);
    } catch (err) {
      setMessages([
        ...currentList,
        { sender: 'alex', text: "I'm having a brief connection hitch, but our autonomous pipeline is monitoring your feed. You can also email alex@omnileadfeeder.tech." },
      ]);
    } finally {
      setIsTyping(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <>
      {/* Floating Action Trigger Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        style={{
          position: 'fixed',
          bottom: '24px',
          left: '24px',
          zIndex: 9998,
          background: 'linear-gradient(135deg, var(--cyan), var(--purple))',
          color: '#fff',
          border: 'none',
          borderRadius: '50px',
          padding: '12px 20px',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          fontWeight: 700,
          fontSize: '13px',
          boxShadow: '0 8px 24px rgba(0,0,0,0.6)',
          cursor: 'pointer',
          transition: 'transform 0.2s, box-shadow 0.2s',
        }}
        onMouseEnter={(e) => (e.currentTarget.style.transform = 'translateY(-2px)')}
        onMouseLeave={(e) => (e.currentTarget.style.transform = 'translateY(0)')}
      >
        <span>💬</span>
        <span>{isOpen ? 'Close Chat' : 'Chat with Alex (AI Architect)'}</span>
      </button>

      {/* Glassmorphic Chat Modal */}
      {isOpen && (
        <div
          style={{
            position: 'fixed',
            bottom: '76px',
            left: '24px',
            zIndex: 9999,
            width: '360px',
            maxHeight: '500px',
            background: '#0f172a',
            border: '1px solid var(--border-light)',
            borderRadius: '14px',
            boxShadow: '0 20px 60px rgba(0,0,0,0.8)',
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
            backdropFilter: 'blur(16px)',
          }}
        >
          {/* Header */}
          <div
            style={{
              background: '#162238',
              padding: '14px 16px',
              borderBottom: '1px solid var(--border)',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <div
                style={{
                  width: '10px',
                  height: '10px',
                  borderRadius: '50%',
                  background: 'var(--green)',
                  boxShadow: '0 0 8px var(--green)',
                }}
              />
              <span style={{ fontSize: '13px', fontWeight: 800, color: '#fff' }}>
                Alex • Solutions Architect
              </span>
            </div>
            <button
              onClick={() => setIsOpen(false)}
              style={{
                background: 'none',
                border: 'none',
                color: 'var(--text-muted)',
                cursor: 'pointer',
                fontSize: '16px',
              }}
            >
              ✕
            </button>
          </div>

          {/* Messages Body */}
          <div
            style={{
              padding: '16px',
              flex: 1,
              overflowY: 'auto',
              display: 'flex',
              flexDirection: 'column',
              gap: '12px',
              maxHeight: '340px',
              fontSize: '13px',
              lineHeight: 1.5,
            }}
          >
            {messages.map((m, idx) => (
              <div
                key={idx}
                style={{
                  alignSelf: m.sender === 'user' ? 'flex-end' : 'flex-start',
                  maxWidth: '85%',
                  background: m.sender === 'user' ? 'var(--cyan)' : 'var(--card-alt)',
                  color: m.sender === 'user' ? '#041410' : '#f0f6fc',
                  padding: '10px 14px',
                  borderRadius: '10px',
                  border: m.sender === 'user' ? 'none' : '1px solid var(--border)',
                  fontWeight: m.sender === 'user' ? 600 : 400,
                }}
              >
                {m.text}
              </div>
            ))}
            {isTyping && (
              <div
                style={{
                  alignSelf: 'flex-start',
                  color: 'var(--cyan)',
                  fontSize: '12px',
                  fontFamily: 'var(--mono)',
                  fontStyle: 'italic',
                }}
              >
                Alex is analyzing schema...
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          {/* Quick Prompts */}
          <div
            style={{
              display: 'flex',
              gap: '6px',
              padding: '8px 12px',
              overflowX: 'auto',
              borderTop: '1px solid var(--border)',
              background: '#0b1322',
            }}
          >
            <button
              className="btn btn-outline"
              style={{ fontSize: '11px', padding: '3px 8px', whiteSpace: 'nowrap' }}
              onClick={() => handleSend('How does the $250 escrow deposit work?')}
            >
              How does escrow work?
            </button>
            <button
              className="btn btn-outline"
              style={{ fontSize: '11px', padding: '3px 8px', whiteSpace: 'nowrap' }}
              onClick={() => handleSend('Can you deliver to my Google Sheet at 8:00 AM?')}
            >
              Google Sheet setup?
            </button>
          </div>

          {/* Input Box */}
          <div
            style={{
              padding: '10px 12px',
              background: '#0b1322',
              display: 'flex',
              gap: '8px',
            }}
          >
            <input
              type="text"
              className="form-input"
              style={{ padding: '8px 12px', fontSize: '12px' }}
              placeholder="Ask Alex a question..."
              value={inputVal}
              onChange={(e) => setInputVal(e.target.value)}
              onKeyDown={handleKeyDown}
            />
            <button
              className="btn btn-primary"
              style={{ padding: '8px 14px', fontSize: '12px' }}
              onClick={() => handleSend()}
            >
              Send
            </button>
          </div>
        </div>
      )}
    </>
  );
}
