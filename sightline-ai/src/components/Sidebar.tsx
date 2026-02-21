import { MessageSquare, Mic, Image as ImageIcon, Headphones } from 'lucide-react';

export function Sidebar({ activeTab, setActiveTab }: { activeTab: string, setActiveTab: (tab: string) => void }) {
  const tabs = [
    { id: 'chat', label: 'Smart Chat', icon: MessageSquare },
    { id: 'live', label: 'Live Assistant', icon: Mic },
    { id: 'vision', label: 'Vision Studio', icon: ImageIcon },
    { id: 'audio', label: 'Audio Studio', icon: Headphones },
  ];

  return (
    <div className="w-64 bg-white border-r border-gray-200 flex flex-col">
      <div className="p-6 border-b border-gray-200">
        <h1 className="text-xl font-semibold tracking-tight">SightLine AI</h1>
      </div>
      <nav className="flex-1 p-4 space-y-2">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`w-full flex items-center space-x-3 px-4 py-3 rounded-xl transition-colors ${
                isActive ? 'bg-gray-100 text-gray-900 font-medium' : 'text-gray-500 hover:bg-gray-50 hover:text-gray-900'
              }`}
            >
              <Icon className="w-5 h-5" />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </nav>
    </div>
  );
}
