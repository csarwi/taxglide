import React, { useState, useMemo } from 'react';
import { theme, createInputStyle } from '../theme';

// Generic table column definition
export interface TableColumn<T> {
  key: keyof T;
  label: string;
  sortable?: boolean;
  filterable?: boolean;
  render?: (value: any, row: T) => React.ReactNode;
  align?: 'left' | 'center' | 'right';
  width?: string;
}

interface DataTableProps<T> {
  data: T[];
  columns: TableColumn<T>[];
  searchable?: boolean;
  searchPlaceholder?: string;
  className?: string;
  maxHeight?: string;
}

type SortDirection = 'asc' | 'desc' | null;

function DataTable<T extends Record<string, any>>({
  data,
  columns,
  searchable = true,
  searchPlaceholder = "Search...",
  className = "",
  maxHeight = "60vh"
}: DataTableProps<T>) {
  const [searchTerm, setSearchTerm] = useState("");
  const [sortColumn, setSortColumn] = useState<keyof T | null>(null);
  const [sortDirection, setSortDirection] = useState<SortDirection>(null);
  const [columnFilters, setColumnFilters] = useState<Record<keyof T, string>>({} as Record<keyof T, string>);

  // Filter and search data
  const filteredData = useMemo(() => {
    let filtered = data;

    // Apply search filter
    if (searchTerm) {
      const searchLower = searchTerm.toLowerCase();
      filtered = filtered.filter(row =>
        columns.some(col => {
          const value = row[col.key];
          if (value == null) return false;
          return String(value).toLowerCase().includes(searchLower);
        })
      );
    }

    // Apply column filters
    Object.entries(columnFilters).forEach(([key, filterValue]) => {
      if (filterValue) {
        const filterLower = filterValue.toLowerCase();
        filtered = filtered.filter(row => {
          const value = row[key as keyof T];
          if (value == null) return false;
          return String(value).toLowerCase().includes(filterLower);
        });
      }
    });

    return filtered;
  }, [data, searchTerm, columnFilters, columns]);

  // Sort data
  const sortedData = useMemo(() => {
    if (!sortColumn || !sortDirection) return filteredData;

    return [...filteredData].sort((a, b) => {
      const aVal = a[sortColumn];
      const bVal = b[sortColumn];

      // Handle null/undefined values
      if (aVal == null && bVal == null) return 0;
      if (aVal == null) return 1;
      if (bVal == null) return -1;

      // Numeric comparison
      if (typeof aVal === 'number' && typeof bVal === 'number') {
        return sortDirection === 'asc' ? aVal - bVal : bVal - aVal;
      }

      // String comparison
      const aStr = String(aVal).toLowerCase();
      const bStr = String(bVal).toLowerCase();
      
      if (sortDirection === 'asc') {
        return aStr < bStr ? -1 : aStr > bStr ? 1 : 0;
      } else {
        return aStr > bStr ? -1 : aStr < bStr ? 1 : 0;
      }
    });
  }, [filteredData, sortColumn, sortDirection]);

  // Handle column header click for sorting
  const handleSort = (column: TableColumn<T>) => {
    if (!column.sortable) return;

    if (sortColumn === column.key) {
      // Cycle through: asc -> desc -> null
      if (sortDirection === 'asc') {
        setSortDirection('desc');
      } else if (sortDirection === 'desc') {
        setSortColumn(null);
        setSortDirection(null);
      }
    } else {
      setSortColumn(column.key);
      setSortDirection('asc');
    }
  };

  // Handle column filter change
  const handleColumnFilterChange = (columnKey: keyof T, value: string) => {
    setColumnFilters(prev => ({
      ...prev,
      [columnKey]: value
    }));
  };

  // Get sort indicator
  const getSortIndicator = (column: TableColumn<T>) => {
    if (!column.sortable) return null;
    if (sortColumn !== column.key) return '↕️';
    return sortDirection === 'asc' ? '↑' : '↓';
  };

  return (
    <div className={className} style={{ display: 'flex', flexDirection: 'column', gap: theme.spacing.md }}>
      {/* Search Input */}
      {searchable && (
        <div style={{ display: 'flex', alignItems: 'center', gap: theme.spacing.md }}>
          <div style={{ flex: 1 }}>
            <input
              type="text"
              placeholder={searchPlaceholder}
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              style={{
                ...createInputStyle(),
                fontSize: theme.fontSizes.sm,
              }}
            />
          </div>
          <div style={{
            fontSize: theme.fontSizes.sm,
            color: theme.colors.textSecondary,
            minWidth: 'max-content',
          }}>
            Showing {sortedData.length} of {data.length} rows
          </div>
        </div>
      )}

      {/* Table Container */}
      <div style={{
        maxHeight,
        overflowY: 'auto',
        border: `1px solid ${theme.colors.gray300}`,
        borderRadius: theme.borderRadius.md,
        backgroundColor: theme.colors.background,
      }}>
        <table style={{
          width: '100%',
          borderCollapse: 'collapse',
          fontSize: theme.fontSizes.sm,
        }}>
          {/* Table Head */}
          <thead style={{
            backgroundColor: theme.colors.backgroundSecondary,
            position: 'sticky',
            top: 0,
            zIndex: 1,
          }}>
            <tr>
              {columns.map(column => (
                <th
                  key={String(column.key)}
                  style={{
                    padding: `${theme.spacing.sm} ${theme.spacing.md}`,
                    textAlign: column.align || 'left',
                    fontWeight: '600',
                    color: theme.colors.text,
                    borderBottom: `2px solid ${theme.colors.gray300}`,
                    cursor: column.sortable ? 'pointer' : 'default',
                    userSelect: 'none',
                    width: column.width,
                    minWidth: column.width,
                  }}
                  onClick={() => handleSort(column)}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: column.align === 'right' ? 'flex-end' : column.align === 'center' ? 'center' : 'flex-start', gap: theme.spacing.xs }}>
                    <span>{column.label}</span>
                    {column.sortable && (
                      <span style={{ opacity: 0.7, fontSize: theme.fontSizes.xs }}>
                        {getSortIndicator(column)}
                      </span>
                    )}
                  </div>
                </th>
              ))}
            </tr>
            
            {/* Filter Row */}
            {columns.some(col => col.filterable) && (
              <tr>
                {columns.map(column => (
                  <th
                    key={`filter-${String(column.key)}`}
                    style={{
                      padding: `${theme.spacing.xs} ${theme.spacing.md}`,
                      borderBottom: `1px solid ${theme.colors.gray300}`,
                      backgroundColor: theme.colors.backgroundTertiary,
                    }}
                  >
                    {column.filterable && (
                      <input
                        type="text"
                        placeholder={`Filter ${column.label.toLowerCase()}...`}
                        value={columnFilters[column.key] || ''}
                        onChange={(e) => handleColumnFilterChange(column.key, e.target.value)}
                        style={{
                          ...createInputStyle(),
                          fontSize: theme.fontSizes.xs,
                          padding: `${theme.spacing.xs} ${theme.spacing.sm}`,
                          margin: 0,
                        }}
                      />
                    )}
                  </th>
                ))}
              </tr>
            )}
          </thead>

          {/* Table Body */}
          <tbody>
            {sortedData.length === 0 ? (
              <tr>
                <td
                  colSpan={columns.length}
                  style={{
                    padding: theme.spacing.xl,
                    textAlign: 'center',
                    color: theme.colors.textSecondary,
                    fontSize: theme.fontSizes.md,
                  }}
                >
                  {data.length === 0 ? 'No data available' : 'No matching results'}
                </td>
              </tr>
            ) : (
              sortedData.map((row, index) => (
                <tr
                  key={index}
                  style={{
                    backgroundColor: index % 2 === 0 ? theme.colors.background : theme.colors.backgroundSecondary,
                  }}
                  onMouseEnter={(e) => {
                    (e.currentTarget as HTMLTableRowElement).style.backgroundColor = theme.colors.gray100;
                  }}
                  onMouseLeave={(e) => {
                    (e.currentTarget as HTMLTableRowElement).style.backgroundColor = 
                      index % 2 === 0 ? theme.colors.background : theme.colors.backgroundSecondary;
                  }}
                >
                  {columns.map(column => (
                    <td
                      key={String(column.key)}
                      style={{
                        padding: `${theme.spacing.sm} ${theme.spacing.md}`,
                        textAlign: column.align || 'left',
                        borderBottom: `1px solid ${theme.colors.gray200}`,
                        fontFamily: typeof row[column.key] === 'number' ? theme.fonts.mono : theme.fonts.body,
                      }}
                    >
                      {column.render ? 
                        column.render(row[column.key], row) : 
                        row[column.key] != null ? String(row[column.key]) : '—'
                      }
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Footer with stats */}
      {data.length > 0 && (
        <div style={{
          fontSize: theme.fontSizes.xs,
          color: theme.colors.textSecondary,
          textAlign: 'center',
        }}>
          {sortedData.length !== data.length && `${sortedData.length} filtered results from `}
          {data.length} total rows
          {searchTerm && ` • Search: "${searchTerm}"`}
          {Object.values(columnFilters).some(Boolean) && ` • Filters applied`}
        </div>
      )}
    </div>
  );
}

export default DataTable;
