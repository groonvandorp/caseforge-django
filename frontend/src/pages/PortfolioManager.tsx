import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  CardActions,
  Button,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Chip,
  Alert,
  Fab,
  Menu,
  MenuItem,
} from '@mui/material';
import {
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  MoreVert as MoreVertIcon,
  Folder as FolderIcon,
  FolderOpen as FolderOpenIcon,
  ArrowBack as ArrowBackIcon,
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { apiService } from '../services/api';

interface Portfolio {
  id: number;
  name: string;
  description?: string;
  items_count: number;
  created_at: string;
}


interface PortfolioItem {
  id: number;
  portfolio: number;
  usecase_candidate: number;
  usecase_title: string;
  node_code: string;
  candidate_uid: string;
  added_at: string;
}

const PortfolioManager: React.FC = () => {
  const [portfolios, setPortfolios] = useState<Portfolio[]>([]);
  const [selectedPortfolio, setSelectedPortfolio] = useState<Portfolio | null>(null);
  const [portfolioItems, setPortfolioItems] = useState<PortfolioItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Dialog states
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [portfolioToDelete, setPortfolioToDelete] = useState<Portfolio | null>(null);
  
  // Form states
  const [portfolioName, setPortfolioName] = useState('');
  const [portfolioDescription, setPortfolioDescription] = useState('');
  
  // Menu states
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [menuPortfolio, setMenuPortfolio] = useState<Portfolio | null>(null);
  
  const navigate = useNavigate();

  // Load portfolios
  useEffect(() => {
    loadPortfolios();
  }, []);

  const loadPortfolios = async () => {
    try {
      setLoading(true);
      setError(null);
      const portfolios = await apiService.getPortfolios();
      setPortfolios(portfolios);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load portfolios');
    } finally {
      setLoading(false);
    }
  };

  const loadPortfolioItems = async (portfolioId: number) => {
    try {
      setLoading(true);
      setError(null);
      const items = await apiService.getPortfolioItems(portfolioId);
      setPortfolioItems(items);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load portfolio items');
    } finally {
      setLoading(false);
    }
  };

  const handleCreatePortfolio = async () => {
    if (!portfolioName.trim()) return;
    
    try {
      setLoading(true);
      await apiService.createPortfolio(portfolioName, portfolioDescription);
      
      setCreateDialogOpen(false);
      setPortfolioName('');
      setPortfolioDescription('');
      await loadPortfolios();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create portfolio');
    } finally {
      setLoading(false);
    }
  };

  const handleEditPortfolio = async () => {
    if (!selectedPortfolio || !portfolioName.trim()) return;
    
    try {
      setLoading(true);
      await apiService.updatePortfolio(selectedPortfolio.id, portfolioName, portfolioDescription);
      
      setEditDialogOpen(false);
      setSelectedPortfolio(null);
      setPortfolioName('');
      setPortfolioDescription('');
      await loadPortfolios();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to update portfolio');
    } finally {
      setLoading(false);
    }
  };

  const handleDeletePortfolio = async () => {
    if (!portfolioToDelete) return;
    
    try {
      setLoading(true);
      await apiService.deletePortfolio(portfolioToDelete.id);
      
      setDeleteDialogOpen(false);
      setPortfolioToDelete(null);
      
      // If we're currently viewing the deleted portfolio, go back to list
      if (selectedPortfolio?.id === portfolioToDelete.id) {
        setSelectedPortfolio(null);
        setPortfolioItems([]);
      }
      
      await loadPortfolios();
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to delete portfolio');
    } finally {
      setLoading(false);
    }
  };

  const handleRemoveItem = async (itemId: number) => {
    if (!selectedPortfolio) return;
    
    try {
      setLoading(true);
      const item = portfolioItems.find(item => item.id === itemId);
      if (item) {
        await apiService.removeFromPortfolio(selectedPortfolio.id, item.candidate_uid);
        await loadPortfolioItems(selectedPortfolio.id);
        await loadPortfolios(); // Refresh counts
      }
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to remove item');
    } finally {
      setLoading(false);
    }
  };

  const openCreateDialog = () => {
    setPortfolioName('');
    setPortfolioDescription('');
    setCreateDialogOpen(true);
  };

  const openEditDialog = (portfolio: Portfolio) => {
    setSelectedPortfolio(portfolio);
    setPortfolioName(portfolio.name);
    setPortfolioDescription(portfolio.description || '');
    setEditDialogOpen(true);
    setAnchorEl(null);
  };

  const openDeleteDialog = (portfolio: Portfolio) => {
    setPortfolioToDelete(portfolio);
    setDeleteDialogOpen(true);
    setAnchorEl(null);
  };

  const handleMenuClick = (event: React.MouseEvent<HTMLElement>, portfolio: Portfolio) => {
    setAnchorEl(event.currentTarget);
    setMenuPortfolio(portfolio);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
    setMenuPortfolio(null);
  };

  const navigateToComposer = (item: PortfolioItem) => {
    // Navigate to composer with the specific node code and use case ID
    navigate(`/composer?processCode=${item.node_code}&usecaseId=${item.usecase_candidate}`);
  };

  const viewPortfolioContents = async (portfolio: Portfolio) => {
    setSelectedPortfolio(portfolio);
    await loadPortfolioItems(portfolio.id);
  };

  const backToPortfolioList = () => {
    setSelectedPortfolio(null);
    setPortfolioItems([]);
  };

  if (selectedPortfolio) {
    // Portfolio contents view
    return (
      <Box sx={{ p: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
          <IconButton onClick={backToPortfolioList} sx={{ mr: 2 }}>
            <ArrowBackIcon />
          </IconButton>
          <FolderOpenIcon sx={{ mr: 2, color: 'primary.main' }} />
          <Box>
            <Typography variant="h4" component="h1">
              {selectedPortfolio.name}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {selectedPortfolio.description}
            </Typography>
          </Box>
        </Box>

        {error && (
          <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        {portfolioItems.length === 0 ? (
          <Card sx={{ p: 4, textAlign: 'center' }}>
            <Typography variant="h6" color="text.secondary" sx={{ mb: 2 }}>
              This portfolio is empty
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Add AI use cases from the Composer to build your portfolio
            </Typography>
            <Button
              variant="outlined"
              onClick={() => navigate('/composer')}
              sx={{ mt: 2 }}
            >
              Go to Composer
            </Button>
          </Card>
        ) : (
          <Box sx={{ 
            display: 'grid', 
            gridTemplateColumns: { xs: '1fr', md: 'repeat(2, 1fr)', lg: 'repeat(3, 1fr)' }, 
            gap: 3 
          }}>
            {portfolioItems.map((item) => (
              <Card key={item.id} sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                  <CardContent sx={{ flexGrow: 1 }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
                      <Chip
                        label={item.node_code}
                        size="small"
                        variant="outlined"
                        color="primary"
                      />
                      <IconButton
                        size="small"
                        onClick={() => handleRemoveItem(item.id)}
                        color="error"
                      >
                        <DeleteIcon />
                      </IconButton>
                    </Box>
                    
                    <Typography variant="h6" sx={{ mb: 1, fontWeight: 600 }}>
                      {item.usecase_title}
                    </Typography>
                    
                    <Typography variant="body2" color="text.secondary">
                      Added {new Date(item.added_at).toLocaleDateString()}
                    </Typography>
                  </CardContent>
                  
                  <CardActions>
                    <Button
                      size="small"
                      onClick={() => navigateToComposer(item)}
                      variant="outlined"
                    >
                      View in Composer
                    </Button>
                  </CardActions>
                </Card>
            ))}
          </Box>
        )}
      </Box>
    );
  }

  // Portfolio list view
  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" component="h1" sx={{ mb: 3, display: 'flex', alignItems: 'center' }}>
        <FolderIcon sx={{ mr: 2, color: 'primary.main' }} />
        Portfolio Manager
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {portfolios.length === 0 ? (
        <Card sx={{ p: 4, textAlign: 'center' }}>
          <Typography variant="h6" color="text.secondary" sx={{ mb: 2 }}>
            No portfolios yet
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            Create your first portfolio to start organizing AI use cases
          </Typography>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={openCreateDialog}
          >
            Create Portfolio
          </Button>
        </Card>
      ) : (
        <>
          <Box sx={{ 
            display: 'grid', 
            gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, 1fr)', lg: 'repeat(3, 1fr)' }, 
            gap: 3 
          }}>
            {portfolios.map((portfolio) => (
                <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                  <CardContent sx={{ flexGrow: 1 }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
                      <Typography variant="h6" sx={{ fontWeight: 600 }}>
                        {portfolio.name}
                      </Typography>
                      <IconButton
                        size="small"
                        onClick={(e) => handleMenuClick(e, portfolio)}
                      >
                        <MoreVertIcon />
                      </IconButton>
                    </Box>
                    
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                      {portfolio.description || 'No description'}
                    </Typography>
                    
                    <Chip
                      label={`${portfolio.items_count} use cases`}
                      size="small"
                      color="primary"
                      variant="outlined"
                    />
                    
                    <Typography variant="caption" color="text.secondary" sx={{ mt: 2, display: 'block' }}>
                      Created {new Date(portfolio.created_at).toLocaleDateString()}
                    </Typography>
                  </CardContent>
                  
                  <CardActions>
                    <Button
                      size="small"
                      onClick={() => viewPortfolioContents(portfolio)}
                      variant="outlined"
                    >
                      View Contents
                    </Button>
                  </CardActions>
                </Card>
            ))}
          </Box>

          <Fab
            color="primary"
            aria-label="add portfolio"
            sx={{ position: 'fixed', bottom: 16, right: 16 }}
            onClick={openCreateDialog}
          >
            <AddIcon />
          </Fab>
        </>
      )}

      {/* Context Menu */}
      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleMenuClose}
      >
        <MenuItem onClick={() => menuPortfolio && openEditDialog(menuPortfolio)}>
          <EditIcon sx={{ mr: 1 }} /> Edit
        </MenuItem>
        <MenuItem onClick={() => menuPortfolio && openDeleteDialog(menuPortfolio)}>
          <DeleteIcon sx={{ mr: 1 }} /> Delete
        </MenuItem>
      </Menu>

      {/* Create Portfolio Dialog */}
      <Dialog open={createDialogOpen} onClose={() => setCreateDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Create New Portfolio</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="Portfolio Name"
            fullWidth
            variant="outlined"
            value={portfolioName}
            onChange={(e) => setPortfolioName(e.target.value)}
            sx={{ mb: 2 }}
          />
          <TextField
            margin="dense"
            label="Description (optional)"
            fullWidth
            multiline
            rows={3}
            variant="outlined"
            value={portfolioDescription}
            onChange={(e) => setPortfolioDescription(e.target.value)}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateDialogOpen(false)}>Cancel</Button>
          <Button
            onClick={handleCreatePortfolio}
            variant="contained"
            disabled={!portfolioName.trim() || loading}
          >
            Create
          </Button>
        </DialogActions>
      </Dialog>

      {/* Edit Portfolio Dialog */}
      <Dialog open={editDialogOpen} onClose={() => setEditDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Edit Portfolio</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="Portfolio Name"
            fullWidth
            variant="outlined"
            value={portfolioName}
            onChange={(e) => setPortfolioName(e.target.value)}
            sx={{ mb: 2 }}
          />
          <TextField
            margin="dense"
            label="Description (optional)"
            fullWidth
            multiline
            rows={3}
            variant="outlined"
            value={portfolioDescription}
            onChange={(e) => setPortfolioDescription(e.target.value)}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditDialogOpen(false)}>Cancel</Button>
          <Button
            onClick={handleEditPortfolio}
            variant="contained"
            disabled={!portfolioName.trim() || loading}
          >
            Save Changes
          </Button>
        </DialogActions>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onClose={() => setDeleteDialogOpen(false)}>
        <DialogTitle>Delete Portfolio</DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to delete "{portfolioToDelete?.name}"?
            {portfolioToDelete?.items_count && portfolioToDelete.items_count > 0 && (
              <Alert severity="warning" sx={{ mt: 2 }}>
                This portfolio contains {portfolioToDelete.items_count} use cases. 
                You must remove all items before deleting the portfolio.
              </Alert>
            )}
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialogOpen(false)}>Cancel</Button>
          <Button
            onClick={handleDeletePortfolio}
            color="error"
            variant="contained"
            disabled={loading || Boolean(portfolioToDelete?.items_count && portfolioToDelete.items_count > 0)}
          >
            Delete
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default PortfolioManager;