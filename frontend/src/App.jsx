/**
 * App.jsx — Root application component with page routing.
 * Manages student session data, settings, and theme from the setup form.
 */

import { useState, useCallback, useEffect } from 'react';
import useChat from './hooks/useChat';
import Layout from './components/Layout';
import Landing from './pages/Landing';
import Dashboard from './pages/Dashboard';
import Chat from './pages/Chat';
import StudyMode from './pages/StudyMode';
import StudyPlan from './pages/StudyPlan';
import Documents from './pages/Documents';
import Settings from './pages/Settings';
import Feedback from './pages/Feedback';
import ExamPapers from './pages/ExamPapers';

const DEFAULT_SETTINGS = { tone: 'professional', darkMode: true };

function loadSettings() {
  try {
    const raw = localStorage.getItem('syllabusai_settings');
    if (raw) return { ...DEFAULT_SETTINGS, ...JSON.parse(raw) };
  } catch { /* ignore */ }
  return DEFAULT_SETTINGS;
}

function App() {
  const [currentPage, setCurrentPage] = useState('landing');
  const [studentInfo, setStudentInfo] = useState(null);
  const [selectedSubject, setSelectedSubject] = useState(null);
  const [selectedUnit, setSelectedUnit] = useState(null);
  const [pageParams, setPageParams] = useState({});
  const [appSettings, setAppSettings] = useState(loadSettings);

  // Lift chat state to App level so it persists across page switches
  const chatState = useChat();

  // Lift study plan state to App level so it persists across page switches
  const [studyPlanState, setStudyPlanState] = useState({
    selectedSubject: null,
    section: null,
    message: '',
    plan: null,
    refineMessages: [],
  });

  // Apply theme to DOM
  useEffect(() => {
    document.documentElement.setAttribute(
      'data-theme',
      appSettings.darkMode ? 'dark' : 'light'
    );
  }, [appSettings.darkMode]);

  const navigate = useCallback((page, params = {}) => {
    setCurrentPage(page);
    setPageParams(params);

    if (params.subjectCode) {
      setSelectedSubject(params.subjectCode);
    }
    if (params.unitNumber) {
      setSelectedUnit(params.unitNumber);
    }
  }, []);

  // Called when student submits the setup form
  const handleStartPreparation = useCallback((formData) => {
    setStudentInfo(formData);
    setSelectedSubject(formData.subject);
    setSelectedUnit(formData.unit);
    setCurrentPage('chat');
  }, []);

  const handleSelectSubject = useCallback((subjectCode) => {
    setSelectedSubject(subjectCode);
    setSelectedUnit(null); // Reset unit — Chat page will show UnitSelector
    setCurrentPage('chat');
  }, []);

  const handleSwitchContext = useCallback(({ subjectCode, unitNumber }) => {
    if (subjectCode) setSelectedSubject(subjectCode);
    if (unitNumber) setSelectedUnit(unitNumber);
  }, []);

  const handleUpdateSettings = useCallback((newSettings) => {
    setAppSettings(newSettings);
    localStorage.setItem('syllabusai_settings', JSON.stringify(newSettings));
  }, []);

  // Landing page (setup form) renders without sidebar
  if (currentPage === 'landing') {
    return (
      <>
        <div className="bg-mesh" />
        <div className="bg-grid" />
        <Landing onStartPreparation={handleStartPreparation} />
      </>
    );
  }

  // All other pages use the Layout shell
  const renderPage = () => {
    switch (currentPage) {
      case 'dashboard':
        return <Dashboard onSelectSubject={handleSelectSubject} />;
      case 'chat':
        return (
          <Chat
            subjectCode={selectedSubject || pageParams.subjectCode}
            initialUnit={selectedUnit || pageParams.unitNumber}
            studentInfo={studentInfo}
            onBack={() => navigate('dashboard')}
            onSwitchContext={handleSwitchContext}
            tone={appSettings.tone}
            chatState={chatState}
          />
        );
      case 'study-mode':
        return (
          <StudyMode
            subjectCode={pageParams.subjectCode || selectedSubject}
            studentInfo={studentInfo}
            onBack={() => navigate('dashboard')}
          />
        );
      case 'study-plan':
        return (
          <StudyPlan
            studentInfo={studentInfo}
            onBack={() => navigate('dashboard')}
            persistedState={studyPlanState}
            onStateChange={setStudyPlanState}
          />
        );
      case 'documents':
        return (
          <Documents
            onBack={() => navigate('dashboard')}
          />
        );
      case 'exam-papers':
        return <ExamPapers />;
      case 'feedback':
        return (
          <Feedback
            studentInfo={studentInfo}
          />
        );
      case 'settings':
        return (
          <Settings
            settings={appSettings}
            onUpdateSettings={handleUpdateSettings}
          />
        );
      default:
        return <Dashboard onSelectSubject={handleSelectSubject} />;
    }
  };

  return (
    <Layout
      activePage={currentPage}
      onNavigate={navigate}
      studentInfo={studentInfo}
    >
      {renderPage()}
    </Layout>
  );
}

export default App;
