import { Routes, Route } from 'react-router-dom';
import AppShell from './components/layout/AppShell';
import DashboardPage from './pages/DashboardPage';
import UploadPage from './pages/UploadPage';
import DatasetDetailPage from './pages/DatasetDetailPage';
import ReviewQueuePage from './pages/ReviewQueuePage';
import ExportPage from './pages/ExportPage';

export default function App() {
  return (
    <AppShell>
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/upload" element={<UploadPage />} />
        <Route path="/datasets/:id" element={<DatasetDetailPage />} />
        <Route path="/review" element={<ReviewQueuePage />} />
        <Route path="/export" element={<ExportPage />} />
      </Routes>
    </AppShell>
  );
}
