import React, { useState } from 'react';
import { Card } from 'primereact/card';
import { Button } from 'primereact/button';
import { DataTable } from 'primereact/datatable';
import { Column } from 'primereact/column';
import { Tag } from 'primereact/tag';
import { Message } from 'primereact/message';
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
        return 'danger';
      default:
        return null;
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
      <Card className="p-6">
        <div className="flex items-center gap-2 mb-4">
          <i className="pi pi-receipt text-blue-500"></i>
          <h2 className="text-xl font-semibold">Invoice History</h2>
        </div>
        <Message 
          severity="info" 
          text="No invoices found. Invoices will appear here once you have an active subscription." 
        />
      </Card>
    );
  }

  const statusTemplate = (rowData: any) => {
    return (
      <Tag 
        value={rowData.status.toUpperCase()} 
        severity={getStatusColor(rowData.status)} 
      />
    );
  };

  const dateTemplate = (rowData: any) => {
    return (
      <div>
        <div className="font-medium text-sm">
          {format(new Date(rowData.invoiceDate), 'MMM dd, yyyy')}
        </div>
        {rowData.dueDate && rowData.status === 'open' && (
          <div className="text-xs text-gray-500">
            Due: {format(new Date(rowData.dueDate), 'MMM dd, yyyy')}
          </div>
        )}
      </div>
    );
  };

  const amountTemplate = (rowData: any) => {
    return (
      <div className="text-right">
        <div className="font-bold">
          {formatCurrency(rowData.total, rowData.currency)}
        </div>
        {rowData.amountDue > 0 && rowData.status !== 'paid' && (
          <div className="text-xs text-red-500">
            Due: {formatCurrency(rowData.amountDue, rowData.currency)}
          </div>
        )}
      </div>
    );
  };

  const actionsTemplate = (rowData: any) => {
    return (
      <div className="flex justify-center gap-1">
        {rowData.hostedInvoiceUrl && (
          <Button
            icon="pi pi-eye"
            size="small"
            outlined
            onClick={() => window.open(rowData.hostedInvoiceUrl, '_blank')}
            tooltip="View Invoice"
          />
        )}
        {rowData.invoicePdfUrl && (
          <Button
            icon="pi pi-download"
            size="small"
            outlined
            onClick={() => window.open(rowData.invoicePdfUrl, '_blank')}
            tooltip="Download PDF"
          />
        )}
      </div>
    );
  };

  const expandTemplate = (rowData: any) => {
    if (!rowData.lineItems || rowData.lineItems.length === 0) return null;
    
    return (
      <Button
        icon={expandedInvoice === rowData.id ? 'pi pi-chevron-up' : 'pi pi-chevron-down'}
        size="small"
        text
        onClick={() => handleExpandClick(rowData.id)}
      />
    );
  };

  const rowExpansionTemplate = (data: any) => {
    return (
      <div className="p-4 bg-gray-50">
        <h4 className="font-semibold mb-3">Invoice Details</h4>
        
        {/* Line Items */}
        <div className="mb-4">
          {data.lineItems.map((lineItem: any, index: number) => (
            <div
              key={index}
              className={`flex justify-between items-center py-2 ${
                index < data.lineItems.length - 1 ? 'border-b border-gray-200' : ''
              }`}
            >
              <div>
                <div className="text-sm font-medium">
                  {lineItem.description}
                </div>
                {lineItem.periodStart && lineItem.periodEnd && (
                  <div className="text-xs text-gray-500">
                    {format(new Date(lineItem.periodStart), 'MMM dd')} -{' '}
                    {format(new Date(lineItem.periodEnd), 'MMM dd, yyyy')}
                  </div>
                )}
              </div>
              <div className="text-sm">
                {lineItem.quantity > 1 && `${lineItem.quantity} × `}
                {formatCurrency(lineItem.unitAmount, lineItem.currency)}
              </div>
            </div>
          ))}
        </div>

        {/* Totals */}
        <div className="border-t border-gray-300 pt-3 space-y-2">
          <div className="flex justify-between text-sm">
            <span>Subtotal:</span>
            <span>{formatCurrency(data.subtotal, data.currency)}</span>
          </div>
          
          {data.tax > 0 && (
            <div className="flex justify-between text-sm">
              <span>Tax:</span>
              <span>{formatCurrency(data.tax, data.currency)}</span>
            </div>
          )}
          
          {data.discount > 0 && (
            <div className="flex justify-between text-sm text-green-600">
              <span>Discount:</span>
              <span>-{formatCurrency(data.discount, data.currency)}</span>
            </div>
          )}
          
          <div className="flex justify-between font-semibold pt-2 border-t border-gray-200">
            <span>Total:</span>
            <span>{formatCurrency(data.total, data.currency)}</span>
          </div>
        </div>

        {/* Payment Information */}
        {data.paidAt && (
          <div className="mt-4 p-3 bg-green-50 rounded text-sm text-green-700">
            Paid on {format(new Date(data.paidAt), 'MMM dd, yyyy')}
          </div>
        )}
      </div>
    );
  };

  return (
    <Card className="p-6">
      <div className="flex justify-between items-center mb-4">
        <div className="flex items-center gap-2">
          <i className="pi pi-receipt text-blue-500"></i>
          <h2 className="text-xl font-semibold">Invoice History</h2>
        </div>
        {!showAll && invoices.length > 5 && (
          <Button 
            label="View All" 
            size="small" 
            outlined
            onClick={onRefresh}
          />
        )}
      </div>
      
      <DataTable 
        value={displayInvoices}
        expandedRows={expandedInvoice ? {[expandedInvoice]: true} : undefined}
        onRowToggle={(e) => setExpandedInvoice(Object.keys(e.data).length > 0 ? Number(Object.keys(e.data)[0]) : null)}
        rowExpansionTemplate={rowExpansionTemplate}
        responsiveLayout="scroll"
        className="p-datatable-sm"
      >
        <Column 
          field="invoiceNumber" 
          header="Invoice" 
          body={(rowData) => (
            <span className="font-mono text-sm">
              {rowData.invoiceNumber || `INV-${rowData.id}`}
            </span>
          )}
        />
        <Column header="Date" body={dateTemplate} />
        <Column header="Status" body={statusTemplate} />
        <Column header="Amount" body={amountTemplate} />
        <Column header="Actions" body={actionsTemplate} style={{ width: '120px' }} />
        <Column expander body={expandTemplate} style={{ width: '40px' }} />
      </DataTable>

      {/* Summary */}
      <div className="mt-4 p-3 bg-gray-50 rounded text-sm text-gray-600">
        Showing {displayInvoices.length} of {invoices.length} invoice{invoices.length !== 1 ? 's' : ''}
      </div>
    </Card>
  );
};

export default InvoiceHistory;