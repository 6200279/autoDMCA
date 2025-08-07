import React from 'react';
import {
  Chart as ChartJS,
  ArcElement,
  Tooltip,
  Legend,
} from 'chart.js';
import { Doughnut } from 'react-chartjs-2';
import { Box, useTheme, alpha } from '@mui/material';

ChartJS.register(ArcElement, Tooltip, Legend);

interface PlatformData {
  platform: string;
  count: number;
}

interface PlatformDistributionProps {
  data?: PlatformData[];
}

const PlatformDistribution: React.FC<PlatformDistributionProps> = ({ data }) => {
  const theme = useTheme();

  // Default data for when no data is available
  const defaultData: PlatformData[] = [
    { platform: 'YouTube', count: 45 },
    { platform: 'Instagram', count: 23 },
    { platform: 'TikTok', count: 18 },
    { platform: 'Facebook', count: 12 },
    { platform: 'Other', count: 8 },
  ];

  const platformData = data || defaultData;

  // Generate colors for each platform
  const colors = [
    theme.palette.error.main,
    theme.palette.warning.main,
    theme.palette.info.main,
    theme.palette.success.main,
    theme.palette.primary.main,
  ];

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'bottom' as const,
        labels: {
          usePointStyle: true,
          padding: 15,
          color: theme.palette.text.primary,
          font: {
            size: 11,
            weight: '500',
          },
        },
      },
      tooltip: {
        backgroundColor: alpha(theme.palette.background.paper, 0.95),
        titleColor: theme.palette.text.primary,
        bodyColor: theme.palette.text.primary,
        borderColor: theme.palette.divider,
        borderWidth: 1,
        cornerRadius: 8,
        callbacks: {
          label: (context: any) => {
            const total = context.dataset.data.reduce((a: number, b: number) => a + b, 0);
            const percentage = ((context.raw / total) * 100).toFixed(1);
            return `${context.label}: ${context.raw} (${percentage}%)`;
          },
        },
      },
    },
    cutout: '65%',
    elements: {
      arc: {
        borderWidth: 2,
        borderColor: theme.palette.background.paper,
      },
    },
  };

  const chartData = {
    labels: platformData.map(item => item.platform),
    datasets: [
      {
        data: platformData.map(item => item.count),
        backgroundColor: colors.map(color => alpha(color, 0.8)),
        borderColor: colors,
        borderWidth: 2,
        hoverBackgroundColor: colors.map(color => alpha(color, 0.9)),
        hoverBorderWidth: 3,
      },
    ],
  };

  return (
    <Box sx={{ height: 220, width: '100%', position: 'relative' }}>
      <Doughnut options={options} data={chartData} />
      
      {/* Center text */}
      <Box
        sx={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          textAlign: 'center',
          pointerEvents: 'none',
        }}
      >
        <Box sx={{ fontSize: '1.5rem', fontWeight: 700, color: theme.palette.text.primary }}>
          {platformData.reduce((sum, item) => sum + item.count, 0)}
        </Box>
        <Box sx={{ fontSize: '0.75rem', color: theme.palette.text.secondary, mt: -0.5 }}>
          Total
        </Box>
      </Box>
    </Box>
  );
};

export default PlatformDistribution;