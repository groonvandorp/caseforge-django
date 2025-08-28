import React, { useState, useEffect, useCallback } from 'react';
import {
  Container,
  Paper,
  Typography,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  LinearProgress,
  Alert,
  Divider,
} from '@mui/material';
import {
  AutoAwesome,
  Delete,
  Description,
} from '@mui/icons-material';
import ReactMarkdown from 'react-markdown';
import { useSearchParams } from 'react-router-dom';
import SimpleProcessTree from '../components/Process/SimpleProcessTree';
import { ProcessNode, NodeDocument, NodeUsecaseCandidate } from '../types';
import { apiService } from '../services/api';
import { useAppState } from '../contexts/AppStateContext';

const Composer: React.FC = () => {
  const { state: appState } = useAppState();
  const [searchParams, setSearchParams] = useSearchParams();
  // Use global model directly instead of local state
  const selectedModel = appState.selectedModelKey || '';
  const [selectedNode, setSelectedNode] = useState<ProcessNode | null>(null);
  const [processDetails, setProcessDetails] = useState<NodeDocument | null>(null);
  const [nodeDocuments, setNodeDocuments] = useState<NodeDocument[]>([]);
  const [usecaseCandidates, setUsecaseCandidates] = useState<NodeUsecaseCandidate[]>([]);
  const [highlightedUsecaseId, setHighlightedUsecaseId] = useState<number | null>(null);
  const [expandedNodeIds, setExpandedNodeIds] = useState<number[]>([]);
  const [loadingDetails, setLoadingDetails] = useState(false);
  const [taskProgress, setTaskProgress] = useState<{
    current: number;
    total: number;
    status: string;
  } | null>(null);
  const [loadingUsecases, setLoadingUsecases] = useState(false);
  const [loadingDocuments, setLoadingDocuments] = useState(false);


  // Function to expand tree path to show a specific node
  const expandPathToNode = async (nodeId: number) => {
    try {
      console.log('Composer: Expanding path to node:', nodeId);
      const ancestors = await apiService.getNodeAncestors(nodeId);
      const ancestorIds = ancestors.map(node => node.id);
      console.log('Composer: Setting expanded nodes to ancestors:', ancestorIds);
      setExpandedNodeIds(ancestorIds);
    } catch (error) {
      console.error('Composer: Failed to get ancestors for node expansion:', error);
    }
  };

  // Reset state when model changes
  useEffect(() => {
    setSelectedNode(null);
    setProcessDetails(null);
    setNodeDocuments([]);
    setUsecaseCandidates([]);
  }, [appState.selectedModelKey]);

  // Handle processCode or nodeId from URL parameters (navigation from Dashboard)
  useEffect(() => {
    const processCode = searchParams.get('processCode');
    const nodeId = searchParams.get('nodeId');
    const usecaseId = searchParams.get('usecaseId');
    console.log('Composer: processCode from URL:', processCode, 'nodeId:', nodeId, 'usecaseId:', usecaseId, 'selectedModel:', selectedModel, 'selectedNode:', selectedNode?.id);
    
    if (selectedModel) {
      if (nodeId && (!selectedNode || selectedNode.id !== parseInt(nodeId))) {
        console.log('Composer: Loading process from node ID:', nodeId);
        const loadProcessFromId = async () => {
          try {
            const process = await apiService.getNode(parseInt(nodeId));
            console.log('Composer: Successfully loaded process from ID:', process);
            console.log('Composer: Requested nodeId was:', nodeId, 'but got process with ID:', process.id);
            setSelectedNode(process);
            
            // Expand tree path to show the selected node
            await expandPathToNode(process.id);
            
            // If there's a usecaseId, set it for highlighting
            if (usecaseId) {
              console.log('Composer: Setting highlighted usecase ID:', usecaseId);
              setHighlightedUsecaseId(parseInt(usecaseId));
            }
            
            // Clear the URL parameters after loading
            setSearchParams({});
          } catch (error) {
            console.error(`Composer: Failed to load process with ID ${nodeId}:`, error);
          }
        };
        loadProcessFromId();
      } else if (processCode) {
        console.log('Composer: Loading process from code:', processCode);
        const loadProcessFromCode = async () => {
          try {
            const process = await apiService.getNodeByCode(processCode, selectedModel!);
            console.log('Composer: Successfully loaded process from code:', process);
            setSelectedNode(process);
            // Clear the URL parameter after loading
            setSearchParams({});
          } catch (error) {
            console.error(`Composer: Failed to load process with code ${processCode}:`, error);
          }
        };
        loadProcessFromCode();
      }
    }
  }, [searchParams, selectedModel, selectedNode, setSearchParams]);

  // Auto-scroll to highlighted use case after use cases are loaded
  useEffect(() => {
    if (highlightedUsecaseId && usecaseCandidates.length > 0) {
      // Small delay to ensure the DOM is updated
      setTimeout(() => {
        const element = document.getElementById(`usecase-${highlightedUsecaseId}`);
        if (element) {
          console.log('Composer: Scrolling to highlighted use case:', highlightedUsecaseId);
          element.scrollIntoView({ 
            behavior: 'smooth', 
            block: 'center',
            inline: 'nearest'
          });
          // Clear the highlight after a few seconds
          setTimeout(() => setHighlightedUsecaseId(null), 5000);
        }
      }, 100);
    }
  }, [highlightedUsecaseId, usecaseCandidates]);

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

  useEffect(() => {
    if (selectedNode) {
      loadNodeData();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedNode]);

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
      // Start the async task
      const response = await apiService.api.post(`/nodes/${selectedNode.id}/generate_details/`, {
        include_branch: true,
        cross_category: true
      });
      
      if (response.status === 202) {
        const taskId = response.data.task_id;
        console.log('Task started:', taskId);
        
        // Show initial success message
        alert(`Process details generation started for "${selectedNode.name}". This will run in the background - you can continue using the interface.`);
        
        // Start polling for task status
        pollTaskStatus(taskId);
      }
    } catch (error) {
      console.error('Failed to start process details generation:', error);
      alert('Failed to start process details generation. Please try again.');
      setLoadingDetails(false);
    }
  };

  const pollTaskStatus = async (taskId: string, maxAttempts = 30) => {
    let attempts = 0;
    
    const poll = async () => {
      try {
        attempts++;
        const response = await apiService.api.get(`/nodes/task-status/${taskId}/`);
        const taskData = response.data;
        
        console.log(`Task ${taskId} status:`, taskData.status, taskData);
        
        // Update progress if we have progress info
        if (taskData.status === 'PROGRESS' && taskData.info) {
          setTaskProgress({
            current: taskData.info.current || 0,
            total: taskData.info.total || 4,
            status: taskData.info.status || 'Processing...'
          });
        }
        
        if (taskData.ready) {
          setLoadingDetails(false);
          setTaskProgress(null);
          
          if (taskData.success) {
            console.log('Task completed successfully:', taskData.result);
            const resultStatus = taskData.result?.status || `Process details generated successfully for "${selectedNode?.name}"`;
            alert(`${resultStatus}. Check the Documents section below.`);
            
            // Refresh documents to show the new document
            if (selectedNode) {
              loadNodeData();
            }
          } else {
            console.error('Task failed:', taskData.error);
            alert(`Failed to generate process details: ${taskData.error || 'Unknown error'}`);
          }
          return;
        }
        
        // Continue polling if not ready and haven't exceeded max attempts
        if (attempts < maxAttempts) {
          setTimeout(poll, 2000); // Poll every 2 seconds
        } else {
          setLoadingDetails(false);
          setTaskProgress(null);
          alert('Process details generation is taking longer than expected. Please check the Documents section later.');
        }
      } catch (error) {
        console.error('Failed to check task status:', error);
        setLoadingDetails(false);
        setTaskProgress(null);
        alert('Unable to check generation status. Please refresh the page to see if the document was created.');
      }
    };
    
    // Start polling after a short delay
    setTimeout(poll, 1000);
  };

  const handleGenerateUsecases = async () => {
    if (!selectedNode) return;

    setLoadingUsecases(true);
    try {
      console.log('Generate use cases for:', selectedNode.code);
      
      // Call the real API endpoint
      const response = await apiService.generateUsecaseCandidates(selectedNode.id, true, true);
      console.log('Usecase generation started:', response);

      // Start polling for task completion (same pattern as process details)
      const taskId = response.task_id;
      setTaskProgress({ current: 0, total: 4, status: 'Starting usecase generation...' });
      
      const poll = async () => {
        try {
          const response = await apiService.api.get(`/nodes/task-status/${taskId}/`);
          const statusResponse = response.data;
          console.log('Task status:', statusResponse);
          
          if (statusResponse.status === 'PROGRESS' && statusResponse.info) {
            setTaskProgress(statusResponse.info);
          }
          
          if (statusResponse.ready) {
            setLoadingUsecases(false);
            setTaskProgress(null);
            
            if (statusResponse.success) {
              alert('AI usecase candidates generated successfully! Refreshing candidates...');
              // Refresh the usecase candidates list
              if (selectedNode) {
                const candidates = await apiService.getUsecasesByNode(selectedNode.id);
                setUsecaseCandidates(candidates);
              }
            } else {
              const errorMsg = statusResponse.error || 'Generation failed';
              alert(`Failed to generate usecase candidates: ${errorMsg}`);
            }
            return;
          }
          
          // Continue polling
          setTimeout(poll, 2000);
        } catch (error) {
          console.error('Failed to check task status:', error);
          setLoadingUsecases(false);
          setTaskProgress(null);
          alert('Unable to check generation status. Please refresh the page to see if candidates were created.');
        }
      };
      
      // Start polling after a short delay
      setTimeout(poll, 1000);
      
    } catch (error) {
      console.error('Failed to generate use cases:', error);
      alert('Failed to start usecase generation. Please try again.');
      setLoadingUsecases(false);
      setTaskProgress(null);
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

  const handleDeleteProcessDetails = async () => {
    if (!selectedNode || !processDetails) return;
    
    if (window.confirm(`Are you sure you want to delete the process details document for "${selectedNode.name}"? This action cannot be undone.`)) {
      try {
        const response = await apiService.deleteProcessDetails(selectedNode.id);
        
        // Remove from local state immediately
        setProcessDetails(null);
        alert(`Process details deleted successfully for ${response.node_code} (${response.node_name}).`);
        
        // Optionally refresh the node data to ensure consistency
        await loadNodeData();
      } catch (error: any) {
        console.error('Failed to delete process details:', error);
        const errorMessage = error.response?.data?.error || 'Failed to delete process details. Please try again.';
        alert(errorMessage);
      }
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


  return (
    <Container maxWidth="xl">
      <Box sx={{ mb: 3 }}>
        <Typography variant="h4" gutterBottom>
          AI Use Case Composer
        </Typography>
        
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
                expandedNodeIds={expandedNodeIds}
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
                {/* Compact Header Section */}
                <Box sx={{ mb: 2, p: 2, backgroundColor: 'action.hover', borderRadius: 1 }}>
                  <Box sx={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', mb: 1 }}>
                    <Box sx={{ flex: 1, mr: 2 }}>
                      <Typography variant="h6" sx={{ fontWeight: 600, mb: 0.5 }}>
                        {selectedNode.code}
                      </Typography>
                      <Typography variant="body1" sx={{ mb: 1 }}>
                        {selectedNode.name}
                      </Typography>
                    </Box>
                    <Box sx={{ display: 'flex', gap: 1, flexShrink: 0 }}>
                      <Chip 
                        label={`Level ${selectedNode.level}`} 
                        size="small" 
                        color="primary" 
                        variant="outlined"
                      />
                      <Chip 
                        label={selectedNode.is_leaf ? 'Leaf Node' : 'Parent Node'} 
                        size="small" 
                        color={selectedNode.is_leaf ? 'success' : 'info'}
                        variant="outlined"
                      />
                    </Box>
                  </Box>
                  
                  {selectedNode.description && (
                    <Typography variant="body2" color="text.secondary" sx={{ mt: 1, lineHeight: 1.4 }}>
                      {selectedNode.description}
                    </Typography>
                  )}
                </Box>

                {/* Process Details Actions - only for leaf nodes */}
                {selectedNode.is_leaf && (
                  <Box sx={{ mb: 3 }}>
                    {!processDetails ? (
                      // Show generate button if no process details exist
                      <Button
                        variant="contained"
                        startIcon={<AutoAwesome />}
                        onClick={handleGenerateDetails}
                        disabled={loadingDetails}
                        fullWidth
                        sx={{ mb: 1 }}
                      >
                        {loadingDetails ? 'Generating...' : 'Generate Process Details'}
                      </Button>
                    ) : (
                      // Show both regenerate and delete buttons if process details exist
                      <Box sx={{ display: 'flex', gap: 1, mb: 1 }}>
                        <Button
                          variant="contained"
                          startIcon={<AutoAwesome />}
                          onClick={handleGenerateDetails}
                          disabled={loadingDetails}
                          sx={{ flex: 1 }}
                        >
                          {loadingDetails ? 'Regenerating...' : 'Regenerate Details'}
                        </Button>
                        <Button
                          variant="outlined"
                          color="error"
                          startIcon={<Delete />}
                          onClick={handleDeleteProcessDetails}
                          disabled={loadingDetails}
                          sx={{ minWidth: '120px' }}
                        >
                          Delete
                        </Button>
                      </Box>
                    )}
                    
                    {/* AI Usecase Candidates Generation Button - Only show when process details exist */}
                    {processDetails && (
                      <Button
                        variant="outlined"
                        startIcon={<AutoAwesome />}
                        onClick={handleGenerateUsecases}
                        disabled={loadingUsecases || loadingDetails}
                        fullWidth
                        sx={{ mb: 1 }}
                      >
                        {loadingUsecases ? 'Generating AI Usecases...' : 'Generate AI Usecase Candidates'}
                      </Button>
                    )}
                    
                    {/* Progress indicator */}
                    {taskProgress && (
                      <Box sx={{ mt: 2 }}>
                        <Alert severity="info" sx={{ mb: 1 }}>
                          {taskProgress.status}
                        </Alert>
                        <LinearProgress 
                          variant="determinate" 
                          value={(taskProgress.current / taskProgress.total) * 100}
                          sx={{ mb: 1 }}
                        />
                        <Typography variant="body2" color="text.secondary" align="center">
                          Step {taskProgress.current} of {taskProgress.total}
                        </Typography>
                      </Box>
                    )}
                  </Box>
                )}
                
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
                    
                    {/* Use Case Candidates as Expandable Cards */}
                    {usecaseCandidates.map((uc, index) => {
                      const hasSpec = findSpecDocument(uc);
                      const isHighlighted = highlightedUsecaseId === uc.id;
                      return (
                        <Card 
                          key={uc.id} 
                          variant="outlined" 
                          id={`usecase-${uc.id}`}
                          sx={{ 
                            mb: 1.5,
                            ...(isHighlighted && {
                              border: '2px solid #1976d2',
                              backgroundColor: 'rgba(25, 118, 210, 0.04)',
                              boxShadow: '0 0 0 1px rgba(25, 118, 210, 0.2)'
                            })
                          }}
                        >
                          <CardContent>
                            {/* Header with Title and Actions */}
                            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
                              <Box sx={{ flex: 1, mr: 2 }}>
                                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                                  <Chip 
                                    label={uc.candidate_uid} 
                                    size="small" 
                                    color="primary" 
                                    variant="filled"
                                    sx={{ fontSize: '0.75rem', fontWeight: 600 }}
                                  />
                                  <Typography 
                                    variant="h6" 
                                    sx={{ 
                                      fontSize: '1rem', 
                                      fontWeight: 600,
                                      ...(isHighlighted && {
                                        color: '#1976d2'
                                      })
                                    }}
                                  >
                                    {isHighlighted && '🎯 '}{uc.title}
                                  </Typography>
                                </Box>
                                <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mb: 1 }}>
                                  {uc.complexity_score && (
                                    <Chip 
                                      label={`Complexity: ${uc.complexity_score}/10`} 
                                      size="small" 
                                      color={uc.complexity_score <= 3 ? 'success' : uc.complexity_score <= 6 ? 'warning' : 'error'}
                                      variant="outlined"
                                    />
                                  )}
                                  {hasSpec && (
                                    <Chip 
                                      label="Spec Available" 
                                      size="small" 
                                      color="primary" 
                                      variant="filled"
                                    />
                                  )}
                                  {uc.meta_json?.implementation_effort && (
                                    <Chip 
                                      label={`Effort: ${uc.meta_json.implementation_effort}`} 
                                      size="small" 
                                      variant="outlined"
                                    />
                                  )}
                                  {uc.meta_json?.roi_potential && (
                                    <Chip 
                                      label={`ROI: ${uc.meta_json.roi_potential}`} 
                                      size="small" 
                                      variant="outlined"
                                      color="secondary"
                                    />
                                  )}
                                </Box>
                              </Box>
                              
                              {/* Action Buttons */}
                              <Box sx={{ display: 'flex', gap: 1, flexShrink: 0 }}>
                                <Button
                                  size="small"
                                  variant="contained"
                                  onClick={() => handleGenerateSpec(uc)}
                                  disabled={!!hasSpec}
                                >
                                  {hasSpec ? 'Spec Generated' : 'Generate Spec'}
                                </Button>
                                <Button
                                  size="small"
                                  variant="outlined"
                                  color="error"
                                  onClick={() => handleDeleteCandidate(uc)}
                                >
                                  Delete
                                </Button>
                              </Box>
                            </Box>
                            
                            {/* Full Description */}
                            <Box sx={{ mb: 1.5 }}>
                              {uc.description.split(/(?=\b(?:What it does|Integration|Workflow|Expected outcomes|Business users):|(?:\d+\)))/g)
                                .filter(part => part.trim())
                                .map((part, index) => {
                                  const trimmedPart = part.trim();
                                  
                                  // Check if this is a section header
                                  if (trimmedPart.match(/^(What it does|Integration|Workflow|Expected outcomes|Business users):/)) {
                                    const [header, ...contentParts] = trimmedPart.split(':');
                                    const content = contentParts.join(':').trim();
                                    
                                    return (
                                      <Box key={index} sx={{ mb: 1 }}>
                                        <Typography variant="body2" sx={{ fontWeight: 600, color: 'text.primary', mb: 0.5 }}>
                                          {header}:
                                        </Typography>
                                        <Typography variant="body2" color="text.secondary" sx={{ lineHeight: 1.6 }}>
                                          {content}
                                        </Typography>
                                      </Box>
                                    );
                                  }
                                  
                                  // Check if this is a numbered item
                                  if (trimmedPart.match(/^\d+\)/)) {
                                    return (
                                      <Typography key={index} variant="body2" color="text.secondary" sx={{ lineHeight: 1.6, mb: 0.5, pl: 1 }}>
                                        {trimmedPart}
                                      </Typography>
                                    );
                                  }
                                  
                                  // Regular paragraph
                                  return (
                                    <Typography key={index} variant="body2" color="text.secondary" sx={{ lineHeight: 1.6, mb: 1 }}>
                                      {trimmedPart}
                                    </Typography>
                                  );
                                })}
                            </Box>
                            
                            {/* Impact Assessment */}
                            {uc.impact_assessment && (
                              <Box sx={{ mb: 1.5 }}>
                                <Typography variant="subtitle2" sx={{ mb: 0.5, fontWeight: 600 }}>
                                  Impact Assessment
                                </Typography>
                                <Typography variant="body2" color="text.secondary" sx={{ lineHeight: 1.6 }}>
                                  {uc.impact_assessment}
                                </Typography>
                              </Box>
                            )}
                            
                            {/* Additional Metadata */}
                            {uc.meta_json && (
                              <Box sx={{ mt: 2 }}>
                                {uc.meta_json.ai_technologies && uc.meta_json.ai_technologies.length > 0 && (
                                  <Box sx={{ mb: 1 }}>
                                    <Typography variant="caption" sx={{ fontWeight: 600, mr: 1 }}>
                                      AI Technologies:
                                    </Typography>
                                    {uc.meta_json.ai_technologies.map((tech: string, idx: number) => (
                                      <Chip 
                                        key={idx}
                                        label={tech} 
                                        size="small" 
                                        sx={{ mr: 0.5, mb: 0.5 }}
                                        variant="outlined"
                                      />
                                    ))}
                                  </Box>
                                )}
                                
                                {uc.meta_json.process_alignment && (
                                  <Box>
                                    <Typography variant="caption" sx={{ fontWeight: 600 }}>
                                      Process Alignment:
                                    </Typography>
                                    <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.25 }}>
                                      {uc.meta_json.process_alignment}
                                    </Typography>
                                  </Box>
                                )}
                              </Box>
                            )}
                            
                            {/* Created Date */}
                            <Typography variant="caption" color="text.disabled" sx={{ display: 'block', mt: 2 }}>
                              Generated: {new Date(uc.created_at).toLocaleString()}
                            </Typography>
                          </CardContent>
                        </Card>
                      );
                    })}
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