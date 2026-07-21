import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Layout } from './components/Layout';
import { VoiceDesign } from './pages/VoiceDesign';
import { VoiceClone } from './pages/VoiceClone';
import { VoiceLibrary } from './pages/VoiceLibrary';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Navigate to="/voice-design" replace />} />
          <Route path="/voice-design" element={<VoiceDesign />} />
          <Route path="/voice-clone" element={<VoiceClone />} />
          <Route path="/debug" element={<div className="text-gray-400 text-sm">Phase 3 实施</div>} />
          <Route path="/library" element={<VoiceLibrary />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
