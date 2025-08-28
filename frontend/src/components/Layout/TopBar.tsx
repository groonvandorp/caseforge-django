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
  ToggleButton,
  ToggleButtonGroup,
} from '@mui/material';
import { Search, Clear } from '@mui/icons-material';
import { useAppState } from '../../contexts/AppStateContext';
import { apiService } from '../../services/api';
import { useNavigate } from 'react-router-dom';

const TopBar: React.FC = () => {
  const { state: appState, setSelectedModel } = useAppState();
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState('');
  const [searchScope, setSearchScope] = useState<'processes' | 'usecases' | 'all'>('all');
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

  const handleScopeChange = (event: React.MouseEvent<HTMLElement>, newScope: 'processes' | 'usecases' | 'all' | null) => {
    if (newScope !== null) {
      setSearchScope(newScope);
      // Clear existing results when scope changes
      setSearchResults([]);
      setShowResults(false);
    }
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
        scope: searchScope,
        search_type: 'hybrid',
        limit: 10,
        min_similarity: 0.3
      });
      
      console.log('🔍 Search API response:', response);
      
      // Normalize results from both old and new API formats
      let normalizedResults: any[] = [];
      
      if (response.results) {
        // Legacy format - convert to new format for display
        normalizedResults = response.results.map(result => ({
          ...result,
          id: result.node_id,
          node_id: result.node_id, // Ensure node_id is preserved for navigation
          similarity: result.similarity_score,
          type: 'process'
        }));
      } else if (response.processes || response.usecases) {
        // New scoped format
        const processResults = (response.processes || []).map(p => {
          const process = p as any; // Type assertion for actual API structure
          return {
            node_id: process.node_id || process.id,
            id: process.node_id || process.id,
            code: process.code,
            name: process.name,
            description: process.description,
            level: process.level,
            similarity: process.similarity_score || process.similarity,
            similarity_score: process.similarity_score || process.similarity,
            type: 'process',
            parent_name: process.parent_name,
            is_leaf: process.is_leaf
          };
        });
        
        const usecaseResults = (response.usecases || []).map(uc => ({
          node_id: uc.node_id,
          id: uc.id,
          code: uc.node_code,
          name: uc.title,
          description: uc.description,
          level: 0, // Use cases don't have levels
          similarity: uc.similarity,
          similarity_score: uc.similarity,
          type: 'usecase',
          parent_name: uc.node_name,
          candidate_uid: uc.candidate_uid,
          impact_assessment: uc.impact_assessment,
          complexity_score: uc.complexity_score,
          category: uc.category,
          estimated_roi: uc.estimated_roi,
          risk_level: uc.risk_level
        }));
        
        normalizedResults = [...processResults, ...usecaseResults];
      }
      
      setSearchResults(normalizedResults);
      setShowResults(true);
      
      if (normalizedResults.length > 0) {
        const totalCount = response.total_count || response.total_results || normalizedResults.length;
        const searchType = response.search_type || 'enhanced';
        console.log(`🔍 ✅ Found ${totalCount} results (${searchType}):`);
        normalizedResults.forEach((result, index) => {
          const prefix = result.type === 'usecase' ? '💡' : '📋';
          console.log(`  ${index + 1}. ${prefix} [${result.code}] ${result.name} (similarity: ${result.similarity || result.similarity_score || 'N/A'})`);
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
    
    // Hide search results
    setShowResults(false);
    
    if (result.type === 'usecase') {
      console.log('🔍 Use case selected - navigating to parent process with use case highlight');
      console.log('🔍 Use case ID:', result.id, 'Parent Node ID:', result.node_id);
      
      // Navigate to Composer page with parent node ID and use case highlight
      navigate(`/composer?nodeId=${result.node_id}&usecaseId=${result.id}`);
    } else {
      console.log('🔍 Process selected - navigating to Composer with node ID:', result.node_id);
      
      // Navigate to Composer page with nodeId parameter
      navigate(`/composer?nodeId=${result.node_id}`);
    }
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
        
        {/* Search Scope Selector */}
        <Box sx={{ mr: 1 }}>
          <ToggleButtonGroup
            value={searchScope}
            exclusive
            onChange={handleScopeChange}
            size="small"
            sx={{ height: 40 }}
          >
            <ToggleButton value="processes" sx={{ px: 2, fontSize: '0.75rem' }}>
              Processes
            </ToggleButton>
            <ToggleButton value="usecases" sx={{ px: 2, fontSize: '0.75rem' }}>
              AI Use Cases
            </ToggleButton>
            <ToggleButton value="all" sx={{ px: 2, fontSize: '0.75rem' }}>
              All
            </ToggleButton>
          </ToggleButtonGroup>
        </Box>

        {/* Search Input */}
        <ClickAwayListener onClickAway={handleClickAway}>
          <Box sx={{ minWidth: 350, mr: 2, position: 'relative' }}>
            <TextField
              size="small"
              fullWidth
              placeholder={
                searchScope === 'processes' 
                  ? "Search processes..." 
                  : searchScope === 'usecases'
                  ? "Search AI use cases..."
                  : "Search processes and use cases..."
              }
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
                              label={result.type === 'usecase' ? '💡' : result.code}
                              size="small"
                              color={result.type === 'usecase' ? 'secondary' : 'primary'}
                              variant={result.type === 'usecase' ? 'filled' : 'outlined'}
                            />
                            <Typography variant="body2" sx={{ fontWeight: 500 }}>
                              {result.name}
                            </Typography>
                            {result.type === 'usecase' && result.category && (
                              <Chip
                                label={result.category}
                                size="small"
                                color="info"
                                variant="outlined"
                                sx={{ fontSize: '0.6rem' }}
                              />
                            )}
                            {(result.similarity_score || result.similarity) && (
                              <Chip
                                label={`${((result.similarity || result.similarity_score) * 100).toFixed(1)}%`}
                                size="small"
                                color="success"
                                sx={{ ml: 'auto', fontSize: '0.7rem' }}
                              />
                            )}
                          </Box>
                        }
                        secondary={
                          <Box>
                            <Typography variant="caption" color="text.secondary">
                              {result.description?.length > 100 
                                ? `${result.description.substring(0, 100)}...`
                                : result.description
                              }
                            </Typography>
                            {result.type === 'usecase' && result.parent_name && (
                              <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.5 }}>
                                📋 Process: {result.parent_name}
                              </Typography>
                            )}
                          </Box>
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
              {appState.models
                .sort((a, b) => a.name.localeCompare(b.name))
                .map((model) => (
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