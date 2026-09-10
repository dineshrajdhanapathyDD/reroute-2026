import { HashRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ToastProvider } from './components/ui/Toast';
import { MissionProvider } from './lib/mission';
import AppShell from './components/layout/AppShell';
import Chat from './pages/Chat';
import Onboarding from './pages/Onboarding';
import Mission from './pages/Mission';
import Schedule from './pages/Schedule';
import Sessions from './pages/Sessions';
import SessionDetail from './pages/SessionDetail';
import Explore from './pages/Explore';
import Plans from './pages/Plans';
import Prep from './pages/Prep';
import Learning from './pages/Learning';
import ReRoute from './pages/ReRoute';
import Wayfinder from './pages/Wayfinder';
import Journey from './pages/Journey';
import Settings from './pages/Settings';
import SettingsAccessibility from './pages/SettingsAccessibility';
import AgentActivityPage from './pages/AgentActivityPage';
import Demo from './pages/Demo';

export default function App() {
  return (
    <ToastProvider>
      <MissionProvider>
      <HashRouter>
        <Routes>
          <Route path="/" element={<Navigate to="/chat" replace />} />
          <Route path="/chat" element={<Chat />} />
          <Route path="/onboarding" element={<Onboarding />} />

          <Route element={<AppShell />}>
            <Route path="/mission" element={<Mission />} />
            <Route path="/schedule" element={<Schedule />} />
            <Route path="/sessions" element={<Sessions />} />
            <Route path="/sessions/:id" element={<SessionDetail />} />
            <Route path="/explore" element={<Explore />} />
            <Route path="/plans" element={<Plans />} />
            <Route path="/prep" element={<Prep />} />
            <Route path="/learning" element={<Learning />} />
            <Route path="/reroute" element={<ReRoute />} />
            <Route path="/wayfinder" element={<Wayfinder />} />
            <Route path="/journey" element={<Journey />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="/settings/accessibility" element={<SettingsAccessibility />} />
            <Route path="/agent/activity" element={<AgentActivityPage />} />
            <Route path="/demo" element={<Demo />} />
          </Route>

          <Route path="*" element={<Navigate to="/chat" replace />} />
        </Routes>
      </HashRouter>
      </MissionProvider>
    </ToastProvider>
  );
}
