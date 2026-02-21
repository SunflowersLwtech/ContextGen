import { useState, useRef, useEffect } from 'react';
import { ai } from '../services/gemini';
import Markdown from 'react-markdown';
import { Send, Brain, Search, MapPin, Zap, MessageSquare } from 'lucide-react';
import { ThinkingLevel } from '@google/genai';

type Message = { role: 'user' | 'model'; text: string; urls?: string[] };

export function SmartChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [mode, setMode] = useState<'standard' | 'thinking' | 'search' | 'maps' | 'fast'>('standard');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMsg = input;
    setInput('');
    setMessages(prev => [...prev, { role: 'user', text: userMsg }]);
    setIsLoading(true);

    try {
      let model = 'gemini-3.1-pro-preview';
      let config: any = {};

      if (mode === 'thinking') {
        config.thinkingConfig = { thinkingLevel: ThinkingLevel.HIGH };
      } else if (mode === 'search') {
        model = 'gemini-3-flash-preview';
        config.tools = [{ googleSearch: {} }];
      } else if (mode === 'maps') {
        model = 'gemini-2.5-flash';
        config.tools = [{ googleMaps: {} }];
        try {
          const pos = await new Promise<GeolocationPosition>((res, rej) => navigator.geolocation.getCurrentPosition(res, rej));
          config.toolConfig = {
            retrievalConfig: {
              latLng: {
                latitude: pos.coords.latitude,
                longitude: pos.coords.longitude
              }
            }
          };
        } catch (e) {
          console.warn("Could not get location", e);
        }
      } else if (mode === 'fast') {
        model = 'gemini-2.5-flash-lite';
      }

      const response = await ai.models.generateContent({
        model,
        contents: userMsg,
        config
      });

      let urls: string[] = [];
      if (mode === 'search' || mode === 'maps') {
        const chunks = response.candidates?.[0]?.groundingMetadata?.groundingChunks;
        if (chunks) {
          chunks.forEach((chunk: any) => {
            if (chunk.web?.uri) urls.push(chunk.web.uri);
            if (chunk.maps?.uri) urls.push(chunk.maps.uri);
            if (chunk.maps?.placeAnswerSources?.reviewSnippets) {
              chunk.maps.placeAnswerSources.reviewSnippets.forEach((snippet: any) => {
                if (snippet.uri) urls.push(snippet.uri);
              });
            }
          });
        }
      }

      setMessages(prev => [...prev, { role: 'model', text: response.text || '', urls }]);
    } catch (error: any) {
      console.error(error);
      setMessages(prev => [...prev, { role: 'model', text: `Error: ${error.message}` }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)] bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
      <div className="p-4 border-b border-gray-100 flex gap-2 overflow-x-auto">
        <ModeButton active={mode === 'standard'} onClick={() => setMode('standard')} icon={MessageSquare} label="Standard" />
        <ModeButton active={mode === 'thinking'} onClick={() => setMode('thinking')} icon={Brain} label="Thinking" />
        <ModeButton active={mode === 'search'} onClick={() => setMode('search')} icon={Search} label="Search" />
        <ModeButton active={mode === 'maps'} onClick={() => setMode('maps')} icon={MapPin} label="Maps" />
        <ModeButton active={mode === 'fast'} onClick={() => setMode('fast')} icon={Zap} label="Fast" />
      </div>
      
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {messages.map((msg, idx) => (
          <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[80%] rounded-2xl p-4 ${msg.role === 'user' ? 'bg-gray-900 text-white' : 'bg-gray-50 text-gray-900 border border-gray-100'}`}>
              {msg.role === 'model' ? (
                <div className="prose prose-sm max-w-none">
                  <Markdown>{msg.text}</Markdown>
                  {msg.urls && msg.urls.length > 0 && (
                    <div className="mt-4 pt-4 border-t border-gray-200">
                      <p className="text-xs font-semibold text-gray-500 uppercase mb-2">Sources</p>
                      <ul className="space-y-1">
                        {Array.from(new Set(msg.urls)).map((url, i) => (
                          <li key={i}>
                            <a href={url} target="_blank" rel="noreferrer" className="text-blue-600 hover:underline text-sm break-all">{url}</a>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              ) : (
                <p>{msg.text}</p>
              )}
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-gray-50 rounded-2xl p-4 border border-gray-100">
              <div className="flex space-x-2">
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" />
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }} />
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.4s' }} />
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="p-4 border-t border-gray-100">
        <div className="flex items-center gap-2 bg-gray-50 rounded-xl p-2 border border-gray-200 focus-within:border-gray-400 transition-colors">
          <input
            type="text"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSend()}
            placeholder="Ask anything..."
            className="flex-1 bg-transparent border-none focus:ring-0 px-2 py-1 outline-none"
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || isLoading}
            className="p-2 bg-gray-900 text-white rounded-lg disabled:opacity-50 hover:bg-gray-800 transition-colors"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}

function ModeButton({ active, onClick, icon: Icon, label }: any) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors whitespace-nowrap ${
        active ? 'bg-gray-900 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
      }`}
    >
      <Icon className="w-4 h-4" />
      {label}
    </button>
  );
}
