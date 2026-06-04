import { lazy, Suspense } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider } from './contexts/ThemeContext';
import Layout from './components/layout/Layout';
import { Toaster } from './components/ui/toaster';
import { Loader2 } from 'lucide-react';

const PageLoader = () => (
  <div className="min-h-screen flex items-center justify-center">
    <Loader2 className="w-12 h-12 text-[var(--accent)] animate-spin" />
  </div>
);

const LazyRoute = ({ children }: { children: React.ReactNode }) => (
  <Suspense fallback={<PageLoader />}>{children}</Suspense>
);

const LoginPage = lazy(() => import('./pages/LoginPage'));
const RegisterPage = lazy(() => import('./pages/RegisterPage'));
const DashboardPage = lazy(() => import('./pages/DashboardPage'));
const TicketsPage = lazy(() => import('./pages/TicketsPage'));
const NewTicketPage = lazy(() => import('./pages/NewTicketPage'));
const TicketDetailPage = lazy(() => import('./pages/TicketDetailPage'));
const CounterpartiesPage = lazy(() => import('./pages/CounterpartiesPage'));
const NewCounterpartyPage = lazy(() => import('./pages/NewCounterpartyPage'));
const CounterpartyDetailPage = lazy(() => import('./pages/CounterpartyDetailPage'));
const MyCompanyPage = lazy(() => import('./pages/MyCompanyPage'));
const InvitationsPage = lazy(() => import('./pages/InvitationsPage'));
const NotificationsPage = lazy(() => import('./pages/NotificationsPage'));
const ProfilePage = lazy(() => import('./pages/ProfilePage'));
const ProjectsPage = lazy(() => import('./pages/ProjectsPage'));
const NewProjectPage = lazy(() => import('./pages/NewProjectPage'));
const ProjectDetailPage = lazy(() => import('./pages/ProjectDetailPage'));
const ProductsTab = lazy(() => import('./pages/ProductsPage'));
const CreateProductPage = lazy(() => import('./pages/CreateProductPage'));
const TasksPage = lazy(() => import('./pages/TasksPage'));

export default function App() {
  return (
    <ThemeProvider>
      <>
        <Routes>
          <Route path="/login" element={<LazyRoute><LoginPage /></LazyRoute>} />
          <Route path="/auth/invite/accept" element={<LazyRoute><RegisterPage /></LazyRoute>} />
          <Route element={<Layout />}>
            <Route path="/dashboard" element={<LazyRoute><DashboardPage /></LazyRoute>} />
            <Route path="/tasks" element={<LazyRoute><TasksPage /></LazyRoute>} />
            <Route path="/tickets" element={<LazyRoute><TicketsPage /></LazyRoute>} />
            <Route path="/tickets/new" element={<LazyRoute><NewTicketPage /></LazyRoute>} />
            <Route path="/tickets/:ticketNumber" element={<LazyRoute><TicketDetailPage /></LazyRoute>} />
            <Route path="/counterparties" element={<LazyRoute><CounterpartiesPage /></LazyRoute>} />
            <Route path="/counterparties/new" element={<LazyRoute><NewCounterpartyPage /></LazyRoute>} />
            <Route path="/counterparties/:id" element={<LazyRoute><CounterpartyDetailPage /></LazyRoute>} />
            <Route path="/projects" element={<LazyRoute><ProjectsPage /></LazyRoute>} />
            <Route path="/projects/new" element={<LazyRoute><NewProjectPage /></LazyRoute>} />
            <Route path="/projects/:id" element={<LazyRoute><ProjectDetailPage /></LazyRoute>} />
            <Route path="/my-company" element={<LazyRoute><MyCompanyPage /></LazyRoute>} />
            <Route path="/invitations" element={<LazyRoute><InvitationsPage /></LazyRoute>} />
            <Route path="/notifications" element={<LazyRoute><NotificationsPage /></LazyRoute>} />
            <Route path="/products" element={<LazyRoute><ProductsTab /></LazyRoute>} />
            <Route path="/products/new" element={<LazyRoute><CreateProductPage /></LazyRoute>} />
            <Route path="/profile" element={<LazyRoute><ProfilePage /></LazyRoute>} />
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
          </Route>
        </Routes>
        <Toaster />
      </>
    </ThemeProvider>
  );
}
