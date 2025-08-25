import React, { useState, useEffect, useCallback } from 'react';
import {
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Collapse,
  Box,
  Typography,
  Chip,
  IconButton,
  Tooltip,
} from '@mui/material';
import {
  ExpandLess,
  ExpandMore,
  Folder,
  Description,
  Star,
  StarBorder,
} from '@mui/icons-material';
import { ProcessNode } from '../../types';
import { apiService } from '../../services/api';

interface SimpleProcessTreeProps {
  modelKey: string;
  onNodeSelect: (node: ProcessNode) => void;
  selectedNodeId?: number;
}

const SimpleProcessTree: React.FC<SimpleProcessTreeProps> = ({ 
  modelKey, 
  onNodeSelect, 
  selectedNodeId 
}) => {
  const [treeData, setTreeData] = useState<ProcessNode[]>([]);
  const [expandedNodes, setExpandedNodes] = useState<Set<number>>(new Set());
  const [bookmarkCounts, setBookmarkCounts] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (modelKey) {
      loadRootNodes();
      loadBookmarkCounts();
    }
  }, [modelKey]);

  const loadRootNodes = useCallback(async () => {
    try {
      setLoading(true);
      const roots = await apiService.getRoots(modelKey);
      setTreeData(roots);
    } catch (error) {
      console.error('Failed to load root nodes:', error);
    } finally {
      setLoading(false);
    }
  }, [modelKey]);

  const loadBookmarkCounts = useCallback(async () => {
    try {
      const counts = await apiService.getBookmarkCounts(modelKey);
      setBookmarkCounts(counts);
    } catch (error) {
      console.error('Failed to load bookmark counts:', error);
    }
  }, [modelKey]);

  const handleToggle = async (node: ProcessNode) => {
    const isExpanded = expandedNodes.has(node.id);
    const newExpanded = new Set(expandedNodes);
    
    if (isExpanded) {
      newExpanded.delete(node.id);
    } else {
      newExpanded.add(node.id);
      // Load children if not already loaded
      if (!node.children && !node.is_leaf) {
        try {
          const children = await apiService.getChildren(node.id);
          // Update tree data with children
          const updateNodeChildren = (nodes: ProcessNode[]): ProcessNode[] => {
            return nodes.map(n => {
              if (n.id === node.id) {
                return { ...n, children };
              }
              if (n.children) {
                return { ...n, children: updateNodeChildren(n.children) };
              }
              return n;
            });
          };
          setTreeData(updateNodeChildren(treeData));
        } catch (error) {
          console.error('Failed to load children:', error);
        }
      }
    }
    
    setExpandedNodes(newExpanded);
  };

  const handleNodeClick = (node: ProcessNode) => {
    if (node.is_leaf) {
      onNodeSelect(node);
    }
  };

  const handleBookmarkToggle = async (event: React.MouseEvent, node: ProcessNode) => {
    event.stopPropagation();
    try {
      const result = await apiService.toggleBookmark(node.id);
      
      const newCounts = { ...bookmarkCounts };
      if (result.bookmarked) {
        newCounts[node.code] = (newCounts[node.code] || 0) + 1;
      } else {
        newCounts[node.code] = Math.max(0, (newCounts[node.code] || 1) - 1);
        if (newCounts[node.code] === 0) {
          delete newCounts[node.code];
        }
      }
      setBookmarkCounts(newCounts);
    } catch (error) {
      console.error('Failed to toggle bookmark:', error);
    }
  };

  const renderNode = (node: ProcessNode, level: number = 0): React.ReactNode => {
    const isExpanded = expandedNodes.has(node.id);
    const isSelected = selectedNodeId === node.id;
    const hasChildren = !node.is_leaf && (node.children_count > 0 || node.children);

    return (
      <Box key={node.id}>
        <ListItem
          disablePadding
          sx={{
            pl: level * 2,
            backgroundColor: isSelected ? 'primary.light' : 'transparent',
            '&:hover': {
              backgroundColor: 'action.hover',
            },
          }}
        >
          <ListItemButton
            onClick={() => hasChildren ? handleToggle(node) : handleNodeClick(node)}
            disabled={!node.is_leaf && !hasChildren}
          >
            <ListItemIcon sx={{ minWidth: 32 }}>
              {hasChildren ? (
                isExpanded ? <ExpandLess /> : <ExpandMore />
              ) : node.is_leaf ? (
                <Description />
              ) : (
                <Folder />
              )}
            </ListItemIcon>
            
            <ListItemText
              primary={
                <Box sx={{ display: 'flex', alignItems: 'center' }}>
                  <Typography variant="body2" sx={{ flexGrow: 1 }}>
                    {node.code}: {node.name}
                  </Typography>
                  {bookmarkCounts[node.code] && (
                    <Chip
                      size="small"
                      label={bookmarkCounts[node.code]}
                      color="primary"
                      sx={{ mr: 1, height: 20, fontSize: '0.75rem' }}
                    />
                  )}
                  {node.is_leaf && (
                    <Tooltip title="Toggle bookmark">
                      <IconButton
                        size="small"
                        onClick={(e) => handleBookmarkToggle(e, node)}
                        sx={{ p: 0.5 }}
                      >
                        {bookmarkCounts[node.code] ? 
                          <Star fontSize="small" color="primary" /> : 
                          <StarBorder fontSize="small" />
                        }
                      </IconButton>
                    </Tooltip>
                  )}
                </Box>
              }
            />
          </ListItemButton>
        </ListItem>
        
        {hasChildren && (
          <Collapse in={isExpanded} timeout="auto" unmountOnExit>
            <List component="div" disablePadding>
              {node.children?.map(child => renderNode(child, level + 1))}
            </List>
          </Collapse>
        )}
      </Box>
    );
  };

  if (loading) {
    return (
      <Box sx={{ p: 2, textAlign: 'center' }}>
        <Typography>Loading process tree...</Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ minHeight: 400, flexGrow: 1, maxWidth: 400, overflowY: 'auto' }}>
      <List component="nav" aria-label="process tree">
        {treeData.map(node => renderNode(node))}
      </List>
    </Box>
  );
};

export default SimpleProcessTree;