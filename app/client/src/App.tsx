import { createBrowserRouter, RouterProvider, NavLink, Outlet } from 'react-router';
import { useEffect, useState } from 'react';
import { Badge } from '@databricks/appkit-ui/react';
import { OverviewPage } from './pages/OverviewPage';
import { CasesPage } from './pages/CasesPage';
import { AskPage } from './pages/AskPage';
import { TopicsPage } from './pages/TopicsPage';
import { MonitoringPage } from './pages/MonitoringPage';

const navLinkClass = ({ isActive }: { isActive: boolean }) =>
  `px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
    isActive ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:bg-muted hover:text-foreground'
  }`;

interface WhoAmI {
  email: string | null;
}

function Layout() {
  const [me, setMe] = useState<WhoAmI | null>(null);
  useEffect(() => {
    fetch('/api/whoami')
      .then((r) => (r.ok ? (r.json() as Promise<WhoAmI>) : null))
      .then(setMe)
      .catch(() => setMe(null));
  }, []);

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <header className="border-b px-4 md:px-6 py-3 flex flex-wrap items-center gap-4">
        <div>
          <h1 className="text-lg font-semibold text-foreground leading-tight">Valtera Motors · VOC Intelligence</h1>
          <p className="text-xs text-muted-foreground">Customer calls and surveys → topics, safety signals, escalations</p>
        </div>
        <nav className="flex gap-1">
          <NavLink to="/" end className={navLinkClass}>Overview</NavLink>
          <NavLink to="/topics" className={navLinkClass}>Topics</NavLink>
          <NavLink to="/cases" className={navLinkClass}>Escalation queue</NavLink>
          <NavLink to="/monitoring" className={navLinkClass}>Monitoring</NavLink>
          <NavLink to="/ask" className={navLinkClass}>Ask Genie</NavLink>
        </nav>
        <div className="ml-auto flex items-center gap-2">
          <Badge variant="outline">Synthetic data</Badge>
          <Badge variant="secondary">{me?.email ?? 'Signed in'}</Badge>
        </div>
      </header>
      <main className="flex-1 p-4 md:p-6">
        <Outlet />
      </main>
    </div>
  );
}

const router = createBrowserRouter([
  {
    element: <Layout />,
    children: [
      { path: '/', element: <OverviewPage /> },
      { path: '/cases', element: <CasesPage /> },
      { path: '/topics', element: <TopicsPage /> },
      { path: '/monitoring', element: <MonitoringPage /> },
      { path: '/ask', element: <AskPage /> },
    ],
  },
]);

export default function App() {
  return <RouterProvider router={router} />;
}
