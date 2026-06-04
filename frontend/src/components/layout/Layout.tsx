import { useState } from 'react';
import { Outlet, Navigate } from 'react-router-dom';
import Sidebar from './Sidebar';
import Header from './Header';
import { useAuthStore } from '../../stores/authStore';

export default function Layout() {
  const { isAuthenticated } = useAuthStore();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return (
    <div className="min-h-screen bg-[var(--bg-primary)]">
      <div className="flex">
        <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
        
        <div className="flex-1 flex flex-col min-h-screen min-w-0">
          <Header onMenuClick={() => setSidebarOpen(true)} />
          
          <main className="flex-1 p-3 md:p-6 lg:p-8 bg-[var(--bg-primary)] min-w-0">
            <Outlet />
          </main>
        </div>
      </div>
    </div>
  );
}