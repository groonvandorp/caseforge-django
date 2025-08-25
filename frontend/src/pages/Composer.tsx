import React, { useState, useEffect, useCallback } from 'react';
import {
  Container,
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
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Chip,
  CircularProgress,
  Divider,
} from '@mui/material';
import {
  ExpandMore,
  Psychology,
  AutoAwesome,
  Visibility,
  Delete,
  Description,
  CheckCircle,
} from '@mui/icons-material';
import ReactMarkdown from 'react-markdown';
import SimpleProcessTree from '../components/Process/SimpleProcessTree';
import { ProcessModel, ProcessNode, NodeDocument, NodeUsecaseCandidate } from '../types';
import { apiService } from '../services/api';

const Composer: React.FC = () => {
  const [models, setModels] = useState<ProcessModel[]>([]);
  const [selectedModel, setSelectedModel] = useState<string>('');
  const [selectedNode, setSelectedNode] = useState<ProcessNode | null>(null);
  const [processDetails, setProcessDetails] = useState<NodeDocument | null>(null);
  const [nodeDocuments, setNodeDocuments] = useState<NodeDocument[]>([]);
  const [usecaseCandidates, setUsecaseCandidates] = useState<NodeUsecaseCandidate[]>([]);
  const [loadingDetails, setLoadingDetails] = useState(false);
  const [loadingUsecases, setLoadingUsecases] = useState(false);
  const [loadingDocuments, setLoadingDocuments] = useState(false);

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
        // Prefer apqc_pcf if available, otherwise use first model
        const preferredModel = modelsData.find(m => m.model_key === 'apqc_pcf');
        const selectedModelKey = preferredModel?.model_key || modelsData[0].model_key;
        setSelectedModel(selectedModelKey);
      }
    } catch (error) {
      console.error('Failed to load models:', error);
    }
  };

  const loadNodeData = useCallback(async () => {
    if (!selectedNode) return;

    setLoadingDocuments(true);
    try {
      const [allDocsData, usecasesData] = await Promise.all([
        apiService.getDocumentsByNode(selectedNode.id),
        apiService.getUsecasesByNode(selectedNode.id),
      ]);

      // Separate process details from other documents
      const processDetailDoc = allDocsData.find((doc: NodeDocument) => doc.document_type === 'process_details');
      const otherDocs = allDocsData.filter((doc: NodeDocument) => doc.document_type !== 'process_details');
      
      setProcessDetails(processDetailDoc || null);
      setNodeDocuments(otherDocs);
      setUsecaseCandidates(usecasesData);
    } catch (error) {
      console.error('Failed to load node data:', error);
    } finally {
      setLoadingDocuments(false);
    }
  }, [selectedNode]);

  const handleModelChange = (event: any) => {
    setSelectedModel(event.target.value);
    setSelectedNode(null);
    setProcessDetails(null);
    setNodeDocuments([]);
    setUsecaseCandidates([]);
  };

  const handleNodeSelect = async (node: ProcessNode) => {
    try {
      // Use direct API call to get full node details by ID
      const response = await apiService.api.get(`/nodes/${node.id}/`);
      const fullNode = response.data;
      setSelectedNode(fullNode);
    } catch (error) {
      console.error('Failed to load full node details:', error);
      // Fall back to the basic node data
      setSelectedNode(node);
    }
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
      console.log('Generating specification for:', candidate.title);
      // Call the Django API to generate specification
      const response = await apiService.api.post(`/usecases/${candidate.id}/generate_specification/`);
      
      if (response.data.success) {
        alert('Specification generation started! Check the Documents section for updates.');
        // Optionally refresh documents to show the new specification
        if (selectedNode) {
          loadNodeData();
        }
      } else {
        throw new Error('Generation failed');
      }
    } catch (error) {
      console.error('Failed to generate specification:', error);
      alert('Failed to generate specification. Please try again.');
    }
  };

  const handleDeleteCandidate = async (candidate: NodeUsecaseCandidate) => {
    if (window.confirm('Are you sure you want to delete this use case candidate?')) {
      try {
        await apiService.api.delete(`/usecases/${candidate.id}/`);
        // Remove from local state immediately
        setUsecaseCandidates(prev => prev.filter(uc => uc.id !== candidate.id));
        alert('Use case candidate deleted successfully.');
      } catch (error) {
        console.error('Failed to delete candidate:', error);
        alert('Failed to delete use case candidate. Please try again.');
      }
    }
  };

  const findSpecDocument = (candidate: NodeUsecaseCandidate) => {
    return nodeDocuments.find(doc => 
      doc.document_type === 'usecase_spec' && 
      (doc.title?.includes(candidate.title) || doc.content?.includes(candidate.candidate_uid || ''))
    );
  };

  const handleViewOrGenerateSpec = async (candidate: NodeUsecaseCandidate) => {
    const existingSpec = findSpecDocument(candidate);
    
    if (existingSpec) {
      // View existing specification in Viewer
      // TODO: Open in Viewer tab/modal
      console.log('Opening specification in viewer:', existingSpec);
      alert(`Opening specification: ${existingSpec.title}`);
    } else {
      // Generate new specification
      await handleGenerateSpec(candidate);
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

      <Box sx={{ display: 'flex', gap: 2 }}>
        {/* Process Tree */}
        <Box sx={{ width: 380 }}>
          <Paper sx={{ p: 2, height: 600, overflow: 'auto' }}>
            <Typography variant="h6" gutterBottom>
              Process Hierarchy
            </Typography>
            {selectedModel && (
              <SimpleProcessTree
                modelKey={selectedModel}
                onNodeSelect={handleNodeSelect}
                selectedNodeId={selectedNode?.id}
              />
            )}
          </Paper>
        </Box>

        {/* Details Panel */}
        <Box sx={{ flex: 1, minWidth: 400 }}>
          <Paper sx={{ p: 2, height: 600, overflow: 'auto' }}>
            <Typography variant="h6" gutterBottom>
              Details
            </Typography>
            {!selectedNode ? (
              <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
                Select a process node to view details
              </Typography>
            ) : (
              <Box>
                <Box sx={{ mb: 3 }}>
                  <Typography variant="subtitle2" color="text.secondary">
                    Code
                  </Typography>
                  <Typography variant="body1" sx={{ fontWeight: 600 }}>
                    {selectedNode.code}
                  </Typography>
                </Box>
                
                <Box sx={{ mb: 3 }}>
                  <Typography variant="subtitle2" color="text.secondary">
                    Name
                  </Typography>
                  <Typography variant="body1">
                    {selectedNode.name}
                  </Typography>
                </Box>
                
                
                <Box sx={{ mb: 3 }}>
                  <Typography variant="subtitle2" color="text.secondary">
                    Description
                  </Typography>
                  {selectedNode.description ? (
                    <Typography variant="body2">
                      {selectedNode.description}
                    </Typography>
                  ) : (
                    <Typography variant="body2" color="text.disabled">
                      No description available (DEBUG: {JSON.stringify({
                        hasDesc: !!selectedNode.description,
                        descLength: selectedNode.description?.length || 0,
                        descValue: selectedNode.description || 'null'
                      })})
                    </Typography>
                  )}
                </Box>
                
                <Box sx={{ mb: 3 }}>
                  <Typography variant="subtitle2" color="text.secondary">
                    Level
                  </Typography>
                  <Chip 
                    label={`Level ${selectedNode.level}`} 
                    size="small" 
                    color="primary" 
                    variant="outlined"
                  />
                </Box>
                
                <Box sx={{ mb: 3 }}>
                  <Typography variant="subtitle2" color="text.secondary">
                    Type
                  </Typography>
                  <Chip 
                    label={selectedNode.is_leaf ? 'Leaf Node' : 'Parent Node'} 
                    size="small" 
                    color={selectedNode.is_leaf ? 'success' : 'info'}
                    variant="outlined"
                  />
                </Box>
                
                <Divider sx={{ my: 2 }} />
                
                {loadingDocuments ? (
                  <Box sx={{ display: 'flex', justifyContent: 'center', py: 2 }}>
                    <CircularProgress size={24} />
                  </Box>
                ) : (
                  <>
                    {processDetails && (
                      <Box sx={{ mb: 3 }}>
                        <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 1, display: 'flex', alignItems: 'center', gap: 0.5 }}>
                          <Description fontSize="small" />
                          Process Details
                        </Typography>
                        <Card variant="outlined" sx={{ backgroundColor: 'action.hover' }}>
                          <CardContent>
                            <Box sx={{ 
                              '& h1, & h2, & h3': { fontSize: '1.1rem', fontWeight: 600, mt: 1, mb: 0.5 },
                              '& h4, & h5, & h6': { fontSize: '1rem', fontWeight: 600, mt: 1, mb: 0.5 },
                              '& p': { fontSize: '0.875rem', lineHeight: 1.6, mb: 1 },
                              '& ul, & ol': { fontSize: '0.875rem', pl: 2 },
                              '& li': { mb: 0.5 },
                              '& code': { backgroundColor: 'action.selected', px: 0.5, py: 0.25, borderRadius: 0.5 },
                              '& pre': { backgroundColor: 'action.selected', p: 1, borderRadius: 1, overflow: 'auto' },
                            }}>
                              <ReactMarkdown>{processDetails.content}</ReactMarkdown>
                            </Box>
                            <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                              Updated: {new Date(processDetails.updated_at || processDetails.created_at).toLocaleString()}
                            </Typography>
                          </CardContent>
                        </Card>
                      </Box>
                    )}
                    
                    {nodeDocuments.filter(doc => doc.document_type !== 'usecase_spec').length > 0 && (
                      <Box sx={{ mb: 3 }}>
                        <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 1 }}>
                          Other Documents ({nodeDocuments.filter(doc => doc.document_type !== 'usecase_spec').length})
                        </Typography>
                        {nodeDocuments.filter(doc => doc.document_type !== 'usecase_spec').map((doc) => (
                          <Card key={doc.id} variant="outlined" sx={{ mb: 1 }}>
                            <CardContent sx={{ py: 1 }}>
                              <Typography variant="body2" fontWeight={600}>
                                {doc.title || doc.document_type}
                              </Typography>
                              <Typography variant="caption" color="text.secondary">
                                Type: {doc.document_type.replace('_', ' ')}
                              </Typography>
                            </CardContent>
                          </Card>
                        ))}
                      </Box>
                    )}
                  </>
                )}
                
                {usecaseCandidates.length > 0 && (
                  <Box sx={{ mb: 3 }}>
                    <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 2, display: 'flex', alignItems: 'center', gap: 0.5 }}>
                      <AutoAwesome fontSize="small" />
                      AI Use Case Candidates ({usecaseCandidates.length})
                    </Typography>
                    
                    {/* Use Case Candidates Table */}
                    <Box sx={{ 
                      border: '1px solid', 
                      borderColor: 'divider', 
                      borderRadius: 1, 
                      overflow: 'hidden',
                      backgroundColor: 'background.paper',
                      fontSize: '13px'
                    }}>
                      {/* Table Header */}
                      <Box sx={{ 
                        display: 'grid', 
                        gridTemplateColumns: '2fr 80px 70px 140px', 
                        backgroundColor: 'action.selected',
                        px: 1,
                        py: 0.75,
                        borderBottom: '1px solid',
                        borderColor: 'divider',
                        fontSize: '13px',
                        fontWeight: 600
                      }}>
                        <Box>Use Case</Box>
                        <Box>Complexity</Box>
                        <Box sx={{ textAlign: 'center' }}>Has Spec</Box>
                        <Box>Actions</Box>
                      </Box>
                      
                      {/* Table Body */}
                      {usecaseCandidates.map((uc, index) => (
                        <Box key={uc.id} sx={{ 
                          display: 'grid', 
                          gridTemplateColumns: '2fr 80px 70px 140px', 
                          px: 1,
                          py: 0.75,
                          borderBottom: index < usecaseCandidates.length - 1 ? '1px solid' : 'none',
                          borderColor: 'divider',
                          fontSize: '13px',
                          '&:hover': {
                            backgroundColor: 'action.hover'
                          },
                          alignItems: 'center'
                        }}>
                          {/* Use Case Title & Description */}
                          <Box>
                            <Typography variant="body2" fontWeight={600} sx={{ mb: 0.25, fontSize: '13px' }}>
                              {uc.title}
                            </Typography>
                            <Typography variant="caption" color="text.secondary" sx={{ 
                              display: '-webkit-box',
                              WebkitLineClamp: 2,
                              WebkitBoxOrient: 'vertical',
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                              lineHeight: 1.3,
                              fontSize: '12px'
                            }}>
                              {uc.description}
                            </Typography>
                            {uc.impact_assessment && (
                              <Typography variant="caption" color="primary" sx={{ display: 'block', mt: 0.25, fontSize: '11px' }}>
                                Impact: {uc.impact_assessment.substring(0, 40)}{uc.impact_assessment.length > 40 ? '...' : ''}
                              </Typography>
                            )}
                          </Box>
                          
                          {/* Complexity Score */}
                          <Box sx={{ display: 'flex', alignItems: 'center' }}>
                            {uc.complexity_score && (
                              <Chip
                                label={`${uc.complexity_score}/10`}
                                size="small"
                                color={uc.complexity_score <= 3 ? 'success' : 
                                       uc.complexity_score <= 7 ? 'warning' : 'error'}
                                sx={{ height: 24 }}
                              />
                            )}
                          </Box>
                          
                          {/* Has Spec */}
                          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                            {nodeDocuments.some(doc => 
                              doc.document_type === 'usecase_spec' && 
                              (doc.title?.includes(uc.title) || doc.content?.includes(uc.candidate_uid || ''))
                            ) && (
                              <CheckCircle sx={{ color: 'success.main', fontSize: '18px' }} />
                            )}
                          </Box>
                          
                          {/* Actions */}
                          <Box sx={{ display: 'flex', gap: 0.5, alignItems: 'center', justifyContent: 'flex-end' }}>
                            <Button
                              size="small"
                              variant={findSpecDocument(uc) ? 'outlined' : 'contained'}
                              startIcon={<Visibility />}
                              onClick={() => handleViewOrGenerateSpec(uc)}
                              sx={{ 
                                fontSize: '11px',
                                height: '28px',
                                minWidth: '60px',
                                px: 0.5
                              }}
                            >
                              {findSpecDocument(uc) ? 'View' : 'Gen'} Spec
                            </Button>
                            <Button
                              size="small"
                              variant="outlined"
                              color="error"
                              startIcon={<Delete />}
                              onClick={() => handleDeleteCandidate(uc)}
                              sx={{ 
                                fontSize: '11px',
                                height: '28px',
                                minWidth: '45px',
                                px: 0.5
                              }}
                            >
                              Del
                            </Button>
                          </Box>
                        </Box>
                      ))}
                    </Box>
                  </Box>
                )}
              </Box>
            )}
          </Paper>
        </Box>

      </Box>
    </Container>
  );
};

export default Composer;