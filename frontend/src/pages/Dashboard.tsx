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
      const [specsData, bookmarkCountsData] = await Promise.all([
        apiService.getDashboardSpecs(selectedModel),
        apiService.getBookmarkCounts(selectedModel),
      ]);
      
      setSpecifications(specsData);
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

  const handleDownloadSpec = async (spec: NodeDocument) => {
    try {
      // TODO: Implement DOCX export
      console.log('Download spec:', spec.id);
    } catch (error) {
      console.error('Failed to download spec:', error);
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