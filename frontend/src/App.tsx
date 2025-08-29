import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { CssBaseline, Box } from '@mui/material';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { AppStateProvider } from './contexts/AppStateContext';
import { ComposerStateProvider } from './contexts/ComposerStateContext';
import Header from './components/Layout/Header';
import TopBar from './components/Layout/TopBar';
import TabNavigation from './components/Navigation/TabNavigation';
import Login from './components/Auth/Login';
import Signup from './components/Auth/Signup';
import Dashboard from './pages/Dashboard';
import Composer from './pages/Composer';
import PortfolioManager from './pages/PortfolioManager';

const theme = createTheme({
  palette: {
    primary: {
      main: '#4caf50',
    },
    secondary: {
      main: '#66bb6a',
    },
  },
});

const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return <div>Loading...</div>;
  }

  return isAuthenticated ? <>{children}</> : <Navigate to="/login" />;
};

const AppContent: React.FC = () => {
  const { isAuthenticated } = useAuth();

  return (
    <Box sx={{ minHeight: '100vh', backgroundColor: 'grey.50' }}>
      {isAuthenticated && <Header />}
      {isAuthenticated && <TopBar />}
      
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/signup" element={<Signup />} />
        <Route path="/" element={<Navigate to="/dashboard" />} />
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <TabNavigation />
              <Dashboard />
            </ProtectedRoute>
          }
        />
        <Route
          path="/composer"
          element={
            <ProtectedRoute>
              <TabNavigation />
              <Composer />
            </ProtectedRoute>
          }
        />
        <Route
          path="/viewer"
          element={
            <ProtectedRoute>
              <TabNavigation />
              <div>Viewer (Coming Soon)</div>
            </ProtectedRoute>
          }
        />
        <Route
          path="/portfolios"
          element={
            <ProtectedRoute>
              <TabNavigation />
              <PortfolioManager />
            </ProtectedRoute>
          }
        />
        <Route
          path="/console"
          element={
            <ProtectedRoute>
              <TabNavigation />
              <div>Console (Coming Soon)</div>
            </ProtectedRoute>
          }
        />
      </Routes>
    </Box>
  );
};

function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <AuthProvider>
        <AppStateProvider>
          <ComposerStateProvider>
            <Router>
              <AppContent />
            </Router>
          </ComposerStateProvider>
        </AppStateProvider>
      </AuthProvider>
    </ThemeProvider>
  );
}

export default App;
