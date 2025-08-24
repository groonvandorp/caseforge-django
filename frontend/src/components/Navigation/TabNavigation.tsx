import React from 'react';
import { Tabs, Tab, Box } from '@mui/material';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  Dashboard,
  Architecture,
  Visibility,
  Build,
  Terminal,
} from '@mui/icons-material';

const TabNavigation: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();

  const tabs = [
    { label: 'Dashboard', path: '/dashboard', icon: <Dashboard /> },
    { label: 'Composer', path: '/composer', icon: <Architecture /> },
    { label: 'Viewer', path: '/viewer', icon: <Visibility /> },
    { label: 'Build Advisor', path: '/build-advisor', icon: <Build /> },
    { label: 'Console', path: '/console', icon: <Terminal /> },
  ];

  const currentTab = tabs.findIndex(tab => location.pathname.startsWith(tab.path));

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    navigate(tabs[newValue].path);
  };

  return (
    <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
      <Tabs
        value={currentTab >= 0 ? currentTab : 0}
        onChange={handleTabChange}
        variant="scrollable"
        scrollButtons="auto"
        aria-label="navigation tabs"
      >
        {tabs.map((tab, index) => (
          <Tab
            key={tab.path}
            label={tab.label}
            icon={tab.icon}
            iconPosition="start"
            sx={{ minHeight: 48 }}
          />
        ))}
      </Tabs>
    </Box>
  );
};

export default TabNavigation;