/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { useState } from 'react';
import { Sidebar } from './components/Sidebar';
import { SmartChat } from './components/SmartChat';
import { LiveAssistant } from './components/LiveAssistant';
import { VisionStudio } from './components/VisionStudio';
import { AudioStudio } from './components/AudioStudio';

export default function App() {
  const [activeTab, setActiveTab] = useState('chat');

  return (
    <div className="flex h-screen bg-gray-50 font-sans text-gray-900">
      <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} />
      <main className="flex-1 p-8 overflow-hidden">
        {activeTab === 'chat' && <SmartChat />}
        {activeTab === 'live' && <LiveAssistant />}
        {activeTab === 'vision' && <VisionStudio />}
        {activeTab === 'audio' && <AudioStudio />}
      </main>
    </div>
  );
}
