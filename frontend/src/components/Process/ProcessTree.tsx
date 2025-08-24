import React, { useState, useEffect } from 'react';
import {
  TreeView,
  TreeItem,
} from '@mui/x-tree-view';
import {
  ExpandMore,
  ChevronRight,
  Folder,
  Description,
  Star,
  StarBorder,
} from '@mui/icons-material';
import { Box, Chip, IconButton, Tooltip } from '@mui/material';
import { ProcessNode } from '../../types';
import { apiService } from '../../services/api';

interface ProcessTreeProps {
  modelKey: string;
  onNodeSelect: (node: ProcessNode) => void;
  selectedNodeId?: number;
}

const ProcessTree: React.FC<ProcessTreeProps> = ({ 
  modelKey, 
  onNodeSelect, 
  selectedNodeId 
}) => {
  const [treeData, setTreeData] = useState<ProcessNode[]>([]);
  const [expandedNodes, setExpandedNodes] = useState<string[]>([]);
  const [bookmarkCounts, setBookmarkCounts] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (modelKey) {
      loadRootNodes();
      loadBookmarkCounts();
    }
  }, [modelKey]);

  const loadRootNodes = async () => {
    try {
      setLoading(true);
      const roots = await apiService.getRoots(modelKey);
      setTreeData(roots);
    } catch (error) {
      console.error('Failed to load root nodes:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadBookmarkCounts = async () => {
    try {
      const counts = await apiService.getBookmarkCounts(modelKey);
      setBookmarkCounts(counts);
    } catch (error) {
      console.error('Failed to load bookmark counts:', error);
    }
  };

  const loadChildren = async (nodeId: number): Promise<ProcessNode[]> => {
    try {
      return await apiService.getChildren(nodeId);
    } catch (error) {
      console.error('Failed to load children:', error);
      return [];
    }
  };

  const handleNodeToggle = async (event: React.SyntheticEvent, nodeIds: string[]) => {
    const newlyExpanded = nodeIds.filter(id => !expandedNodes.includes(id));
    
    if (newlyExpanded.length > 0) {
      const nodeId = parseInt(newlyExpanded[0]);
      const children = await loadChildren(nodeId);
      
      // Update tree data with children
      const updateNodeChildren = (nodes: ProcessNode[]): ProcessNode[] => {
        return nodes.map(node => {
          if (node.id === nodeId) {
            return { ...node, children };
          }
          if (node.children) {
            return { ...node, children: updateNodeChildren(node.children) };
          }
          return node;
        });
      };

      setTreeData(updateNodeChildren(treeData));
    }
    
    setExpandedNodes(nodeIds);
  };

  const handleNodeSelect = (event: React.SyntheticEvent, nodeId: string) => {
    const node = findNodeById(parseInt(nodeId), treeData);
    if (node && node.is_leaf) {
      onNodeSelect(node);
    }
  };

  const handleBookmarkToggle = async (event: React.MouseEvent, node: ProcessNode) => {
    event.stopPropagation();
    try {
      const result = await apiService.toggleBookmark(node.id);
      
      // Update bookmark counts
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

  const findNodeById = (id: number, nodes: ProcessNode[]): ProcessNode | null => {
    for (const node of nodes) {
      if (node.id === id) return node;
      if (node.children) {
        const found = findNodeById(id, node.children);
        if (found) return found;
      }
    }
    return null;
  };

  const renderTree = (nodes: ProcessNode[]) => {
    return nodes.map((node) => (
      <TreeItem
        key={node.id}
        nodeId={node.id.toString()}
        label={
          <Box sx={{ display: 'flex', alignItems: 'center', py: 0.5 }}>
            {node.is_leaf ? <Description sx={{ mr: 1, fontSize: 18 }} /> : <Folder sx={{ mr: 1, fontSize: 18 }} />}
            <Box sx={{ flexGrow: 1 }}>
              <Typography variant="body2" sx={{ fontWeight: node.is_leaf ? 'normal' : 'medium' }}>
                {node.code}: {node.name}
              </Typography>
            </Box>
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
                  {bookmarkCounts[node.code] ? <Star fontSize="small" color="primary" /> : <StarBorder fontSize="small" />}
                </IconButton>
              </Tooltip>
            )}
          </Box>
        }
        sx={{
          '& .MuiTreeItem-content': {
            borderRadius: 1,
            '&:hover': {
              backgroundColor: 'action.hover',
            },
            '&.Mui-selected': {
              backgroundColor: node.is_leaf ? 'primary.light' : 'transparent',
              '&:hover': {
                backgroundColor: node.is_leaf ? 'primary.light' : 'action.hover',
              },
            },
          },
        }}
      >
        {node.children && renderTree(node.children)}
      </TreeItem>
    ));
  };

  if (loading) {
    return (
      <Box sx={{ p: 2, textAlign: 'center' }}>
        Loading process tree...
      </Box>
    );
  }

  return (
    <Box sx={{ minHeight: 400, flexGrow: 1, maxWidth: 400, overflowY: 'auto' }}>
      <TreeView
        aria-label="process tree"
        defaultCollapseIcon={<ExpandMore />}
        defaultExpandIcon={<ChevronRight />}
        expanded={expandedNodes}
        selected={selectedNodeId?.toString() || ''}
        onNodeToggle={handleNodeToggle}
        onNodeSelect={handleNodeSelect}
        multiSelect={false}
      >
        {renderTree(treeData)}
      </TreeView>
    </Box>
  );
};

export default ProcessTree;