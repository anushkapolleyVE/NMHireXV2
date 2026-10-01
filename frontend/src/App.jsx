import { Routes, Route, Navigate } from 'react-router-dom';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import AdminDashboard from './pages/AdminDashboard';
import MatchAgent from './pages/MatchAgent';
import Candidates from './pages/Candidates';
import JobDescriptions from './pages/JobDescriptions';
import Outreach from './pages/Outreach';
import Register from './pages/Register';
import ScheduleInterview from './pages/ScheduleInterview';

function App() {
  return (
    <Routes>
      <Route path="/" element={<Login />} />
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />

      <Route path="/admin" element={<AdminDashboard />} />
      <Route path="/dashboard" element={<Dashboard />} />
      <Route path="/match-agent" element={<MatchAgent />} />
      <Route path="/candidates" element={<Candidates />} />
      <Route path="/job-descriptions" element={<JobDescriptions />} />
      <Route path="/outreach" element={<Outreach />} />
      <Route path="/schedule/:candidateId" element={<ScheduleInterview />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default App;