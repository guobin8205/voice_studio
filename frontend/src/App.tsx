import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Component, type ReactNode } from 'react';
import { Layout } from './components/Layout';
import { VoiceDesign } from './pages/VoiceDesign';
import { VoiceClone } from './pages/VoiceClone';
import { VoiceLibrary } from './pages/VoiceLibrary';
import { DebugConsole } from './pages/DebugConsole';

class ErrorBoundary extends Component<{ children: ReactNode }, { error: Error | null }> {
  state = { error: null as Error | null };
  static getDerivedStateFromError(error: Error) { return { error }; }
  render() {
    if (this.state.error) {
      return (
        <div className="flex items-center justify-center h-screen bg-gray-50">
          <div className="text-center max-w-md">
            <div className="text-4xl mb-4">⚠️</div>
            <h1 className="text-lg font-bold text-gray-900 mb-2">页面加载出错</h1>
            <p className="text-sm text-gray-500 mb-4">{this.state.error.message}</p>
            <button
              onClick={() => { this.setState({ error: null }); window.location.reload(); }}
              className="px-6 py-2 bg-violet-500 text-white rounded-lg font-medium text-sm hover:bg-violet-600"
            >
              重试
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

function App() {
  return (
    <ErrorBoundary>
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
    </ErrorBoundary>
  );
}

export default App;
