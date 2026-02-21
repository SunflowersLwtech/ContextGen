import { useState, useRef, useEffect } from 'react';
import { ai } from '../services/gemini';
import { Mic, MicOff, Loader2 } from 'lucide-react';
import { LiveServerMessage, Modality } from '@google/genai';

export function LiveAssistant() {
  const [isConnecting, setIsConnecting] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [transcript, setTranscript] = useState<Array<{role: string, text: string}>>([]);
  
  const sessionRef = useRef<any>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null);
  
  // Audio playback queue
  const audioQueueRef = useRef<Float32Array[]>([]);
  const isPlayingRef = useRef(false);
  const nextPlayTimeRef = useRef(0);

  const connect = async () => {
    setIsConnecting(true);
    setError(null);
    setTranscript([]);

    try {
      audioContextRef.current = new (window.AudioContext || (window as any).webkitAudioContext)({ sampleRate: 16000 });
      
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaStreamRef.current = stream;
      
      sourceRef.current = audioContextRef.current.createMediaStreamSource(stream);
      processorRef.current = audioContextRef.current.createScriptProcessor(4096, 1, 1);
      
      sourceRef.current.connect(processorRef.current);
      processorRef.current.connect(audioContextRef.current.destination);

      const sessionPromise = ai.live.connect({
        model: "gemini-2.5-flash-native-audio-preview-12-2025",
        callbacks: {
          onopen: () => {
            setIsConnected(true);
            setIsConnecting(false);
            
            processorRef.current!.onaudioprocess = (e) => {
              const inputData = e.inputBuffer.getChannelData(0);
              const pcm16 = new Int16Array(inputData.length);
              for (let i = 0; i < inputData.length; i++) {
                let s = Math.max(-1, Math.min(1, inputData[i]));
                pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
              }
              
              const buffer = new ArrayBuffer(pcm16.length * 2);
              const view = new DataView(buffer);
              for (let i = 0; i < pcm16.length; i++) {
                view.setInt16(i * 2, pcm16[i], true); // true for little-endian
              }
              
              const base64 = btoa(String.fromCharCode(...new Uint8Array(buffer)));
              
              sessionPromise.then(session => {
                session.sendRealtimeInput({
                  media: {
                    mimeType: "audio/pcm;rate=16000",
                    data: base64
                  }
                });
              });
            };
          },
          onmessage: (message: LiveServerMessage) => {
            if (message.serverContent?.modelTurn?.parts) {
              for (const part of message.serverContent.modelTurn.parts) {
                if (part.inlineData && part.inlineData.data) {
                  playAudioChunk(part.inlineData.data);
                }
              }
            }
            if (message.serverContent?.interrupted) {
              audioQueueRef.current = [];
              isPlayingRef.current = false;
              nextPlayTimeRef.current = audioContextRef.current?.currentTime || 0;
            }
          },
          onclose: () => {
            disconnect();
          },
          onerror: (e) => {
            console.error("Live API Error:", e);
            setError("Connection error occurred.");
            disconnect();
          }
        },
        config: {
          responseModalities: [Modality.AUDIO],
          speechConfig: {
            voiceConfig: { prebuiltVoiceConfig: { voiceName: "Zephyr" } }
          },
          systemInstruction: {
            parts: [{ text: "You are a helpful, conversational AI assistant. Keep your responses concise and natural." }]
          }
        }
      });
      
      sessionRef.current = await sessionPromise;

    } catch (err: any) {
      console.error(err);
      setError(err.message || "Failed to connect");
      setIsConnecting(false);
      disconnect();
    }
  };

  const playAudioChunk = (base64Data: string) => {
    if (!audioContextRef.current) return;
    
    const binaryString = atob(base64Data);
    const bytes = new Uint8Array(binaryString.length);
    for (let i = 0; i < binaryString.length; i++) {
      bytes[i] = binaryString.charCodeAt(i);
    }
    
    const pcm16 = new Int16Array(bytes.buffer);
    const float32 = new Float32Array(pcm16.length);
    for (let i = 0; i < pcm16.length; i++) {
      float32[i] = pcm16[i] / 32768.0;
    }
    
    const audioBuffer = audioContextRef.current.createBuffer(1, float32.length, 24000);
    audioBuffer.getChannelData(0).set(float32);
    
    const source = audioContextRef.current.createBufferSource();
    source.buffer = audioBuffer;
    source.connect(audioContextRef.current.destination);
    
    const currentTime = audioContextRef.current.currentTime;
    if (nextPlayTimeRef.current < currentTime) {
      nextPlayTimeRef.current = currentTime;
    }
    
    source.start(nextPlayTimeRef.current);
    nextPlayTimeRef.current += audioBuffer.duration;
  };

  const disconnect = () => {
    if (processorRef.current) {
      processorRef.current.disconnect();
      processorRef.current.onaudioprocess = null;
    }
    if (sourceRef.current) {
      sourceRef.current.disconnect();
    }
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach(t => t.stop());
    }
    if (sessionRef.current) {
      // @ts-ignore
      sessionRef.current.close?.();
    }
    setIsConnected(false);
    setIsConnecting(false);
    audioQueueRef.current = [];
    nextPlayTimeRef.current = 0;
  };

  useEffect(() => {
    return () => {
      disconnect();
      if (audioContextRef.current) {
        audioContextRef.current.close();
      }
    };
  }, []);

  return (
    <div className="flex flex-col items-center justify-center h-[calc(100vh-4rem)] bg-white rounded-2xl shadow-sm border border-gray-100 p-8">
      <div className="max-w-md w-full text-center space-y-8">
        <div className="space-y-4">
          <h2 className="text-3xl font-semibold tracking-tight text-gray-900">Live Assistant</h2>
          <p className="text-gray-500">Have a natural, real-time voice conversation with Gemini.</p>
        </div>

        <div className="relative flex justify-center items-center h-48">
          {isConnected && (
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="w-32 h-32 bg-blue-100 rounded-full animate-ping opacity-75"></div>
              <div className="w-24 h-24 bg-blue-200 rounded-full animate-pulse absolute"></div>
            </div>
          )}
          
          <button
            onClick={isConnected ? disconnect : connect}
            disabled={isConnecting}
            className={`relative z-10 p-8 rounded-full transition-all duration-300 shadow-lg ${
              isConnected 
                ? 'bg-red-500 hover:bg-red-600 text-white' 
                : 'bg-gray-900 hover:bg-gray-800 text-white'
            } disabled:opacity-50 disabled:cursor-not-allowed`}
          >
            {isConnecting ? (
              <Loader2 className="w-10 h-10 animate-spin" />
            ) : isConnected ? (
              <MicOff className="w-10 h-10" />
            ) : (
              <Mic className="w-10 h-10" />
            )}
          </button>
        </div>

        <div className="h-12">
          {error && <p className="text-red-500 text-sm font-medium">{error}</p>}
          {isConnected && <p className="text-blue-600 font-medium animate-pulse">Listening and speaking...</p>}
          {isConnecting && <p className="text-gray-500 font-medium">Connecting to Gemini Live...</p>}
        </div>
      </div>
    </div>
  );
}
