import React, { useState } from 'react';
import {
  Card,
  CardContent,
  CardHeader,
  Box,
  Typography,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  IconButton,
  Collapse,
  Link,
  Alert
} from '@mui/material';
import {
  Receipt,
  Download,
  ExpandMore,
  ExpandLess,
  Visibility
} from '@mui/icons-material';
import { format } from 'date-fns';

interface InvoiceHistoryProps {
  invoices: any[];
  showAll?: boolean;
  onRefresh: () => void;
}

const InvoiceHistory: React.FC<InvoiceHistoryProps> = ({
  invoices,
  showAll = false,
  onRefresh
}) => {
  const [expandedInvoice, setExpandedInvoice] = useState<number | null>(null);

  const getStatusColor = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'paid':
        return 'success';
      case 'open':
        return 'warning';
      case 'draft':
        return 'info';
      case 'void':
      case 'uncollectible':
        return 'error';
      default:
        return 'default';
    }
  };

  const handleExpandClick = (invoiceId: number) => {
    setExpandedInvoice(expandedInvoice === invoiceId ? null : invoiceId);
  };

  const formatCurrency = (amount: number, currency: string = 'USD') => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency.toUpperCase(),
    }).format(amount);
  };

  const displayInvoices = showAll ? invoices : invoices.slice(0, 5);

  if (!invoices || invoices.length === 0) {
    return (
      <Card>
        <CardHeader
          title="Invoice History"
          avatar={<Receipt />}
        />
        <CardContent>
          <Alert severity="info">
            No invoices found. Invoices will appear here once you have an active subscription.
          </Alert>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader
        title="Invoice History"
        avatar={<Receipt />}
        action={
          !showAll && invoices.length > 5 && (
            <Button size="small" onClick={onRefresh}>
              View All
            </Button>
          )
        }
      />
      <CardContent>
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Invoice</TableCell>
                <TableCell>Date</TableCell>
                <TableCell>Status</TableCell>
                <TableCell align="right">Amount</TableCell>
                <TableCell align="center">Actions</TableCell>
                <TableCell />
              </TableRow>
            </TableHead>
            <TableBody>
              {displayInvoices.map((invoice) => (
                <React.Fragment key={invoice.id}>
                  <TableRow>
                    <TableCell>
                      <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                        {invoice.invoiceNumber || `INV-${invoice.id}`}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2">
                        {format(new Date(invoice.invoiceDate), 'MMM dd, yyyy')}
                      </Typography>
                      {invoice.dueDate && invoice.status === 'open' && (
                        <Typography variant="caption" color="text.secondary" display="block">
                          Due: {format(new Date(invoice.dueDate), 'MMM dd, yyyy')}
                        </Typography>
                      )}
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={invoice.status.toUpperCase()}
                        color={getStatusColor(invoice.status)}
                        size="small"
                      />
                    </TableCell>
                    <TableCell align="right">
                      <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
                        {formatCurrency(invoice.total, invoice.currency)}
                      </Typography>
                      {invoice.amountDue > 0 && invoice.status !== 'paid' && (
                        <Typography variant="caption" color="error.main" display="block">
                          Due: {formatCurrency(invoice.amountDue, invoice.currency)}
                        </Typography>
                      )}
                    </TableCell>
                    <TableCell align="center">
                      <Box sx={{ display: 'flex', justifyContent: 'center', gap: 0.5 }}>
                        {invoice.hostedInvoiceUrl && (
                          <IconButton
                            size="small"
                            component="a"
                            href={invoice.hostedInvoiceUrl}
                            target="_blank"
                            rel="noopener"
                            title="View Invoice"
                          >
                            <Visibility />
                          </IconButton>
                        )}
                        {invoice.invoicePdfUrl && (
                          <IconButton
                            size="small"
                            component="a"
                            href={invoice.invoicePdfUrl}
                            target="_blank"
                            rel="noopener"
                            title="Download PDF"
                          >
                            <Download />
                          </IconButton>
                        )}
                      </Box>
                    </TableCell>
                    <TableCell>
                      {invoice.lineItems && invoice.lineItems.length > 0 && (
                        <IconButton
                          size="small"
                          onClick={() => handleExpandClick(invoice.id)}
                          title="View Details"
                        >
                          {expandedInvoice === invoice.id ? <ExpandLess /> : <ExpandMore />}
                        </IconButton>
                      )}
                    </TableCell>
                  </TableRow>

                  {/* Expanded Details */}
                  {invoice.lineItems && invoice.lineItems.length > 0 && (
                    <TableRow>
                      <TableCell colSpan={6} sx={{ p: 0, border: 'none' }}>
                        <Collapse in={expandedInvoice === invoice.id}>
                          <Box sx={{ p: 2, bgcolor: 'grey.50' }}>
                            <Typography variant="subtitle2" gutterBottom>
                              Invoice Details
                            </Typography>

                            {/* Line Items */}
                            <Box sx={{ mb: 2 }}>
                              {invoice.lineItems.map((lineItem: any, index: number) => (
                                <Box
                                  key={index}
                                  sx={{
                                    display: 'flex',
                                    justifyContent: 'space-between',
                                    alignItems: 'center',
                                    py: 0.5,
                                    borderBottom: index < invoice.lineItems.length - 1 ? 1 : 0,
                                    borderColor: 'divider'
                                  }}
                                >
                                  <Box>
                                    <Typography variant="body2">
                                      {lineItem.description}
                                    </Typography>
                                    {lineItem.periodStart && lineItem.periodEnd && (
                                      <Typography variant="caption" color="text.secondary">
                                        {format(new Date(lineItem.periodStart), 'MMM dd')} -{' '}
                                        {format(new Date(lineItem.periodEnd), 'MMM dd, yyyy')}
                                      </Typography>
                                    )}
                                  </Box>
                                  <Typography variant="body2">
                                    {lineItem.quantity > 1 && `${lineItem.quantity} × `}
                                    {formatCurrency(lineItem.unitAmount, lineItem.currency)}
                                  </Typography>
                                </Box>
                              ))}
                            </Box>

                            {/* Totals */}
                            <Box sx={{ borderTop: 1, borderColor: 'divider', pt: 1 }}>
                              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                                <Typography variant="body2">Subtotal:</Typography>
                                <Typography variant="body2">
                                  {formatCurrency(invoice.subtotal, invoice.currency)}
                                </Typography>
                              </Box>

                              {invoice.tax > 0 && (
                                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                                  <Typography variant="body2">Tax:</Typography>
                                  <Typography variant="body2">
                                    {formatCurrency(invoice.tax, invoice.currency)}
                                  </Typography>
                                </Box>
                              )}

                              {invoice.discount > 0 && (
                                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                                  <Typography variant="body2" color="success.main">Discount:</Typography>
                                  <Typography variant="body2" color="success.main">
                                    -{formatCurrency(invoice.discount, invoice.currency)}
                                  </Typography>
                                </Box>
                              )}

                              <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 1, pt: 1, borderTop: 1, borderColor: 'divider' }}>
                                <Typography variant="subtitle2">Total:</Typography>
                                <Typography variant="subtitle2" sx={{ fontWeight: 'bold' }}>
                                  {formatCurrency(invoice.total, invoice.currency)}
                                </Typography>
                              </Box>
                            </Box>

                            {/* Payment Information */}
                            {invoice.paidAt && (
                              <Box sx={{ mt: 2, p: 1, bgcolor: 'success.50', borderRadius: 1 }}>
                                <Typography variant="body2" color="success.main">
                                  Paid on {format(new Date(invoice.paidAt), 'MMM dd, yyyy')}
                                </Typography>
                              </Box>
                            )}
                          </Box>
                        </Collapse>
                      </TableCell>
                    </TableRow>
                  )}
                </React.Fragment>
              ))}
            </TableBody>
          </Table>
        </TableContainer>

        {/* Summary */}
        <Box sx={{ mt: 2, p: 2, bgcolor: 'grey.50', borderRadius: 1 }}>
          <Typography variant="body2" color="text.secondary">
            Showing {displayInvoices.length} of {invoices.length} invoice{invoices.length !== 1 ? 's' : ''}
          </Typography>
        </Box>
      </CardContent>
    </Card>
  );
};

export default InvoiceHistory;