import React from 'react';
import {
  AppBar,
  Toolbar,
  Typography,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Box,
} from '@mui/material';
import { useAppState } from '../../contexts/AppStateContext';

const TopBar: React.FC = () => {
  const { state: appState, setSelectedModel } = useAppState();

  const handleModelChange = (event: any) => {
    setSelectedModel(event.target.value);
  };


  // Don't render if models haven't loaded yet or if there are no models
  if (appState.modelsLoading || appState.models.length === 0) {
    return null;
  }

  return (
    <AppBar 
      position="static" 
      color="default" 
      elevation={1}
      sx={{ 
        backgroundColor: 'background.paper',
        borderBottom: '1px solid',
        borderBottomColor: 'divider',
      }}
    >
      <Toolbar variant="dense">
        <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
          Process Model Workspace
        </Typography>
        

        <Box sx={{ minWidth: 300 }}>
          <FormControl size="small" fullWidth>
            <InputLabel>Process Model</InputLabel>
            <Select
              value={appState.selectedModelKey || ''}
              onChange={handleModelChange}
              label="Process Model"
            >
              {appState.models.map((model) => (
                <MenuItem key={model.id} value={model.model_key}>
                  {model.name}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </Box>
      </Toolbar>
    </AppBar>
  );
};

export default TopBar;