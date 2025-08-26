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
} from '@mui/material';
import {
  Visibility,
  GetApp,
  Delete,
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
  const [loading, setLoading] = useState(true);
  const [dashboardStats, setDashboardStats] = useState({
    totalUsecaseCandidates: 0,
    totalUsecaseSpecs: 0,
    totalDetailedProcesses: 0,
    statsLoading: true
  });

  const loadDashboardData = useCallback(async () => {
    if (!appState.selectedModelKey) return;
    
    try {
      setLoading(true);
      // Reset stats to loading state immediately
      setDashboardStats({
        totalUsecaseCandidates: 0,
        totalUsecaseSpecs: 0,
        totalDetailedProcesses: 0,
        statsLoading: true
      });
      
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

      // Load bookmarks
      try {
        const bookmarks = await apiService.getBookmarks();
        const bookmarkedProcessDetails: Record<string, ProcessNode> = {};
        const bookmarkCreatedDates: Record<string, string> = {};
        
        bookmarks.forEach((bookmark) => {
          const processNode: ProcessNode = {
            id: bookmark.node,
            code: bookmark.node_code,
            name: bookmark.node_name,
            level: 0,
            is_leaf: true,
            children_count: 0,
            model_version: 0 as any,
            parent: undefined,
            description: undefined,
          };
          bookmarkedProcessDetails[bookmark.node_code] = processNode;
          bookmarkCreatedDates[bookmark.node_code] = bookmark.created_at;
        });
        
        setBookmarkedProcesses(bookmarkedProcessDetails);
        setBookmarkDates(bookmarkCreatedDates);
      } catch (error: any) {
        console.error('Failed to load bookmarks:', error.response?.status, error.response?.data);
        setBookmarkedProcesses({});
        setBookmarkDates({});
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
  }, [appState.selectedModelKey, loadDashboardData]);

  const handleViewSpec = (spec: NodeDocument) => {
    window.open(`/viewer?docId=${spec.id}`, '_blank');
  };

  const handleViewProcessDetails = (doc: NodeDocument) => {
    window.open(`/viewer?docId=${doc.id}`, '_blank');
  };

  const handleDownloadSpec = async (spec: NodeDocument) => {
    try {
      const response = await apiService.api.get(`/documents/${spec.id}/download/`, {
        responseType: 'blob'
      });
      
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
    const process = bookmarkedProcesses[processCode];
    if (process) {
      navigate(`/composer?nodeId=${process.id}`);
    } else {
      navigate(`/composer?processCode=${processCode}`);
    }
  };

  const handleDeleteBookmark = async (processCode: string) => {
    const process = bookmarkedProcesses[processCode];
    if (!process) return;

    if (window.confirm(`Are you sure you want to remove the bookmark for process ${processCode}?`)) {
      try {
        await apiService.toggleBookmark(process.id);
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
      } catch (error) {
        console.error('Failed to delete bookmark:', error);
        alert('Failed to remove bookmark. Please try again.');
      }
    }
  };

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

      {/* Recently Generated Process Details Table */}
      <Box sx={{ mb: 4 }}>
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom>
            Recently Generated Process Details ({recentProcessDetails.length})
          </Typography>
          {loading ? (
            <Typography>Loading...</Typography>
          ) : recentProcessDetails.length === 0 ? (
            <Typography color="text.secondary">No process details found.</Typography>
          ) : (
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Title</TableCell>
                    <TableCell>Process Code</TableCell>
                    <TableCell>Created</TableCell>
                    <TableCell align="right">Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {recentProcessDetails.map((doc) => (
                    <TableRow key={doc.id}>
                      <TableCell>{doc.title}</TableCell>
                      <TableCell>{doc.node_code}</TableCell>
                      <TableCell>{new Date(doc.created_at).toLocaleDateString()}</TableCell>
                      <TableCell align="right">
                        <Button
                          size="small"
                          startIcon={<Visibility />}
                          onClick={() => handleViewProcessDetails(doc)}
                        >
                          View
                        </Button>
                        <Button
                          size="small"
                          startIcon={<GetApp />}
                          onClick={() => handleDownloadProcessDetails(doc)}
                          sx={{ ml: 1 }}
                        >
                          Download
                        </Button>
                        <Button
                          size="small"
                          startIcon={<Delete />}
                          onClick={() => handleDeleteProcessDetails(doc)}
                          color="error"
                          sx={{ ml: 1 }}
                        >
                          Delete
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </Paper>
      </Box>

      <Box sx={{ display: 'flex', gap: 3, flexWrap: 'wrap' }}>
        {/* Use Case Specifications Table */}
        <Paper sx={{ p: 3, flex: 1, minWidth: 0 }}>
          <Typography variant="h6" gutterBottom>
            Saved Use Case Specifications ({specifications.length})
          </Typography>
          {loading ? (
            <Typography>Loading...</Typography>
          ) : specifications.length === 0 ? (
            <Typography color="text.secondary">No specifications found.</Typography>
          ) : (
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Title</TableCell>
                    <TableCell>Process Code</TableCell>
                    <TableCell align="right">Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {specifications.map((spec) => (
                    <TableRow key={spec.id}>
                      <TableCell sx={{ maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {spec.title}
                      </TableCell>
                      <TableCell>{spec.node_code}</TableCell>
                      <TableCell align="right">
                        <Button
                          size="small"
                          startIcon={<Visibility />}
                          onClick={() => handleViewSpec(spec)}
                          sx={{ minWidth: 'auto', p: 0.5 }}
                        >
                          View
                        </Button>
                        <Button
                          size="small"
                          startIcon={<GetApp />}
                          onClick={() => handleDownloadSpec(spec)}
                          sx={{ ml: 0.5, minWidth: 'auto', p: 0.5 }}
                        >
                          Download
                        </Button>
                        <Button
                          size="small"
                          startIcon={<Delete />}
                          onClick={() => handleDeleteSpec(spec)}
                          color="error"
                          sx={{ ml: 0.5, minWidth: 'auto', p: 0.5 }}
                        >
                          Delete
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </Paper>

        {/* Bookmarked Processes Table */}
        <Paper sx={{ p: 3, flex: 1, minWidth: 0 }}>
          <Typography variant="h6" gutterBottom>
            Bookmarked Processes ({Object.keys(bookmarkedProcesses).length})
          </Typography>
          {Object.keys(bookmarkedProcesses).length === 0 ? (
            <Typography color="text.secondary">No bookmarked processes.</Typography>
          ) : (
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Process Code</TableCell>
                    <TableCell>Name</TableCell>
                    <TableCell align="right">Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {Object.entries(bookmarkedProcesses).map(([code, process]) => (
                    <TableRow key={code}>
                      <TableCell>{code}</TableCell>
                      <TableCell sx={{ maxWidth: 150, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {process.name}
                      </TableCell>
                      <TableCell align="right">
                        <Button
                          size="small"
                          onClick={() => handleOpenInComposer(code)}
                          sx={{ minWidth: 'auto', p: 0.5 }}
                        >
                          Open
                        </Button>
                        <Button
                          size="small"
                          startIcon={<Delete />}
                          onClick={() => handleDeleteBookmark(code)}
                          color="error"
                          sx={{ ml: 0.5, minWidth: 'auto', p: 0.5 }}
                        >
                          Remove
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </Paper>
      </Box>
    </Container>
  );
};

export default Dashboard;