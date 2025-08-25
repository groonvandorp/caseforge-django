import React, { useState, useEffect } from 'react';
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
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
} from '@mui/material';
import {
  Visibility,
  GetApp,
  Delete,
  Star,
} from '@mui/icons-material';
import { ProcessModel, NodeDocument } from '../types';
import { apiService } from '../services/api';

const Dashboard: React.FC = () => {
  const [models, setModels] = useState<ProcessModel[]>([]);
  const [selectedModel, setSelectedModel] = useState<string>('');
  const [specifications, setSpecifications] = useState<NodeDocument[]>([]);
  const [recentProcessDetails, setRecentProcessDetails] = useState<NodeDocument[]>([]);
  const [bookmarkCounts, setBookmarkCounts] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadModels();
  }, []);

  useEffect(() => {
    if (selectedModel) {
      loadDashboardData();
    }
  }, [selectedModel]);

  const loadModels = async () => {
    try {
      console.log('Loading models...');
      const modelsData = await apiService.getModels();
      console.log('Models data received:', modelsData);
      setModels(modelsData);
      if (modelsData.length > 0) {
        setSelectedModel(modelsData[0].model_key);
      }
    } catch (error) {
      console.error('Failed to load models:', error);
    }
  };

  const loadDashboardData = async () => {
    if (!selectedModel) return;
    
    try {
      setLoading(true);
      const [specsData, processDetailsData, bookmarkCountsData] = await Promise.all([
        apiService.getDashboardSpecs(selectedModel),
        apiService.api.get('/documents/', { params: { model_key: selectedModel, document_type: 'process_details' } }).then(res => res.data.results || res.data),
        apiService.getBookmarkCounts(selectedModel),
      ]);
      
      setSpecifications(specsData);
      setRecentProcessDetails(processDetailsData.slice(0, 10)); // Show only recent 10
      setBookmarkCounts(bookmarkCountsData);
    } catch (error) {
      console.error('Failed to load dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleModelChange = (event: any) => {
    setSelectedModel(event.target.value);
  };

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

  return (
    <Container maxWidth="xl">
      <Box sx={{ mb: 3 }}>
        <Typography variant="h4" gutterBottom>
          Dashboard
        </Typography>
        
        <FormControl sx={{ minWidth: 300, mb: 3 }}>
          <InputLabel>Process Model</InputLabel>
          <Select
            value={selectedModel}
            onChange={handleModelChange}
            label="Process Model"
          >
            {models.map((model) => (
              <MenuItem key={model.id} value={model.model_key}>
                {model.name}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
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
                      <TableCell>Title</TableCell>
                      <TableCell>Process</TableCell>
                      <TableCell>Generated</TableCell>
                      <TableCell>Actions</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {recentProcessDetails.map((doc) => (
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
                      <TableCell>Title</TableCell>
                      <TableCell>Process</TableCell>
                      <TableCell>Created</TableCell>
                      <TableCell>Actions</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {specifications.map((spec) => (
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
            
            {Object.keys(bookmarkCounts).length === 0 ? (
              <Typography color="text.secondary">
                No bookmarked processes. Add bookmarks in the Composer tab.
              </Typography>
            ) : (
              <Box>
                {Object.entries(bookmarkCounts).map(([code, count]) => (
                  <Card key={code} sx={{ mb: 1, cursor: 'pointer' }} elevation={1}>
                    <CardContent sx={{ py: 1 }}>
                      <Box sx={{ display: 'flex', alignItems: 'center' }}>
                        <Star color="primary" sx={{ mr: 1 }} />
                        <Typography variant="body2" sx={{ flexGrow: 1 }}>
                          {code}
                        </Typography>
                        <Chip
                          size="small"
                          label={count}
                          color="primary"
                          variant="outlined"
                        />
                      </Box>
                    </CardContent>
                  </Card>
                ))}
              </Box>
            )}
          </Paper>
        </Box>
      </Box>
    </Container>
  );
};

export default Dashboard;