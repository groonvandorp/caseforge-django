import React, { useState, useEffect } from 'react';
import {
  Container,
  Grid,
  Paper,
  Typography,
  Box,
  Button,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Card,
  CardContent,
  CardActions,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Chip,
  CircularProgress,
} from '@mui/material';
import {
  ExpandMore,
  Psychology,
  AutoAwesome,
  Visibility,
  Delete,
} from '@mui/icons-material';
import ProcessTree from '../components/Process/ProcessTree';
import { ProcessModel, ProcessNode, NodeDocument, NodeUsecaseCandidate } from '../types';
import { apiService } from '../services/api';

const Composer: React.FC = () => {
  const [models, setModels] = useState<ProcessModel[]>([]);
  const [selectedModel, setSelectedModel] = useState<string>('');
  const [selectedNode, setSelectedNode] = useState<ProcessNode | null>(null);
  const [processDetails, setProcessDetails] = useState<NodeDocument | null>(null);
  const [usecaseCandidates, setUsecaseCandidates] = useState<NodeUsecaseCandidate[]>([]);
  const [loadingDetails, setLoadingDetails] = useState(false);
  const [loadingUsecases, setLoadingUsecases] = useState(false);

  useEffect(() => {
    loadModels();
  }, []);

  useEffect(() => {
    if (selectedNode) {
      loadNodeData();
    }
  }, [selectedNode]);

  const loadModels = async () => {
    try {
      const modelsData = await apiService.getModels();
      setModels(modelsData);
      if (modelsData.length > 0) {
        setSelectedModel(modelsData[0].model_key);
      }
    } catch (error) {
      console.error('Failed to load models:', error);
    }
  };

  const loadNodeData = async () => {
    if (!selectedNode) return;

    try {
      const [detailsData, usecasesData] = await Promise.all([
        apiService.getDocumentsByNode(selectedNode.id, 'process_details'),
        apiService.getUsecasesByNode(selectedNode.id),
      ]);

      setProcessDetails(detailsData.length > 0 ? detailsData[0] : null);
      setUsecaseCandidates(usecasesData);
    } catch (error) {
      console.error('Failed to load node data:', error);
    }
  };

  const handleModelChange = (event: any) => {
    setSelectedModel(event.target.value);
    setSelectedNode(null);
    setProcessDetails(null);
    setUsecaseCandidates([]);
  };

  const handleNodeSelect = (node: ProcessNode) => {
    setSelectedNode(node);
  };

  const handleGenerateDetails = async () => {
    if (!selectedNode) return;

    setLoadingDetails(true);
    try {
      // TODO: Implement AI generation endpoint
      console.log('Generate process details for:', selectedNode.code);
      // For now, create a mock document
      const mockDocument: NodeDocument = {
        id: Date.now(),
        node: selectedNode.id,
        node_code: selectedNode.code,
        node_name: selectedNode.name,
        document_type: 'process_details',
        title: `Process Details: ${selectedNode.name}`,
        content: `Generated process details for ${selectedNode.code}`,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };
      setProcessDetails(mockDocument);
    } catch (error) {
      console.error('Failed to generate process details:', error);
    } finally {
      setLoadingDetails(false);
    }
  };

  const handleGenerateUsecases = async () => {
    if (!selectedNode) return;

    setLoadingUsecases(true);
    try {
      // TODO: Implement AI generation endpoint
      console.log('Generate use cases for:', selectedNode.code);
      // For now, create mock candidates
      const mockCandidates: NodeUsecaseCandidate[] = [
        {
          id: Date.now(),
          node: selectedNode.id,
          node_code: selectedNode.code,
          node_name: selectedNode.name,
          candidate_uid: `uc-${Date.now()}`,
          title: 'AI-Powered Process Automation',
          description: 'Implement intelligent automation to streamline this process',
          impact_assessment: 'High impact - 40% efficiency gain expected',
          complexity_score: 7,
          created_at: new Date().toISOString(),
        },
      ];
      setUsecaseCandidates(prev => [...prev, ...mockCandidates]);
    } catch (error) {
      console.error('Failed to generate use cases:', error);
    } finally {
      setLoadingUsecases(false);
    }
  };

  const handleGenerateSpec = async (candidate: NodeUsecaseCandidate) => {
    try {
      // TODO: Implement specification generation
      console.log('Generate specification for:', candidate.title);
    } catch (error) {
      console.error('Failed to generate specification:', error);
    }
  };

  const handleDeleteCandidate = async (candidate: NodeUsecaseCandidate) => {
    if (window.confirm('Are you sure you want to delete this use case candidate?')) {
      try {
        await apiService.api.delete(`/usecases/${candidate.id}/`);
        setUsecaseCandidates(prev => prev.filter(uc => uc.id !== candidate.id));
      } catch (error) {
        console.error('Failed to delete candidate:', error);
      }
    }
  };

  return (
    <Container maxWidth="xl">
      <Box sx={{ mb: 3 }}>
        <Typography variant="h4" gutterBottom>
          AI Use Case Composer
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

      <Grid container spacing={3}>
        {/* Process Tree */}
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 2, height: 600 }}>
            <Typography variant="h6" gutterBottom>
              Process Hierarchy
            </Typography>
            {selectedModel && (
              <ProcessTree
                modelKey={selectedModel}
                onNodeSelect={handleNodeSelect}
                selectedNodeId={selectedNode?.id}
              />
            )}
          </Paper>
        </Grid>

        {/* Main Content */}
        <Grid item xs={12} md={8}>
          {!selectedNode ? (
            <Paper sx={{ p: 4, textAlign: 'center', height: 600 }}>
              <Typography variant="h6" color="text.secondary">
                Select a process from the tree to get started
              </Typography>
            </Paper>
          ) : (
            <Box>
              {/* Selected Process Info */}
              <Paper sx={{ p: 3, mb: 2 }}>
                <Typography variant="h6" gutterBottom>
                  {selectedNode.code}: {selectedNode.name}
                </Typography>
                {selectedNode.description && (
                  <Typography variant="body2" color="text.secondary">
                    {selectedNode.description}
                  </Typography>
                )}
                
                <Box sx={{ mt: 2, display: 'flex', gap: 2 }}>
                  <Button
                    variant="contained"
                    startIcon={loadingDetails ? <CircularProgress size={16} /> : <Psychology />}
                    onClick={handleGenerateDetails}
                    disabled={loadingDetails}
                  >
                    Generate Process Details
                  </Button>
                  <Button
                    variant="contained"
                    color="secondary"
                    startIcon={loadingUsecases ? <CircularProgress size={16} /> : <AutoAwesome />}
                    onClick={handleGenerateUsecases}
                    disabled={loadingUsecases}
                  >
                    Generate AI Use Cases
                  </Button>
                </Box>
              </Paper>

              {/* Process Details */}
              {processDetails && (
                <Paper sx={{ p: 3, mb: 2 }}>
                  <Typography variant="h6" gutterBottom>
                    Saved Process Details
                  </Typography>
                  <Card>
                    <CardContent>
                      <Typography variant="body1">
                        {processDetails.content}
                      </Typography>
                    </CardContent>
                  </Card>
                </Paper>
              )}

              {/* Use Case Candidates */}
              {usecaseCandidates.length > 0 && (
                <Paper sx={{ p: 3 }}>
                  <Typography variant="h6" gutterBottom>
                    AI Use Case Candidates
                  </Typography>
                  
                  {usecaseCandidates.map((candidate, index) => (
                    <Accordion key={candidate.id} sx={{ mb: 1 }}>
                      <AccordionSummary expandIcon={<ExpandMore />}>
                        <Box sx={{ display: 'flex', alignItems: 'center', width: '100%' }}>
                          <Typography sx={{ flexGrow: 1 }}>
                            {candidate.title}
                          </Typography>
                          {candidate.complexity_score && (
                            <Chip
                              label={`Complexity: ${candidate.complexity_score}/10`}
                              size="small"
                              color={candidate.complexity_score <= 3 ? 'success' : 
                                     candidate.complexity_score <= 7 ? 'warning' : 'error'}
                              sx={{ mr: 2 }}
                            />
                          )}
                        </Box>
                      </AccordionSummary>
                      <AccordionDetails>
                        <Typography variant="body2" paragraph>
                          {candidate.description}
                        </Typography>
                        {candidate.impact_assessment && (
                          <Typography variant="body2" color="text.secondary" paragraph>
                            <strong>Impact:</strong> {candidate.impact_assessment}
                          </Typography>
                        )}
                        
                        <Box sx={{ display: 'flex', gap: 1, mt: 2 }}>
                          <Button
                            size="small"
                            variant="contained"
                            startIcon={<Visibility />}
                            onClick={() => handleGenerateSpec(candidate)}
                          >
                            Generate Specification
                          </Button>
                          <Button
                            size="small"
                            color="error"
                            startIcon={<Delete />}
                            onClick={() => handleDeleteCandidate(candidate)}
                          >
                            Delete
                          </Button>
                        </Box>
                      </AccordionDetails>
                    </Accordion>
                  ))}
                </Paper>
              )}
            </Box>
          )}
        </Grid>
      </Grid>
    </Container>
  );
};

export default Composer;