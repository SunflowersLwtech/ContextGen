import { useState, useRef } from 'react';
import { ai } from '../services/gemini';
import { Mic, Square, Play, Loader2, FileAudio, Volume2 } from 'lucide-react';
import { Modality } from '@google/genai';
import Markdown from 'react-markdown';

export function AudioStudio() {
  const [activeTab, setActiveTab] = useState<'transcribe' | 'tts'>('transcribe');
  const [isRecording, setIsRecording] = useState(false);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [transcript, setTranscript] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  
  const [ttsText, setTtsText] = useState('Hello! I am Gemini, your AI assistant. How can I help you today?');
  const [ttsAudioUrl, setTtsAudioUrl] = useState<string | null>(null);
  const [isTtsLoading, setIsTtsLoading] = useState(false);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          audioChunksRef.current.push(e.data);
        }
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        const url = URL.createObjectURL(audioBlob);
        setAudioUrl(url);
        await transcribeAudio(audioBlob);
      };

      mediaRecorder.start();
      setIsRecording(true);
      setTranscript(null);
    } catch (err) {
      console.error('Error accessing microphone:', err);
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop());
    }
  };

  const transcribeAudio = async (blob: Blob) => {
    setIsLoading(true);
    try {
      const reader = new FileReader();
      reader.onloadend = async () => {
        const base64Data = (reader.result as string).split(',')[1];
        
        const response = await ai.models.generateContent({
          model: 'gemini-3-flash-preview',
          contents: {
            parts: [
              {
                inlineData: {
                  data: base64Data,
                  mimeType: blob.type,
                },
              },
              { text: 'Please transcribe this audio accurately.' },
            ],
          },
        });

        setTranscript(response.text || 'No transcription available.');
      };
      reader.readAsDataURL(blob);
    } catch (error: any) {
      console.error('Transcription error:', error);
      setTranscript(`Error: ${error.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const generateSpeech = async () => {
    if (!ttsText.trim()) return;
    setIsTtsLoading(true);
    setTtsAudioUrl(null);

    try {
      const response = await ai.models.generateContent({
        model: "gemini-2.5-flash-preview-tts",
        contents: [{ parts: [{ text: ttsText }] }],
        config: {
          responseModalities: [Modality.AUDIO],
          speechConfig: {
            voiceConfig: {
              prebuiltVoiceConfig: { voiceName: 'Kore' },
            },
          },
        },
      });

      const base64Audio = response.candidates?.[0]?.content?.parts?.[0]?.inlineData?.data;
      if (base64Audio) {
        const binaryString = atob(base64Audio);
        const bytes = new Uint8Array(binaryString.length);
        for (let i = 0; i < binaryString.length; i++) {
          bytes[i] = binaryString.charCodeAt(i);
        }
        
        // The TTS model returns 24kHz PCM 16-bit little-endian.
        // We need to wrap it in a WAV header to play it in an <audio> element.
        const wavBuffer = createWavHeader(bytes.buffer, 24000, 1, 16);
        const blob = new Blob([wavBuffer], { type: 'audio/wav' });
        setTtsAudioUrl(URL.createObjectURL(blob));
      } else {
        throw new Error("No audio data returned");
      }
    } catch (error: any) {
      console.error('TTS error:', error);
      alert(`Error generating speech: ${error.message}`);
    } finally {
      setIsTtsLoading(false);
    }
  };

  // Helper to create a WAV file from raw PCM data
  const createWavHeader = (pcmData: ArrayBuffer, sampleRate: number, numChannels: number, bitsPerSample: number) => {
    const header = new ArrayBuffer(44);
    const view = new DataView(header);
    
    // RIFF chunk descriptor
    writeString(view, 0, 'RIFF');
    view.setUint32(4, 36 + pcmData.byteLength, true);
    writeString(view, 8, 'WAVE');
    
    // fmt sub-chunk
    writeString(view, 12, 'fmt ');
    view.setUint32(16, 16, true); // Subchunk1Size (16 for PCM)
    view.setUint16(20, 1, true); // AudioFormat (1 for PCM)
    view.setUint16(22, numChannels, true);
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * numChannels * (bitsPerSample / 8), true); // ByteRate
    view.setUint16(32, numChannels * (bitsPerSample / 8), true); // BlockAlign
    view.setUint16(34, bitsPerSample, true);
    
    // data sub-chunk
    writeString(view, 36, 'data');
    view.setUint32(40, pcmData.byteLength, true);
    
    // Combine header and PCM data
    const wavFile = new Uint8Array(header.byteLength + pcmData.byteLength);
    wavFile.set(new Uint8Array(header), 0);
    wavFile.set(new Uint8Array(pcmData), header.byteLength);
    
    return wavFile.buffer;
  };

  const writeString = (view: DataView, offset: number, string: string) => {
    for (let i = 0; i < string.length; i++) {
      view.setUint8(offset + i, string.charCodeAt(i));
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)] bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
      <div className="p-6 border-b border-gray-100">
        <h2 className="text-2xl font-semibold tracking-tight text-gray-900">Audio Studio</h2>
        <p className="text-sm text-gray-500 mt-1">Transcribe your voice or generate speech from text.</p>
        
        <div className="flex space-x-4 mt-6">
          <button
            onClick={() => setActiveTab('transcribe')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              activeTab === 'transcribe' ? 'bg-gray-900 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            <div className="flex items-center space-x-2">
              <FileAudio className="w-4 h-4" />
              <span>Transcribe</span>
            </div>
          </button>
          <button
            onClick={() => setActiveTab('tts')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              activeTab === 'tts' ? 'bg-gray-900 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            <div className="flex items-center space-x-2">
              <Volume2 className="w-4 h-4" />
              <span>Text to Speech</span>
            </div>
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        {activeTab === 'transcribe' ? (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 h-full">
            <div className="flex flex-col items-center justify-center space-y-8 border-2 border-dashed border-gray-200 rounded-2xl p-8 bg-gray-50">
              <div className="relative">
                {isRecording && (
                  <div className="absolute inset-0 flex items-center justify-center">
                    <div className="w-24 h-24 bg-red-100 rounded-full animate-ping opacity-75"></div>
                  </div>
                )}
                <button
                  onClick={isRecording ? stopRecording : startRecording}
                  className={`relative z-10 p-6 rounded-full transition-all duration-300 shadow-md ${
                    isRecording ? 'bg-red-500 hover:bg-red-600 text-white' : 'bg-gray-900 hover:bg-gray-800 text-white'
                  }`}
                >
                  {isRecording ? <Square className="w-8 h-8" /> : <Mic className="w-8 h-8" />}
                </button>
              </div>
              
              <div className="text-center">
                <p className="text-lg font-medium text-gray-900">
                  {isRecording ? 'Recording...' : 'Click to start recording'}
                </p>
                <p className="text-sm text-gray-500 mt-1">
                  {isRecording ? 'Click the square to stop and transcribe' : 'Uses Gemini 3 Flash for fast transcription'}
                </p>
              </div>

              {audioUrl && !isRecording && (
                <div className="w-full max-w-xs mt-4">
                  <audio src={audioUrl} controls className="w-full" />
                </div>
              )}
            </div>

            <div className="bg-white rounded-2xl border border-gray-200 p-6 overflow-y-auto shadow-sm">
              <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-4 flex items-center">
                {isLoading && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                Transcription Result
              </h3>
              {transcript ? (
                <div className="prose prose-sm max-w-none text-gray-800">
                  <Markdown>{transcript}</Markdown>
                </div>
              ) : (
                <div className="h-full flex items-center justify-center text-gray-400 text-sm text-center">
                  {isLoading ? 'Transcribing audio...' : 'Record audio to see the transcription here.'}
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="max-w-3xl mx-auto space-y-8">
            <div className="space-y-3">
              <label className="block text-sm font-medium text-gray-700">Text to Speak</label>
              <textarea
                value={ttsText}
                onChange={(e) => setTtsText(e.target.value)}
                className="w-full border border-gray-300 rounded-xl p-4 focus:ring-2 focus:ring-gray-900 focus:border-transparent outline-none resize-none h-40 text-gray-800"
                placeholder="Enter text to convert to speech..."
              />
              <button
                onClick={generateSpeech}
                disabled={!ttsText.trim() || isTtsLoading}
                className="w-full bg-gray-900 text-white font-medium py-3 rounded-xl hover:bg-gray-800 transition-colors disabled:opacity-50 flex items-center justify-center space-x-2"
              >
                {isTtsLoading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Play className="w-5 h-5" />}
                <span>{isTtsLoading ? 'Generating Speech...' : 'Generate Speech'}</span>
              </button>
            </div>

            {ttsAudioUrl && (
              <div className="bg-gray-50 rounded-2xl p-6 border border-gray-200 space-y-4">
                <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider">Generated Audio</h3>
                <audio src={ttsAudioUrl} controls autoPlay className="w-full" />
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
