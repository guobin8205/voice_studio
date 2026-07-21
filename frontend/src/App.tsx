import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Layout } from './components/Layout';
import { VoiceDesign } from './pages/VoiceDesign';
import { VoiceClone } from './pages/VoiceClone';
import { VoiceLibrary } from './pages/VoiceLibrary';
import { DebugConsole } from './pages/DebugConsole';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Navigate to="/voice-design" replace />} />
          <Route path="/voice-design" element={<VoiceDesign />} />
          <Route path="/voice-clone" element={<VoiceClone />} />
          <Route path="/debug" element={<DebugConsole />} />
          <Route path="/library" element={<VoiceLibrary />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
