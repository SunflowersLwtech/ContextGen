import { useState, useRef } from 'react';
import { ai } from '../services/gemini';
import { Upload, Image as ImageIcon, Video, Loader2, Play } from 'lucide-react';
import Markdown from 'react-markdown';

export function VisionStudio() {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [result, setResult] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [prompt, setPrompt] = useState('Analyze this image in detail.');
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0];
    if (selected) {
      setFile(selected);
      const url = URL.createObjectURL(selected);
      setPreview(url);
      setResult(null);
    }
  };

  const analyze = async () => {
    if (!file) return;
    setIsLoading(true);
    setResult(null);

    try {
      const reader = new FileReader();
      reader.onloadend = async () => {
        const base64Data = (reader.result as string).split(',')[1];
        const mimeType = file.type;

        const response = await ai.models.generateContent({
          model: 'gemini-3.1-pro-preview',
          contents: {
            parts: [
              {
                inlineData: {
                  data: base64Data,
                  mimeType,
                },
              },
              { text: prompt },
            ],
          },
        });

        setResult(response.text || 'No description provided.');
      };
      reader.readAsDataURL(file);
    } catch (error: any) {
      console.error(error);
      setResult(`Error: ${error.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)] bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
      <div className="p-6 border-b border-gray-100 flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-semibold tracking-tight text-gray-900">Vision Studio</h2>
          <p className="text-sm text-gray-500 mt-1">Upload images or short videos for deep analysis using Gemini Pro.</p>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-6 grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="space-y-6">
          <div 
            className="border-2 border-dashed border-gray-300 rounded-2xl p-8 flex flex-col items-center justify-center text-center hover:bg-gray-50 transition-colors cursor-pointer min-h-[300px]"
            onClick={() => fileInputRef.current?.click()}
          >
            <input 
              type="file" 
              ref={fileInputRef} 
              className="hidden" 
              accept="image/*,video/mp4,video/webm" 
              onChange={handleFileChange} 
            />
            
            {preview ? (
              file?.type.startsWith('video/') ? (
                <video src={preview} controls className="max-h-64 rounded-lg shadow-sm" />
              ) : (
                <img src={preview} alt="Preview" className="max-h-64 rounded-lg shadow-sm object-contain" />
              )
            ) : (
              <div className="space-y-4">
                <div className="flex justify-center space-x-4 text-gray-400">
                  <ImageIcon className="w-12 h-12" />
                  <Video className="w-12 h-12" />
                </div>
                <div>
                  <p className="text-lg font-medium text-gray-900">Click to upload media</p>
                  <p className="text-sm text-gray-500 mt-1">Supports JPG, PNG, MP4, WEBM</p>
                </div>
              </div>
            )}
          </div>

          <div className="space-y-3">
            <label className="block text-sm font-medium text-gray-700">Analysis Prompt</label>
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              className="w-full border border-gray-300 rounded-xl p-3 focus:ring-2 focus:ring-gray-900 focus:border-transparent outline-none resize-none h-24"
              placeholder="What do you want to know about this media?"
            />
            <button
              onClick={analyze}
              disabled={!file || isLoading}
              className="w-full bg-gray-900 text-white font-medium py-3 rounded-xl hover:bg-gray-800 transition-colors disabled:opacity-50 flex items-center justify-center space-x-2"
            >
              {isLoading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Play className="w-5 h-5" />}
              <span>{isLoading ? 'Analyzing...' : 'Analyze Media'}</span>
            </button>
          </div>
        </div>

        <div className="bg-gray-50 rounded-2xl border border-gray-100 p-6 overflow-y-auto h-full">
          <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-4">Analysis Result</h3>
          {result ? (
            <div className="prose prose-sm max-w-none text-gray-800">
              <Markdown>{result}</Markdown>
            </div>
          ) : (
            <div className="h-full flex items-center justify-center text-gray-400 text-sm text-center">
              Upload media and click analyze to see the results here.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
