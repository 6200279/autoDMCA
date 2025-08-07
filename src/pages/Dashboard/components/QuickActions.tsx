import React from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Button,
  Grid,
  useTheme,
  alpha,
  Typography,
} from '@mui/material';
import {
  CloudUpload,
  Security,
  BarChart,
  Settings,
  Add,
  Search,
} from '@mui/icons-material';

const QuickActions: React.FC = () => {
  const navigate = useNavigate();
  const theme = useTheme();

  const actions = [
    {
      label: 'Submit URLs',
      description: 'Manual content submission',
      icon: CloudUpload,
      color: theme.palette.primary.main,
      path: '/submit',
    },
    {
      label: 'View Infringements',
      description: 'Check detected violations',
      icon: Security,
      color: theme.palette.error.main,
      path: '/infringements',
    },
    {
      label: 'Add Monitoring',
      description: 'Monitor new content',
      icon: Add,
      color: theme.palette.success.main,
      path: '/monitoring/add',
    },
    {
      label: 'View Analytics',
      description: 'Detailed reports',
      icon: BarChart,
      color: theme.palette.info.main,
      path: '/analytics',
    },
    {
      label: 'Search Content',
      description: 'Find specific violations',
      icon: Search,
      color: theme.palette.warning.main,
      path: '/search',
    },
    {
      label: 'Settings',
      description: 'Configure preferences',
      icon: Settings,
      color: theme.palette.text.secondary,
      path: '/settings',
    },
  ];

  return (
    <Grid container spacing={2} sx={{ height: '100%' }}>
      {actions.map((action, index) => {
        const Icon = action.icon;
        
        return (
          <Grid item xs={6} key={index}>
            <Button
              fullWidth
              variant="outlined"
              onClick={() => navigate(action.path)}
              sx={{
                height: 80,
                flexDirection: 'column',
                gap: 1,
                border: `1px solid ${alpha(action.color, 0.2)}`,
                backgroundColor: alpha(action.color, 0.02),
                color: theme.palette.text.primary,
                '&:hover': {
                  backgroundColor: alpha(action.color, 0.08),
                  border: `1px solid ${alpha(action.color, 0.4)}`,
                  transform: 'translateY(-1px)',
                },
                transition: 'all 0.2s ease-in-out',
              }}
            >
              <Icon 
                sx={{ 
                  fontSize: 20,
                  color: action.color,
                }} 
              />
              <Box textAlign="center">
                <Typography 
                  variant="body2" 
                  fontWeight="600"
                  sx={{ fontSize: '0.75rem', lineHeight: 1.2 }}
                >
                  {action.label}
                </Typography>
                <Typography 
                  variant="caption" 
                  color="textSecondary"
                  sx={{ fontSize: '0.65rem', lineHeight: 1.1 }}
                >
                  {action.description}
                </Typography>
              </Box>
            </Button>
          </Grid>
        );
      })}
    </Grid>
  );
};

export default QuickActions;