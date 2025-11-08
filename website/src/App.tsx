import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { motion } from 'framer-motion';
import './App.css';

// Import pages
import LandingPage from './pages/LandingPage';
import LearningStudio from './pages/LearningStudio';
import ResearchLab from './pages/ResearchLab';
import QAEngine from './pages/QAEngine';
import UsagePage from './pages/UsagePage';

// Page transition wrapper
const PageTransition: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      transition={{ duration: 0.4, ease: "easeOut" }}
      className="min-h-screen"
    >
      {children}
    </motion.div>
  );
};

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-cyan-50/30">
        <Routes>
          <Route path="/" element={
            <PageTransition>
              <LandingPage />
            </PageTransition>
          } />
          <Route path="/learning" element={
            <PageTransition>
              <LearningStudio />
            </PageTransition>
          } />
          <Route path="/research" element={
            <PageTransition>
              <ResearchLab />
            </PageTransition>
          } />
          <Route path="/qa" element={
            <PageTransition>
              <QAEngine />
            </PageTransition>
          } />
          <Route path="/usage" element={
            <PageTransition>
              <UsagePage />
            </PageTransition>
          } />
        </Routes>
      </div>
    </Router>
  );
}

export default App;