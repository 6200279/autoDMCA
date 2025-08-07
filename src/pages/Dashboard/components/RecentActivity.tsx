import React from 'react';
import {
  Box,
  List,
  ListItem,
  ListItemAvatar,
  ListItemText,
  Avatar,
  Typography,
  Chip,
  useTheme,
  alpha,
} from '@mui/material';
import {
  Security,
  CheckCircle,
  Schedule,
  CloudUpload,
  Warning,
} from '@mui/icons-material';
import { formatDistanceToNow } from 'date-fns';
import { Activity } from '@types/index';

interface RecentActivityProps {
  activities?: Activity[];
}

const getActivityIcon = (type: string) => {
  switch (type) {
    case 'detection':
      return Security;
    case 'takedown':
      return CheckCircle;
    case 'review':
      return Schedule;
    case 'upload':
      return CloudUpload;
    default:
      return Warning;
  }
};

const getActivityColor = (type: string, theme: any) => {
  switch (type) {
    case 'detection':
      return theme.palette.error.main;
    case 'takedown':
      return theme.palette.success.main;
    case 'review':
      return theme.palette.warning.main;
    case 'upload':
      return theme.palette.info.main;
    default:
      return theme.palette.text.secondary;
  }
};

const getStatusColor = (status?: string) => {
  switch (status) {
    case 'completed':
    case 'removed':
      return 'success';
    case 'pending':
      return 'warning';
    case 'failed':
      return 'error';
    default:
      return 'default';
  }
};

const RecentActivity: React.FC<RecentActivityProps> = ({ activities }) => {
  const theme = useTheme();

  // Default data for when no activities are available
  const defaultActivities: Activity[] = [
    {
      id: '1',
      type: 'detection',
      description: 'New infringement detected on YouTube',
      timestamp: new Date(Date.now() - 5 * 60 * 1000).toISOString(),
      status: 'pending',
    },
    {
      id: '2',
      type: 'takedown',
      description: 'Content successfully removed from Instagram',
      timestamp: new Date(Date.now() - 30 * 60 * 1000).toISOString(),
      status: 'completed',
    },
    {
      id: '3',
      type: 'upload',
      description: 'Manual URL submission processed',
      timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
      status: 'completed',
    },
    {
      id: '4',
      type: 'review',
      description: 'Infringement requires manual review',
      timestamp: new Date(Date.now() - 4 * 60 * 60 * 1000).toISOString(),
      status: 'pending',
    },
    {
      id: '5',
      type: 'takedown',
      description: 'DMCA takedown request failed',
      timestamp: new Date(Date.now() - 6 * 60 * 60 * 1000).toISOString(),
      status: 'failed',
    },
  ];

  const activityList = activities || defaultActivities;

  if (!activityList.length) {
    return (
      <Box 
        sx={{ 
          textAlign: 'center', 
          py: 4,
          color: theme.palette.text.secondary,
        }}
      >
        <Typography variant="body2">
          No recent activity to display
        </Typography>
      </Box>
    );
  }

  return (
    <List sx={{ width: '100%', p: 0 }}>
      {activityList.slice(0, 6).map((activity, index) => {
        const Icon = getActivityIcon(activity.type);
        const iconColor = getActivityColor(activity.type, theme);
        const timeAgo = formatDistanceToNow(new Date(activity.timestamp), { addSuffix: true });

        return (
          <ListItem
            key={activity.id}
            alignItems="flex-start"
            sx={{
              px: 0,
              py: 1.5,
              borderBottom: index < activityList.length - 1 ? `1px solid ${theme.palette.divider}` : 'none',
              '&:hover': {
                backgroundColor: alpha(theme.palette.action.hover, 0.5),
                borderRadius: 1,
              },
            }}
          >
            <ListItemAvatar sx={{ minWidth: 48 }}>
              <Avatar
                sx={{
                  width: 36,
                  height: 36,
                  backgroundColor: alpha(iconColor, 0.1),
                  border: `2px solid ${alpha(iconColor, 0.2)}`,
                }}
              >
                <Icon sx={{ fontSize: 18, color: iconColor }} />
              </Avatar>
            </ListItemAvatar>
            
            <ListItemText
              primary={
                <Typography 
                  variant="body2" 
                  sx={{ 
                    fontWeight: 500,
                    lineHeight: 1.3,
                    mb: 0.5,
                  }}
                >
                  {activity.description}
                </Typography>
              }
              secondary={
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 0.5 }}>
                  <Typography 
                    variant="caption" 
                    color="textSecondary"
                    sx={{ fontSize: '0.75rem' }}
                  >
                    {timeAgo}
                  </Typography>
                  {activity.status && (
                    <Chip
                      label={activity.status}
                      size="small"
                      color={getStatusColor(activity.status) as any}
                      sx={{
                        height: 18,
                        fontSize: '0.65rem',
                        fontWeight: 600,
                        textTransform: 'capitalize',
                        '& .MuiChip-label': {
                          px: 1,
                        },
                      }}
                    />
                  )}
                </Box>
              }
            />
          </ListItem>
        );
      })}
    </List>
  );
};

export default RecentActivity;