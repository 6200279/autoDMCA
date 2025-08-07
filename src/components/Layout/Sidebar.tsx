import React from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  Box,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Typography,
  Badge,
  Toolbar,
  Divider,
  useTheme,
} from '@mui/material';
import {
  Dashboard,
  Security,
  Person,
  CloudUpload,
  Settings,
  BarChart,
} from '@mui/icons-material';

interface NavItem {
  label: string;
  path: string;
  icon: React.ComponentType;
  badge?: number;
  description?: string;
}

const navigationItems: NavItem[] = [
  {
    label: 'Dashboard',
    path: '/dashboard',
    icon: Dashboard,
    description: 'Overview and analytics',
  },
  {
    label: 'Infringements',
    path: '/infringements',
    icon: Security,
    badge: 5, // This would be dynamic in real app
    description: 'Detected violations',
  },
  {
    label: 'Submit URLs',
    path: '/submit',
    icon: CloudUpload,
    description: 'Manual content submission',
  },
  {
    label: 'Analytics',
    path: '/analytics',
    icon: BarChart,
    description: 'Detailed reports',
  },
  {
    label: 'Profile',
    path: '/profile',
    icon: Person,
    description: 'Account information',
  },
  {
    label: 'Settings',
    path: '/settings',
    icon: Settings,
    description: 'App preferences',
  },
];

interface SidebarProps {
  onMobileToggle?: () => void;
}

const Sidebar: React.FC<SidebarProps> = ({ onMobileToggle }) => {
  const location = useLocation();
  const navigate = useNavigate();
  const theme = useTheme();

  const handleNavigation = (path: string) => {
    navigate(path);
    if (onMobileToggle) {
      onMobileToggle();
    }
  };

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <Toolbar>
        <Box display="flex" alignItems="center" width="100%">
          <Box
            sx={{
              width: 40,
              height: 40,
              borderRadius: 2,
              background: `linear-gradient(135deg, ${theme.palette.primary.main}, ${theme.palette.secondary.main})`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              mr: 2,
            }}
          >
            <Security sx={{ color: 'white', fontSize: 24 }} />
          </Box>
          <Box>
            <Typography variant="h6" fontWeight="600" color="primary">
              ContentGuard
            </Typography>
            <Typography variant="caption" color="textSecondary">
              Protection Platform
            </Typography>
          </Box>
        </Box>
      </Toolbar>

      <Divider />

      <Box sx={{ flex: 1, overflow: 'auto', py: 1 }}>
        <List>
          {navigationItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path;

            return (
              <ListItemButton
                key={item.path}
                onClick={() => handleNavigation(item.path)}
                selected={isActive}
                sx={{
                  mx: 1,
                  borderRadius: 2,
                  mb: 0.5,
                  '&.Mui-selected': {
                    backgroundColor: theme.palette.primary.main,
                    color: 'white',
                    '&:hover': {
                      backgroundColor: theme.palette.primary.dark,
                    },
                    '& .MuiListItemIcon-root': {
                      color: 'white',
                    },
                    '& .MuiListItemText-primary': {
                      fontWeight: 600,
                    },
                  },
                  '&:hover': {
                    backgroundColor: isActive ? theme.palette.primary.dark : theme.palette.action.hover,
                  },
                }}
              >
                <ListItemIcon
                  sx={{
                    minWidth: 40,
                    color: isActive ? 'white' : theme.palette.text.secondary,
                  }}
                >
                  {item.badge ? (
                    <Badge 
                      badgeContent={item.badge} 
                      color="error"
                      sx={{
                        '& .MuiBadge-badge': {
                          fontSize: '0.75rem',
                          height: 18,
                          minWidth: 18,
                        },
                      }}
                    >
                      <Icon />
                    </Badge>
                  ) : (
                    <Icon />
                  )}
                </ListItemIcon>
                
                <ListItemText
                  primary={item.label}
                  secondary={!isActive ? item.description : undefined}
                  primaryTypographyProps={{
                    fontSize: '0.95rem',
                    fontWeight: isActive ? 600 : 500,
                  }}
                  secondaryTypographyProps={{
                    fontSize: '0.75rem',
                    sx: { 
                      color: isActive ? 'rgba(255,255,255,0.7)' : theme.palette.text.disabled,
                    },
                  }}
                />
              </ListItemButton>
            );
          })}
        </List>

        <Divider sx={{ my: 2 }} />

        {/* Quick Stats Section */}
        <Box sx={{ px: 2, py: 1 }}>
          <Typography variant="overline" color="textSecondary" fontSize="0.75rem">
            Quick Stats
          </Typography>
          <Box sx={{ mt: 1, space: 1 }}>
            <Box display="flex" justifyContent="space-between" mb={1}>
              <Typography variant="body2" color="textSecondary">
                Active Monitoring
              </Typography>
              <Typography variant="body2" fontWeight="600">
                24
              </Typography>
            </Box>
            <Box display="flex" justifyContent="space-between" mb={1}>
              <Typography variant="body2" color="textSecondary">
                This Month
              </Typography>
              <Typography variant="body2" fontWeight="600" color="error">
                12 removed
              </Typography>
            </Box>
            <Box display="flex" justifyContent="space-between">
              <Typography variant="body2" color="textSecondary">
                Success Rate
              </Typography>
              <Typography variant="body2" fontWeight="600" color="success.main">
                94%
              </Typography>
            </Box>
          </Box>
        </Box>
      </Box>
    </Box>
  );
};

export default Sidebar;