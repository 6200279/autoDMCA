import React from 'react';
import {
  Box,
  CircularProgress,
  Typography,
  useTheme,
} from '@mui/material';

const LoadingPage: React.FC = () => {
  const theme = useTheme();

  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '100vh',
        backgroundColor: theme.palette.background.default,
      }}
    >
      <CircularProgress
        size={60}
        thickness={4}
        sx={{ mb: 3 }}
      />
      <Typography
        variant="h6"
        color="textSecondary"
        sx={{ fontWeight: 300 }}
      >
        Loading ContentGuard...
      </Typography>
    </Box>
  );
};

export default LoadingPage;