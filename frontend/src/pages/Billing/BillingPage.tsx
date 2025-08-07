import React from 'react';
import { Container, Box, Typography, Breadcrumbs, Link } from '@mui/material';
import { Home, AccountBalance } from '@mui/icons-material';

import BillingDashboard from '../../components/billing/BillingDashboard';

const BillingPage: React.FC = () => {
  return (
    <Container maxWidth="xl">
      <Box sx={{ py: 3 }}>
        {/* Breadcrumbs */}
        <Breadcrumbs sx={{ mb: 3 }}>
          <Link
            color="inherit"
            href="/dashboard"
            sx={{ display: 'flex', alignItems: 'center' }}
          >
            <Home sx={{ mr: 0.5 }} fontSize="inherit" />
            Dashboard
          </Link>
          <Typography
            color="text.primary"
            sx={{ display: 'flex', alignItems: 'center' }}
          >
            <AccountBalance sx={{ mr: 0.5 }} fontSize="inherit" />
            Billing
          </Typography>
        </Breadcrumbs>

        {/* Main Content */}
        <BillingDashboard />
      </Box>
    </Container>
  );
};

export default BillingPage;