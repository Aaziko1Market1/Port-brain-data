import { Routes, Route, Link, useLocation } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { 
  LayoutDashboard, Users, Package, AlertTriangle, 
  Activity, Bot, Target, Upload
} from 'lucide-react';
import { api } from './api/client';

// Pages
import Dashboard from './pages/Dashboard';
import BuyerList from './pages/BuyerList';
import Buyer360Page from './pages/Buyer360Page';
import HsDashboard from './pages/HsDashboard';
import RiskOverview from './pages/RiskOverview';
import BuyerHunter from './pages/BuyerHunter';
import AdminUpload from './pages/AdminUpload';

function App() {
  const location = useLocation();
  
  const { data: aiStatus } = useQuery({
    queryKey: ['ai-status'],
    queryFn: api.getAIStatus,
    staleTime: 60000,
  });

  const navItems = [
    { path: '/', label: 'Dashboard', icon: LayoutDashboard },
    { path: '/buyer-hunter', label: 'Buyer Hunter', icon: Target },
    { path: '/buyers', label: 'Buyers', icon: Users },
    { path: '/hs-dashboard', label: 'HS Dashboard', icon: Package },
    { path: '/risk', label: 'Risk Overview', icon: AlertTriangle },
    { path: '/admin/upload', label: 'Upload Files', icon: Upload },
  ];

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center space-x-3">
              <Activity className="h-8 w-8 text-blue-600" />
              <div>
                <h1 className="text-xl font-bold text-gray-900">GTI-OS Control Tower</h1>
                <p className="text-xs text-gray-500">Global Trade Intelligence</p>
              </div>
            </div>
            
            {/* AI Status Badge */}
            <div className="flex items-center space-x-2">
              <Bot className={`h-5 w-5 ${aiStatus?.available ? 'text-green-500' : 'text-gray-400'}`} />
              <span className={`text-sm ${aiStatus?.available ? 'text-green-600' : 'text-gray-500'}`}>
                {aiStatus?.available ? `AI: ${aiStatus.model}` : 'AI Offline'}
              </span>
            </div>
          </div>
        </div>
      </header>

      <div className="flex">
        {/* Sidebar */}
        <nav className="w-64 bg-white border-r border-gray-200 min-h-[calc(100vh-64px)]">
          <div className="p-4 space-y-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = location.pathname === item.path || 
                (item.path !== '/' && location.pathname.startsWith(item.path));
              
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`flex items-center space-x-3 px-4 py-3 rounded-lg transition-colors ${
                    isActive
                      ? 'bg-blue-50 text-blue-700 font-medium'
                      : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                  }`}
                >
                  <Icon className="h-5 w-5" />
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </div>
        </nav>

        {/* Main Content */}
        <main className="flex-1 p-6">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/buyers" element={<BuyerList />} />
            <Route path="/buyers/:buyerUuid" element={<Buyer360Page />} />
            <Route path="/hs-dashboard" element={<HsDashboard />} />
            <Route path="/risk" element={<RiskOverview />} />
            <Route path="/buyer-hunter" element={<BuyerHunter />} />
            <Route path="/admin/upload" element={<AdminUpload />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}

export default App;
