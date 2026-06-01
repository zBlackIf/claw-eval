import PageTitle from "@/components/commonTools/PageTitle";
import { PlusOutlined } from "@ant-design/icons";
import { Button, DatePicker } from "antd";
import { FunctionComponent, useEffect, useState, useRef } from "react";
import './index.less'
import moment from "moment";
import { exportInsideApproval, getFilterResultList, getInsideApprovalList } from "@/services/createdApproval";
import { timeFormat } from "@/utils/constants";
import DebounceSelect from "@/components/commonTools/DebounceSelect";
import ExportBtn from "@/components/commonTools/ExportBtn";
import FilterBox, { FilterItemConfig } from '@/components/commonTools/FilterBox';
import MyPaginationV2 from '@/components/commonTools/MyPagination/MyPaginationV2';
import ResizableTable from '@/components/commonTools/ResizableTable';
import { useResizeHeight } from '@/hooks/useResizeHeight';

const { RangePicker } = DatePicker;

type RangeValue = [moment.Moment, moment.Moment];

const insideApproval: FunctionComponent = () => {
  const [dataSource, setDataSource] = useState<any[]>([]);
  const [pagination, setPagination] = useState({
    limit: 20,
    currPage: 1,
    total: 0,
    totalNum: 0
  });
  const [isLoading, setIsLoading] = useState(true);
  const [filterData, setFilterData] = useState<any>({});
  const [filterH, setFilterH] = useState(0);
  const [filterValues, setFilterValues] = useState<any>({});
  const [formActions, setFormActions] = useState<any>(null);

  useResizeHeight('inside-approval-filter', (_h) => {
    setFilterH(_h);
  });

  const filterItems: FilterItemConfig[] = [
    {
      name: 'customerName',
      label: '客户名称',
      type: 'custom',
      render: (form) => (
        <DebounceSelect
          value={filterValues.customerName}
          onChange={(val: string) => setFilterValues((prev: any) => ({ ...prev, customerName: val }))}
          fetchOptions={getFilterResultList}
          placeholder="请输入客户名称"
        />
      ),
    },
    {
      name: 'salesName',
      label: '销售',
      type: 'custom',
      render: (form) => (
        <DebounceSelect
          value={filterValues.salesName}
          onChange={(val: string) => setFilterValues((prev: any) => ({ ...prev, salesName: val }))}
          fetchOptions={getFilterResultList}
          placeholder="请输入销售"
        />
      ),
    },
    {
      name: 'archiveTime',
      label: '创建时间',
      type: 'custom',
      render: (form) => (
        <RangePicker
          value={filterValues.archiveTime}
          onChange={(dates) => setFilterValues((prev: any) => ({ ...prev, archiveTime: dates }))}
          format={timeFormat}
        />
      ),
    },
  ];

  const handleSearch = (values: any) => {
    const params: any = {};
    if (filterValues.customerName) params.customName = filterValues.customerName;
    if (filterValues.salesName) params.salesName = filterValues.salesName;
    if (filterValues.archiveTime?.[0] && filterValues.archiveTime?.[1]) {
      params.startTime = filterValues.archiveTime[0].format(timeFormat);
      params.endTime = filterValues.archiveTime[1].format(timeFormat);
    }
    setFilterData(params);
    setPagination(prev => ({ ...prev, currPage: 1 }));
    getList(1);
  };

  const handleReset = () => {
    setFilterValues({});
    setFilterData({});
    setPagination(prev => ({ ...prev, currPage: 1 }));
    getList(1);
  };

  const getList = async (page?: number, limit?: number) => {
    setIsLoading(true);
    try {
      const params = {
        currPage: page || pagination.currPage,
        limit: limit || pagination.limit,
        ...filterData,
      };
      const res = await getInsideApprovalList(params);
      if (res?.success) {
        setDataSource(res.data?.records || []);
        setPagination(prev => ({
          ...prev,
          total: res.data?.total || 0,
          totalNum: res.data?.totalNum || 0,
          currPage: page || prev.currPage,
          limit: limit || prev.limit,
        }));
      }
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    getList();
  }, []);

  const columns = [
    { title: '流程单号', dataIndex: 'processOrder', key: 'processOrder', width: 160 },
    { title: '客户名称', dataIndex: 'customerName', key: 'customerName' },
    { title: '审批状态', dataIndex: 'approvalStatus', key: 'approvalStatus' },
    { title: '创建时间', dataIndex: 'createTime', key: 'createTime', width: 180 },
  ];

  const changePage = (page: number, pageSize: number) => {
    setPagination(prev => ({ ...prev, currPage: page, limit: pageSize }));
    getList(page, pageSize);
  };

  const tableScrollY = `calc(100vh - ${filterH + 180}px)`;

  return (
    <div className="inside-approval-page">
      <PageTitle title="内部审批" />

      <FilterBox
        compId="inside-approval-filter"
        filterItems={filterItems}
        onSearch={handleSearch}
        onReset={handleReset}
        loading={isLoading}
        collapsible={true}
        defaultExpanded={true}
        collapsedRows={2}
        getFormActions={setFormActions}
        extraActions={
          <>
            <ExportBtn onExport={() => exportInsideApproval(filterData)} />
            <Button type="primary" icon={<PlusOutlined />}>
              新建审批
            </Button>
          </>
        }
      />

      <ResizableTable
        columns={columns}
        dataSource={dataSource}
        rowKey="processOrder"
        loading={isLoading}
        size="small"
        scroll={{ x: 1200, y: tableScrollY }}
        pagination={false}
      />

      <MyPaginationV2
        current={pagination.currPage}
        total={pagination.total}
        pageSize={pagination.limit}
        onChange={changePage}
      />
    </div>
  );
};

export default insideApproval;
