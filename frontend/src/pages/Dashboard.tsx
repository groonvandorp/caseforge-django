import React, { useState, useEffect, useCallback } from 'react';
import {
  Container,
  Paper,
  Typography,
  Box,
  Card,
  CardContent,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TableSortLabel,
  Chip,
  IconButton,
  Tooltip,
} from '@mui/material';
import {
  Visibility,
  GetApp,
  Delete,
  Star,
  Launch,
  AutoAwesome,
  HourglassEmpty,
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { NodeDocument, ProcessNode } from '../types';
import { apiService } from '../services/api';
import { useAppState } from '../contexts/AppStateContext';

const Dashboard: React.FC = () => {
  const { state: appState } = useAppState();
  const navigate = useNavigate();
  const [specifications, setSpecifications] = useState<NodeDocument[]>([]);
  const [recentProcessDetails, setRecentProcessDetails] = useState<NodeDocument[]>([]);
  const [bookmarkedProcesses, setBookmarkedProcesses] = useState<Record<string, ProcessNode>>({});
  const [bookmarkDates, setBookmarkDates] = useState<Record<string, string>>({});
  const [usecaseCounts, setUsecaseCounts] = useState<Record<number, number>>({});
  const [usecaseCountsLoading, setUsecaseCountsLoading] = useState(false);
  const [loading, setLoading] = useState(true);
  const [dashboardStats, setDashboardStats] = useState({
    totalUsecaseCandidates: 0,
    totalUsecaseSpecs: 0,
    totalDetailedProcesses: 0,
    statsLoading: true
  });

  // Sorting state
  const [processDetailsSort, setProcessDetailsSort] = useState<{ field: string; direction: 'asc' | 'desc' }>({ field: 'created_at', direction: 'desc' });
  const [specificationsSort, setSpecificationsSort] = useState<{ field: string; direction: 'asc' | 'desc' }>({ field: 'created_at', direction: 'desc' });
  const [bookmarksSort, setBookmarksSort] = useState<{ field: string; direction: 'asc' | 'desc' }>({ field: 'code', direction: 'asc' });


  const loadDashboardData = useCallback(async () => {
    if (!appState.selectedModelKey) return;
    
    try {
      setLoading(true);
      const [specsData, processDetailsData, statsData] = await Promise.all([
        apiService.getDashboardSpecs(appState.selectedModelKey),
        apiService.api.get('/documents/', { params: { model_key: appState.selectedModelKey, document_type: 'process_details' } }).then(res => res.data.results || res.data),
        apiService.getDashboardStats(appState.selectedModelKey)
      ]);
      
      setSpecifications(specsData);
      setRecentProcessDetails(processDetailsData.slice(0, 10)); // Show only recent 10
      setDashboardStats({
        ...statsData,
        statsLoading: false
      });

      // Load full bookmark details instead of using counts + separate API calls
      const bookmarkedProcessDetails: Record<string, ProcessNode> = {};
      const bookmarkCreatedDates: Record<string, string> = {};
      
      try {
        console.log('Loading bookmarks directly from bookmark API...');
        const bookmarks = await apiService.getBookmarks();
        console.log('Successfully loaded bookmarks:', bookmarks);
        
        // Build process details map from bookmark data (already includes code and name)
        bookmarks.forEach((bookmark) => {
          // Create a simplified ProcessNode object from bookmark data
          const processNode: ProcessNode = {
            id: bookmark.node,
            code: bookmark.node_code,
            name: bookmark.node_name,
            // Add minimal required fields - we mainly need code and name for display
            level: 0,
            is_leaf: true,
            children_count: 0,
            model_version: 0 as any, // These aren't needed for bookmark display
            parent: undefined,
            description: undefined,
          };
          bookmarkedProcessDetails[bookmark.node_code] = processNode;
          bookmarkCreatedDates[bookmark.node_code] = bookmark.created_at;
        });
        
        setBookmarkedProcesses(bookmarkedProcessDetails);
        setBookmarkDates(bookmarkCreatedDates);
        
        // Load usecase counts for the bookmarked processes in the background
        if (bookmarks.length > 0) {
          setUsecaseCountsLoading(true);
          // Load usecase counts asynchronously without blocking the main UI
          setTimeout(async () => {
            try {
              const nodeIds = bookmarks.map(b => b.node);
              console.log('Loading usecase counts for node IDs:', nodeIds);
              const counts = await apiService.getUsecaseCounts(nodeIds);
              console.log('Successfully loaded usecase counts:', counts);
              setUsecaseCounts(counts);
            } catch (error: any) {
              console.error('Failed to load usecase counts:', error);
              setUsecaseCounts({});
            } finally {
              setUsecaseCountsLoading(false);
            }
          }, 100); // Small delay to let the main UI render first
        } else {
          setUsecaseCounts({});
          setUsecaseCountsLoading(false);
        }
        
      } catch (error: any) {
        console.error('Failed to load bookmarks:', error.response?.status, error.response?.data);
        // Fallback: keep the existing empty state
        setBookmarkedProcesses({});
        setBookmarkDates({});
        setUsecaseCounts({});
      }
    } catch (error) {
      console.error('Failed to load dashboard data:', error);
      setDashboardStats(prev => ({ ...prev, statsLoading: false }));
    } finally {
      setLoading(false);
    }
  }, [appState.selectedModelKey]);

  useEffect(() => {
    if (appState.selectedModelKey) {
      loadDashboardData();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [appState.selectedModelKey]);


  const handleViewSpec = (spec: NodeDocument) => {
    // Navigate to viewer with spec ID
    window.open(`/viewer?docId=${spec.id}`, '_blank');
  };

  const handleViewProcessDetails = (doc: NodeDocument) => {
    // Navigate to viewer with document ID
    window.open(`/viewer?docId=${doc.id}`, '_blank');
  };

  const handleDownloadSpec = async (spec: NodeDocument) => {
    try {
      // TODO: Implement DOCX export
      console.log('Download spec:', spec.id);
      const response = await apiService.api.get(`/documents/${spec.id}/download/`, {
        responseType: 'blob'
      });
      
      // Create blob link and download
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `${spec.title || 'document'}.docx`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (error) {
      console.error('Failed to download spec:', error);
      alert('Download failed. The export feature may not be implemented yet.');
    }
  };

  const handleDownloadProcessDetails = async (doc: NodeDocument) => {
    try {
      const response = await apiService.api.get(`/documents/${doc.id}/download/`, {
        responseType: 'blob'
      });
      
      // Create blob link and download
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `${doc.title || 'process-details'}.docx`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (error) {
      console.error('Failed to download document:', error);
      alert('Download failed. The export feature may not be implemented yet.');
    }
  };

  const handleDeleteSpec = async (spec: NodeDocument) => {
    if (window.confirm('Are you sure you want to delete this specification?')) {
      try {
        await apiService.api.delete(`/documents/${spec.id}/`);
        setSpecifications(specs => specs.filter(s => s.id !== spec.id));
      } catch (error) {
        console.error('Failed to delete spec:', error);
      }
    }
  };

  const handleDeleteProcessDetails = async (doc: NodeDocument) => {
    if (window.confirm('Are you sure you want to delete this process details document?')) {
      try {
        await apiService.api.delete(`/documents/${doc.id}/`);
        setRecentProcessDetails(docs => docs.filter(d => d.id !== doc.id));
      } catch (error) {
        console.error('Failed to delete document:', error);
      }
    }
  };

  const handleOpenInComposer = (processCode: string) => {
    console.log('Navigating to Composer with process code:', processCode);
    const process = bookmarkedProcesses[processCode];
    if (process) {
      // Navigate to Composer with the node ID instead of code (more reliable)
      navigate(`/composer?nodeId=${process.id}`);
    } else {
      // Fallback to code-based navigation
      navigate(`/composer?processCode=${processCode}`);
    }
  };

  const handleDeleteBookmark = async (processCode: string) => {
    const process = bookmarkedProcesses[processCode];
    if (!process) return;

    if (window.confirm(`Are you sure you want to remove the bookmark for process ${processCode}?`)) {
      try {
        await apiService.toggleBookmark(process.id);
        // Remove from local state
        setBookmarkedProcesses(prev => {
          const updated = { ...prev };
          delete updated[processCode];
          return updated;
        });
        setBookmarkDates(prev => {
          const updated = { ...prev };
          delete updated[processCode];
          return updated;
        });
        setUsecaseCounts(prev => {
          const updated = { ...prev };
          delete updated[process.id];
          return updated;
        });
      } catch (error) {
        console.error('Failed to delete bookmark:', error);
        alert('Failed to remove bookmark. Please try again.');
      }
    }
  };

  // Sorting helper functions
  const handleSort = (field: string, currentSort: { field: string; direction: 'asc' | 'desc' }, setSort: React.Dispatch<React.SetStateAction<{ field: string; direction: 'asc' | 'desc' }>>) => {
    const direction = currentSort.field === field && currentSort.direction === 'asc' ? 'desc' : 'asc';
    setSort({ field, direction });
  };

  const sortData = <T extends any>(data: T[], sortConfig: { field: string; direction: 'asc' | 'desc' }, getValue: (item: T) => any) => {
    return [...data].sort((a, b) => {
      const aVal = getValue(a);
      const bVal = getValue(b);
      
      if (aVal === bVal) return 0;
      
      const comparison = aVal < bVal ? -1 : 1;
      return sortConfig.direction === 'asc' ? comparison : -comparison;
    });
  };

  // Sort data arrays
  const sortedProcessDetails = sortData(recentProcessDetails, processDetailsSort, (doc) => {
    switch (processDetailsSort.field) {
      case 'title': return doc.title?.toLowerCase() || '';
      case 'process': return `${doc.node_code}: ${doc.node_name}`.toLowerCase();
      case 'created_at': return new Date(doc.created_at).getTime();
      default: return '';
    }
  });

  const sortedSpecifications = sortData(specifications, specificationsSort, (spec) => {
    switch (specificationsSort.field) {
      case 'title': return spec.title?.toLowerCase() || '';
      case 'process': return `${spec.node_code}: ${spec.node_name}`.toLowerCase();
      case 'created_at': return new Date(spec.created_at).getTime();
      default: return '';
    }
  });

  const sortedBookmarks = sortData(Object.keys(bookmarkedProcesses), bookmarksSort, (code) => {
    const process = bookmarkedProcesses[code];
    switch (bookmarksSort.field) {
      case 'process': return process ? `${code}: ${process.name}`.toLowerCase() : code.toLowerCase();
      case 'usecases': return process ? (usecaseCounts[process.id] || 0) : 0;
      case 'created_at': return bookmarkDates[code] ? new Date(bookmarkDates[code]).getTime() : 0;
      case 'code': 
      default: 
        // Natural sort for process codes like 1.1.1.1, 1.1.1.2, etc.
        return code.split('.').map(n => parseInt(n) || 0);
    }
  });

  return (
    <Container maxWidth="xl">
      <Box sx={{ mb: 3 }}>
        <Typography variant="h4" gutterBottom>
          Dashboard
        </Typography>
        
        {/* Stats Section */}
        <Box sx={{ display: 'flex', gap: 3, flexWrap: 'wrap', mb: 4 }}>
          <Box sx={{ flex: '1 1 300px' }}>
            <Card sx={{ textAlign: 'center', p: 2, background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', color: 'white' }}>
              <CardContent>
                <Typography variant="h3" sx={{ fontWeight: 'bold', mb: 1 }}>
                  {dashboardStats.statsLoading ? '...' : dashboardStats.totalUsecaseCandidates.toLocaleString()}
                </Typography>
                <Typography variant="h6">
                  AI Usecase Candidates
                </Typography>
              </CardContent>
            </Card>
          </Box>
          
          <Box sx={{ flex: '1 1 300px' }}>
            <Card sx={{ textAlign: 'center', p: 2, background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)', color: 'white' }}>
              <CardContent>
                <Typography variant="h3" sx={{ fontWeight: 'bold', mb: 1 }}>
                  {dashboardStats.statsLoading ? '...' : dashboardStats.totalUsecaseSpecs.toLocaleString()}
                </Typography>
                <Typography variant="h6">
                  AI Usecase Specs
                </Typography>
              </CardContent>
            </Card>
          </Box>
          
          <Box sx={{ flex: '1 1 300px' }}>
            <Card sx={{ textAlign: 'center', p: 2, background: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)', color: 'white' }}>
              <CardContent>
                <Typography variant="h3" sx={{ fontWeight: 'bold', mb: 1 }}>
                  {dashboardStats.statsLoading ? '...' : dashboardStats.totalDetailedProcesses.toLocaleString()}
                </Typography>
                <Typography variant="h6">
                  Detailed Processes
                </Typography>
              </CardContent>
            </Card>
          </Box>
        </Box>
      </Box>

      <Box sx={{ display: 'flex', gap: 3, flexWrap: 'wrap', mb: 4 }}>
        {/* Recently Generated Process Details */}
        <Box sx={{ flex: '1 1 100%', minWidth: 600 }}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Recently Generated Process Details
            </Typography>
            
            {loading ? (
              <Typography>Loading process details...</Typography>
            ) : recentProcessDetails.length === 0 ? (
              <Typography color="text.secondary">
                No process details found. Generate some using the "Generate Process Details" button in the Composer tab.
              </Typography>
            ) : (
              <TableContainer>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>
                        <TableSortLabel
                          active={processDetailsSort.field === 'title'}
                          direction={processDetailsSort.direction}
                          onClick={() => handleSort('title', processDetailsSort, setProcessDetailsSort)}
                        >
                          Title
                        </TableSortLabel>
                      </TableCell>
                      <TableCell>
                        <TableSortLabel
                          active={processDetailsSort.field === 'process'}
                          direction={processDetailsSort.direction}
                          onClick={() => handleSort('process', processDetailsSort, setProcessDetailsSort)}
                        >
                          Process
                        </TableSortLabel>
                      </TableCell>
                      <TableCell sx={{ width: 120 }}>
                        <TableSortLabel
                          active={processDetailsSort.field === 'created_at'}
                          direction={processDetailsSort.direction}
                          onClick={() => handleSort('created_at', processDetailsSort, setProcessDetailsSort)}
                        >
                          Generated
                        </TableSortLabel>
                      </TableCell>
                      <TableCell sx={{ width: 200 }}>Actions</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {sortedProcessDetails.map((doc) => (
                      <TableRow key={doc.id}>
                        <TableCell>
                          <Typography variant="body2" sx={{ fontWeight: 'medium' }}>
                            {doc.title}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2" color="text.secondary">
                            {doc.node_code}: {doc.node_name}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2" color="text.secondary">
                            {new Date(doc.created_at).toLocaleDateString()}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Box sx={{ display: 'flex', gap: 1 }}>
                            <Button
                              size="small"
                              startIcon={<Visibility />}
                              onClick={() => handleViewProcessDetails(doc)}
                            >
                              Open
                            </Button>
                            <Button
                              size="small"
                              startIcon={<GetApp />}
                              onClick={() => handleDownloadProcessDetails(doc)}
                            >
                              Download
                            </Button>
                            <Button
                              size="small"
                              color="error"
                              startIcon={<Delete />}
                              onClick={() => handleDeleteProcessDetails(doc)}
                            >
                              Delete
                            </Button>
                          </Box>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            )}
          </Paper>
        </Box>
      </Box>

      <Box sx={{ display: 'flex', gap: 3, flexWrap: 'wrap' }}>
        {/* Saved Specifications */}
        <Box sx={{ flex: '1 1 65%', minWidth: 600 }}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Saved Use Case Specifications
            </Typography>
            
            {loading ? (
              <Typography>Loading specifications...</Typography>
            ) : specifications.length === 0 ? (
              <Typography color="text.secondary">
                No specifications found. Create some in the Composer tab.
              </Typography>
            ) : (
              <TableContainer>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>
                        <TableSortLabel
                          active={specificationsSort.field === 'title'}
                          direction={specificationsSort.direction}
                          onClick={() => handleSort('title', specificationsSort, setSpecificationsSort)}
                        >
                          Title
                        </TableSortLabel>
                      </TableCell>
                      <TableCell>
                        <TableSortLabel
                          active={specificationsSort.field === 'process'}
                          direction={specificationsSort.direction}
                          onClick={() => handleSort('process', specificationsSort, setSpecificationsSort)}
                        >
                          Process
                        </TableSortLabel>
                      </TableCell>
                      <TableCell sx={{ width: 120 }}>
                        <TableSortLabel
                          active={specificationsSort.field === 'created_at'}
                          direction={specificationsSort.direction}
                          onClick={() => handleSort('created_at', specificationsSort, setSpecificationsSort)}
                        >
                          Created
                        </TableSortLabel>
                      </TableCell>
                      <TableCell sx={{ width: 200 }}>Actions</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {sortedSpecifications.map((spec) => (
                      <TableRow key={spec.id}>
                        <TableCell>
                          <Typography variant="body2" sx={{ fontWeight: 'medium' }}>
                            {spec.title}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2" color="text.secondary">
                            {spec.node_code}: {spec.node_name}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2" color="text.secondary">
                            {new Date(spec.created_at).toLocaleDateString()}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Box sx={{ display: 'flex', gap: 1 }}>
                            <Button
                              size="small"
                              startIcon={<Visibility />}
                              onClick={() => handleViewSpec(spec)}
                            >
                              Open
                            </Button>
                            <Button
                              size="small"
                              startIcon={<GetApp />}
                              onClick={() => handleDownloadSpec(spec)}
                            >
                              Download
                            </Button>
                            <Button
                              size="small"
                              color="error"
                              startIcon={<Delete />}
                              onClick={() => handleDeleteSpec(spec)}
                            >
                              Delete
                            </Button>
                          </Box>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            )}
          </Paper>
        </Box>

        {/* Bookmarked Processes */}
        <Box sx={{ flex: '1 1 35%', minWidth: 300 }}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Bookmarked Processes
            </Typography>
            
{Object.keys(bookmarkedProcesses).length === 0 ? (
              <Typography color="text.secondary">
                No bookmarked processes. Add bookmarks in the Composer tab.
              </Typography>
            ) : (
              <TableContainer>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>
                        <TableSortLabel
                          active={bookmarksSort.field === 'process'}
                          direction={bookmarksSort.direction}
                          onClick={() => handleSort('process', bookmarksSort, setBookmarksSort)}
                        >
                          Process
                        </TableSortLabel>
                      </TableCell>
                      <TableCell>
                        <TableSortLabel
                          active={bookmarksSort.field === 'usecases'}
                          direction={bookmarksSort.direction}
                          onClick={() => handleSort('usecases', bookmarksSort, setBookmarksSort)}
                        >
                          AI Use Cases
                        </TableSortLabel>
                      </TableCell>
                      <TableCell sx={{ width: 120 }}>
                        <TableSortLabel
                          active={bookmarksSort.field === 'created_at'}
                          direction={bookmarksSort.direction}
                          onClick={() => handleSort('created_at', bookmarksSort, setBookmarksSort)}
                        >
                          Created
                        </TableSortLabel>
                      </TableCell>
                      <TableCell sx={{ width: 200 }}>Actions</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {sortedBookmarks.map((code) => {
                      const process = bookmarkedProcesses[code];
                      const usecaseCount = process ? usecaseCounts[process.id] || 0 : 0;
                      const createdDate = bookmarkDates[code];
                      return (
                        <TableRow key={code}>
                          <TableCell>
                            <Typography variant="body2" sx={{ fontWeight: 'medium' }}>
                              {process ? `${code}: ${process.name}` : code}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Typography variant="body2" color="text.secondary">
                              {usecaseCountsLoading ? '...' : usecaseCount}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Typography variant="body2" color="text.secondary">
                              {createdDate ? new Date(createdDate).toLocaleDateString() : '--'}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Box sx={{ display: 'flex', gap: 1 }}>
                              <Button
                                size="small"
                                startIcon={<Visibility />}
                                onClick={() => handleOpenInComposer(code)}
                              >
                                Open
                              </Button>
                              <Button
                                size="small"
                                color="error"
                                startIcon={<Delete />}
                                onClick={() => handleDeleteBookmark(code)}
                              >
                                Delete
                              </Button>
                            </Box>
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </TableContainer>
            )}
          </Paper>
        </Box>
      </Box>
    </Container>
  );
};

export default Dashboard;