import { useState, useEffect, useCallback, useMemo } from 'react';

interface UseVirtualGridOptions {
  itemCount: number;
  containerHeight: number;
  containerWidth: number;
  itemMinWidth: number;
  itemHeight: number;
  gap?: number;
  overscan?: number;
}

interface VirtualGridItem {
  index: number;
  x: number;
  y: number;
  width: number;
  height: number;
}

export const useVirtualGrid = (options: UseVirtualGridOptions) => {
  const {
    itemCount,
    containerHeight,
    containerWidth,
    itemMinWidth,
    itemHeight,
    gap = 16,
    overscan = 5
  } = options;

  const [scrollTop, setScrollTop] = useState(0);

  // Calculate grid dimensions
  const gridMetrics = useMemo(() => {
    if (containerWidth === 0) return null;

    const availableWidth = containerWidth - gap;
    const columnsCount = Math.max(1, Math.floor(availableWidth / (itemMinWidth + gap)));
    const itemWidth = (availableWidth - (columnsCount - 1) * gap) / columnsCount;
    const rowsCount = Math.ceil(itemCount / columnsCount);
    const totalHeight = rowsCount * (itemHeight + gap) - gap;

    return {
      columnsCount,
      rowsCount,
      itemWidth,
      totalHeight
    };
  }, [containerWidth, itemMinWidth, itemHeight, gap, itemCount]);

  // Calculate visible items
  const visibleItems = useMemo(() => {
    if (!gridMetrics) return [];

    const { columnsCount, itemWidth, rowsCount } = gridMetrics;
    const rowHeight = itemHeight + gap;
    
    // Calculate visible row range
    const startRow = Math.max(0, Math.floor(scrollTop / rowHeight) - overscan);
    const endRow = Math.min(
      rowsCount - 1,
      Math.ceil((scrollTop + containerHeight) / rowHeight) + overscan
    );

    const items: VirtualGridItem[] = [];

    for (let row = startRow; row <= endRow; row++) {
      for (let col = 0; col < columnsCount; col++) {
        const index = row * columnsCount + col;
        if (index >= itemCount) break;

        items.push({
          index,
          x: col * (itemWidth + gap),
          y: row * rowHeight,
          width: itemWidth,
          height: itemHeight
        });
      }
    }

    return items;
  }, [
    gridMetrics,
    scrollTop,
    containerHeight,
    itemHeight,
    gap,
    overscan,
    itemCount
  ]);

  const handleScroll = useCallback((event: React.UIEvent<HTMLDivElement>) => {
    setScrollTop(event.currentTarget.scrollTop);
  }, []);

  return {
    visibleItems,
    totalHeight: gridMetrics?.totalHeight || 0,
    columnsCount: gridMetrics?.columnsCount || 0,
    itemWidth: gridMetrics?.itemWidth || 0,
    handleScroll,
    gridStyle: {
      height: containerHeight,
      overflow: 'auto',
      position: 'relative' as const
    },
    containerStyle: {
      height: gridMetrics?.totalHeight || 0,
      position: 'relative' as const
    }
  };
};

export default useVirtualGrid;