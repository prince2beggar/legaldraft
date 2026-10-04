/**
 * AIN-AI ResponsiveTable Component (ADR-018)
 * Automatically converts traditional multi-column tables into stacked, readable cards
 * on mobile (< 640px) to prevent horizontal scrolling, while rendering a clean table on tablet/desktop.
 */

import React from 'react';
import { colors, radius } from '../tokens';

export interface ColumnDef<T> {
  key: string;
  headerBn: string;
  headerEn: string;
  render?: (row: T) => React.ReactNode;
  width?: string;
}

export interface ResponsiveTableProps<T> {
  data: T[];
  columns: ColumnDef<T>[];
  lang?: 'bn' | 'en';
  keyField: keyof T;
  emptyMessageBn?: string;
  emptyMessageEn?: string;
  onRowClick?: (row: T) => void;
}

export function ResponsiveTable<T extends Record<string, any>>({
  data,
  columns,
  lang = 'bn',
  keyField,
  emptyMessageBn = 'কোনো তথ্য পাওয়া যায়নি।',
  emptyMessageEn = 'No records found.',
  onRowClick,
}: ResponsiveTableProps<T>) {
  if (data.length === 0) {
    return (
      <div className="ain-table-empty">
        <p>{lang === 'bn' ? emptyMessageBn : emptyMessageEn}</p>
        <style>{`
          .ain-table-empty {
            padding: 3rem 1rem;
            text-align: center;
            background: #ffffff;
            border: 1px dashed ${colors.neutral.border};
            border-radius: ${radius.card};
            color: ${colors.neutral.textMuted};
            font-size: 1rem;
          }
        `}</style>
      </div>
    );
  }

  return (
    <div className="ain-table-wrapper">
      {/* Desktop & Tablet Table (>= 640px) */}
      <table className="ain-desktop-table" role="table">
        <thead>
          <tr>
            {columns.map((col) => (
              <th key={col.key} style={{ width: col.width }} scope="col">
                {lang === 'bn' ? col.headerBn : col.headerEn}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row) => (
            <tr
              key={String(row[keyField])}
              onClick={() => onRowClick && onRowClick(row)}
              className={onRowClick ? 'clickable' : ''}
            >
              {columns.map((col) => (
                <td key={col.key}>
                  {col.render ? col.render(row) : String(row[col.key] ?? '')}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>

      {/* Mobile Stacked Card View (< 640px) */}
      <div className="ain-mobile-cards" role="list">
        {data.map((row) => (
          <div
            key={String(row[keyField])}
            className={`ain-mobile-card ${onRowClick ? 'clickable' : ''}`}
            onClick={() => onRowClick && onRowClick(row)}
            role="listitem"
            tabIndex={onRowClick ? 0 : undefined}
          >
            {columns.map((col) => (
              <div key={col.key} className="ain-card-field">
                <span className="ain-card-label">
                  {lang === 'bn' ? col.headerBn : col.headerEn}:
                </span>
                <span className="ain-card-value">
                  {col.render ? col.render(row) : String(row[col.key] ?? '')}
                </span>
              </div>
            ))}
          </div>
        ))}
      </div>

      <style>{`
        .ain-table-wrapper {
          width: 100%;
          overflow-x: hidden;
        }

        /* Desktop/Tablet Table */
        .ain-desktop-table {
          width: 100%;
          border-collapse: separate;
          border-spacing: 0;
          background: #ffffff;
          border: 1px solid ${colors.neutral.border};
          border-radius: ${radius.card};
          overflow: hidden;
        }

        .ain-desktop-table th {
          background-color: ${colors.neutral.bg};
          color: ${colors.neutral.textMuted};
          font-weight: 600;
          font-size: 0.875rem;
          text-align: left;
          padding: 0.875rem 1.25rem;
          border-bottom: 1px solid ${colors.neutral.border};
        }

        .ain-desktop-table td {
          padding: 1rem 1.25rem;
          border-bottom: 1px solid ${colors.neutral.border};
          font-size: 0.95rem;
          color: ${colors.neutral.textMain};
        }

        .ain-desktop-table tr:last-child td {
          border-bottom: none;
        }

        .ain-desktop-table tr.clickable {
          cursor: pointer;
          transition: background-color 0.15s ease;
        }

        .ain-desktop-table tr.clickable:hover {
          background-color: ${colors.primarySoft};
        }

        /* Mobile Cards Hidden on Desktop */
        .ain-mobile-cards {
          display: none;
        }

        /* Mobile Breakpoint (< 640px) */
        @media (max-width: 639px) {
          .ain-desktop-table {
            display: none;
          }

          .ain-mobile-cards {
            display: flex;
            flex-direction: column;
            gap: 0.75rem;
            width: 100%;
          }

          .ain-mobile-card {
            background: #ffffff;
            border: 1px solid ${colors.neutral.border};
            border-radius: ${radius.card};
            padding: 1rem;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
          }

          .ain-mobile-card.clickable {
            cursor: pointer;
            touch-action: manipulation;
          }

          .ain-mobile-card.clickable:active {
            background-color: ${colors.neutral.bg};
          }

          .ain-card-field {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 0.5rem;
            font-size: 0.9rem;
            padding-bottom: 0.35rem;
            border-bottom: 1px dashed #f1f5f9;
          }

          .ain-card-field:last-child {
            border-bottom: none;
            padding-bottom: 0;
          }

          .ain-card-label {
            font-weight: 600;
            color: ${colors.neutral.textMuted};
            flex-shrink: 0;
            max-width: 40%;
          }

          .ain-card-value {
            color: ${colors.neutral.textMain};
            text-align: right;
            word-break: break-word;
          }
        }
      `}</style>
    </div>
  );
}
