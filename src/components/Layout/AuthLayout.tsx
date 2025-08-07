import React from 'react';
import {
  Box,
  Container,
  Paper,
  Typography,
  useTheme,
  alpha,
} from '@mui/material';

interface AuthLayoutProps {
  children: React.ReactNode;
}

const AuthLayout: React.FC<AuthLayoutProps> = ({ children }) => {
  const theme = useTheme();

  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: `linear-gradient(135deg, ${alpha(theme.palette.primary.main, 0.1)} 0%, ${alpha(theme.palette.secondary.main, 0.1)} 100%)`,
        padding: 2,
      }}
    >
      <Container maxWidth="sm">
        <Box textAlign="center" mb={4}>
          <Typography
            variant="h2"
            component="h1"
            gutterBottom
            sx={{
              fontWeight: 300,
              color: theme.palette.primary.main,
              textShadow: '0 2px 4px rgba(0,0,0,0.1)',
            }}
          >
            ContentGuard
          </Typography>
          <Typography
            variant="h6"
            color="textSecondary"
            sx={{ fontWeight: 300 }}
          >
            Protect your content with AI-powered monitoring
          </Typography>
        </Box>
        
        <Paper
          elevation={8}
          sx={{
            padding: 4,
            backgroundColor: alpha(theme.palette.background.paper, 0.95),
            backdropFilter: 'blur(10px)',
            borderRadius: 3,
            border: `1px solid ${alpha(theme.palette.divider, 0.1)}`,
          }}
        >
          {children}
        </Paper>
        
        <Box textAlign="center" mt={3}>
          <Typography variant="body2" color="textSecondary">
            © 2024 ContentGuard. Secure content protection platform.
          </Typography>
        </Box>
      </Container>
    </Box>
  );
};

export default AuthLayout;