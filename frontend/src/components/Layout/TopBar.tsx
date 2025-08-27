import React, { useState } from 'react';
import {
  AppBar,
  Toolbar,
  Typography,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Box,
  TextField,
  InputAdornment,
  IconButton,
  Paper,
  List,
  ListItem,
  ListItemText,
  Chip,
  Popper,
  ClickAwayListener,
} from '@mui/material';
import { Search, Clear } from '@mui/icons-material';
import { useAppState } from '../../contexts/AppStateContext';
import { apiService } from '../../services/api';
import { useNavigate } from 'react-router-dom';

const TopBar: React.FC = () => {
  const { state: appState, setSelectedModel } = useAppState();
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [showResults, setShowResults] = useState(false);
  const [searchAnchorEl, setSearchAnchorEl] = useState<HTMLElement | null>(null);

  const handleModelChange = (event: any) => {
    setSelectedModel(event.target.value);
  };

  const handleSearchChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setSearchQuery(event.target.value);
  };

  const handleSearchSubmit = async () => {
    if (!searchQuery.trim()) {
      console.log('🔍 Search aborted - empty query');
      return;
    }
    
    console.log('🔍 Search initiated for:', searchQuery);
    console.log('🔍 Auth token exists:', !!localStorage.getItem('access_token'));
    console.log('🔍 Current selected model:', appState.selectedModelKey);
    
    if (!appState.selectedModelKey) {
      console.log('🔍 Search aborted - no model selected');
      return;
    }
    
    setSearchLoading(true);
    
    try {
      console.log('🔍 Calling search API...');
      
      const response = await apiService.searchNodes(searchQuery, {
        model_key: appState.selectedModelKey,
        limit: 10,
        min_similarity: 0.3
      });
      
      console.log('🔍 Search API response:', response);
      setSearchResults(response.results);
      setShowResults(true);
      
      if (response.results.length > 0) {
        console.log(`🔍 ✅ Found ${response.results.length} results (${response.search_type}):`);
        response.results.forEach((result, index) => {
          console.log(`  ${index + 1}. [${result.code}] ${result.name} (similarity: ${result.similarity_score || 'N/A'})`);
        });
      } else {
        console.log('🔍 ❌ No results found');
      }
    } catch (error: any) {
      console.error('🔍 ❌ Search error:', error);
      console.error('🔍 Error details:', {
        status: error.response?.status,
        message: error.response?.data || error.message,
        url: error.config?.url
      });
      setSearchResults([]);
    } finally {
      setSearchLoading(false);
      console.log('🔍 Search completed');
    }
  };

  const handleSearchClear = () => {
    setSearchQuery('');
    setSearchResults([]);
    setShowResults(false);
  };

  const handleSearchKeyPress = (event: React.KeyboardEvent) => {
    if (event.key === 'Enter') {
      handleSearchSubmit();
    }
  };

  const handleClickAway = () => {
    setShowResults(false);
  };

  const handleResultClick = (result: any) => {
    console.log('🔍 User selected result:', result);
    console.log('🔍 Navigating to Composer with node ID:', result.node_id);
    
    // Hide search results
    setShowResults(false);
    
    // Navigate to Composer page with nodeId parameter
    navigate(`/composer?nodeId=${result.node_id}`);
  };


  // Don't render if still loading, but show even if no models (could be auth issue)
  if (appState.modelsLoading) {
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
          <Typography variant="body2" color="text.secondary">
            Loading...
          </Typography>
        </Toolbar>
      </AppBar>
    );
  }

  if (appState.models.length === 0) {
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
          <Typography variant="body2" color="error">
            No models available - please check authentication
          </Typography>
        </Toolbar>
      </AppBar>
    );
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
        
        {/* Search Input */}
        <ClickAwayListener onClickAway={handleClickAway}>
          <Box sx={{ minWidth: 350, mr: 2, position: 'relative' }}>
            <TextField
              size="small"
              fullWidth
              placeholder="Search processes..."
              value={searchQuery}
              onChange={handleSearchChange}
              onKeyPress={handleSearchKeyPress}
              ref={(el) => setSearchAnchorEl(el)}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <IconButton
                      size="small"
                      onClick={handleSearchSubmit}
                      disabled={searchLoading || !searchQuery.trim()}
                    >
                      <Search />
                    </IconButton>
                  </InputAdornment>
                ),
                endAdornment: searchQuery && (
                  <InputAdornment position="end">
                    <IconButton
                      size="small"
                      onClick={handleSearchClear}
                    >
                      <Clear />
                    </IconButton>
                  </InputAdornment>
                ),
              }}
            />
            
            {/* Search Results Dropdown */}
            <Popper 
              open={showResults && searchResults.length > 0} 
              anchorEl={searchAnchorEl}
              placement="bottom-start"
              style={{ zIndex: 1300, width: searchAnchorEl?.offsetWidth || 350 }}
            >
              <Paper elevation={8} sx={{ maxHeight: 400, overflow: 'auto' }}>
                <List dense>
                  {searchResults.map((result, index) => (
                    <ListItem
                      key={`${result.node_id}-${index}`}
                      onClick={() => handleResultClick(result)}
                      sx={{
                        borderBottom: '1px solid #f0f0f0',
                        cursor: 'pointer',
                        '&:hover': { backgroundColor: '#f5f5f5' }
                      }}
                    >
                      <ListItemText
                        primary={
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            <Chip
                              label={result.code}
                              size="small"
                              color="primary"
                              variant="outlined"
                            />
                            <Typography variant="body2" sx={{ fontWeight: 500 }}>
                              {result.name}
                            </Typography>
                            {result.similarity_score && (
                              <Chip
                                label={`${(result.similarity_score * 100).toFixed(1)}%`}
                                size="small"
                                color="success"
                                sx={{ ml: 'auto', fontSize: '0.7rem' }}
                              />
                            )}
                          </Box>
                        }
                        secondary={
                          <Typography variant="caption" color="text.secondary">
                            {result.description?.length > 100 
                              ? `${result.description.substring(0, 100)}...`
                              : result.description
                            }
                          </Typography>
                        }
                      />
                    </ListItem>
                  ))}
                </List>
              </Paper>
            </Popper>
          </Box>
        </ClickAwayListener>

        {/* Model Dropdown */}
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