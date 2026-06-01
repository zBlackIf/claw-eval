import React, { useState, useMemo, FunctionComponent, useEffect } from 'react';
import { Table } from 'antd';

interface ColumnType {
  width?: number | string;
  [key: string]: any;
}

interface ResizableTableProps {
  columns: ColumnType[];
  onColumnsChange?: (columns: ColumnType[]) => void;
  [key: string]: any;
}

const ResizableTable: FunctionComponent<ResizableTableProps> = ({
  columns,
  onColumnsChange,
  ...restProps
}) => {
  const [columnsState, setColumnsState] = useState(columns);

  useEffect(() => {
    setColumnsState(columns);
  }, [columns]);

  return (
    <Table
      columns={columnsState}
      {...restProps}
    />
  );
};

export default ResizableTable;
