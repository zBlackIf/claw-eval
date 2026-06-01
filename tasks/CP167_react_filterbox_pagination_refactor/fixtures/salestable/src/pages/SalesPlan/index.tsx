// 引入antd组件
import {
  Spin,
  Modal,
  Col,
  Button,
  Form,
  Row,
  Input,
  Table,
  Cascader,
  Select,
  DatePicker,
  message
} from 'antd';
import { PlusOutlined, LeftOutlined, DownOutlined, UpOutlined } from '@ant-design/icons';

// 引入公共的组件
import PageTitle from '@/components/commonTools/PageTitle';
import React, {
  FunctionComponent,
  useEffect,
  useState,
  useRef,
  Ref,
  forwardRef,
  createRef,
  useCallback,
  useMemo
} from 'react';

import './index.less'
import MyPagination from '@/components/commonTools/MyPagination';
import { getFormatNameList, getSecondFormatNameList } from '@/services/productOpenList';
import moment from 'moment';
import ResizableTable from '@/components/commonTools/ResizableTable';
import { timeFormat } from "@/utils/constants";
import MyCard from '@/components/commonTools/MyCard';

import { getFilterResultListSalesPlan, getSalesPlanList, postSalesPlanListExport } from '@/services/salesPlan';
import DebounceSelect from '@/components/commonTools/DebounceSelect';
import { history } from '@/utils/router'
import { bo_query_mainpart } from '@/services/batchoperate';
const { RangePicker } = DatePicker

type RangeValue = [moment.Moment, moment.Moment];

const SalePlan: FunctionComponent<any> = forwardRef((props, ref) => {
  const [pagination, setPagination] = useState({
    limit: 20,
    currPage: 1,
    total: 0,
    totalNum: 0
  })
  const [dataSource, setDataSource] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [moreFilter, setMoreFilter] = useState(false);
  const [filterData, setFilterData] = useState<any>({});
  const [archiveTime, setArchiveTime] = useState<RangeValue>([moment().startOf('month'), moment().endOf('month')]);
  const [customerNameValue, setCustomerNameValue] = useState('');
  const [salesValue, setSalesValue] = useState('');
  const [firstFormatOptions, setFirstFormatOptions] = useState<any[]>([]);
  const [secondFormatOptions, setSecondFormatOptions] = useState<any[]>([]);
  const [mainPartOptions, setMainPartOptions] = useState<any[]>([]);

  const customerNameRef = useRef<any>(null);
  const salesRef = useRef<any>(null);

  const goDetail = useCallback((record: any, activeTab?: string) => {
    sessionStorage.setItem('salesPlanPage', JSON.stringify({ pagination, filterData }));
    history.push({
      pathname: `/salesPlan/salesPlanDetail/${record.planCode}`,
      resourceId: 'salesPlanDetail',
      query: {
        serialCode: record.serialCode || '',
        activeTab: activeTab || 'basic'
      }
    })
  }, [pagination])

  const columns: any = useMemo(() => [
    {
      title: '订单号',
      dataIndex: 'planCode',
      key: 'planCode',
      render: (text: any, record: any) => (
        <div className="table-item-link" onClick={() => goDetail(record)}>{text}</div>
      ),
      width: 160
    },
    {
      title: '方案名称',
      dataIndex: 'planName',
      key: 'planName',
      ellipsis: true,
      render: (text: any, record: any) => (
        <div className='table-item-link-normal' onClick={() => goDetail(record)}>{text}</div>
      ),
      width: '20em'
    },
    {
      title: '集团号',
      dataIndex: 'groupCode',
      key: 'groupCode',
    },
    {
      title: '集团名称',
      dataIndex: 'groupName',
      key: 'groupName',
    },
    {
      title: '客户名称',
      dataIndex: 'customName',
      key: 'customName',
    },
    {
      title: '所属服务商',
      dataIndex: 'servicerName',
      key: 'servicerName',
    },
    {
      title: '项目所属人',
      dataIndex: 'projectOwner',
      key: 'projectOwner',
    },
    {
      title: '一级业态',
      dataIndex: 'firstFormat',
      key: 'firstFormat',
    },
    {
      title: '二级业态',
      dataIndex: 'secondFormat',
      key: 'secondFormat',
    },
    {
      title: '销售主体',
      dataIndex: 'mainPart',
      key: 'mainPart',
    },
    {
      title: '审批状态',
      dataIndex: 'authStatusName',
      key: 'authStatusName',
    },
    {
      title: '创建时间',
      dataIndex: 'createTime',
      key: 'createTime',
      width: 180
    },
  ], [goDetail])

  // 获取列表数据
  const getList = async (page?: number, limit?: number) => {
    setIsLoading(true);
    try {
      const params = {
        currPage: page || pagination.currPage,
        limit: limit || pagination.limit,
        ...filterData,
      };
      const res = await getSalesPlanList(params);
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
    loadFilterOptions();
  }, []);

  // 加载筛选选项
  const loadFilterOptions = async () => {
    const [formatRes, mainPartRes] = await Promise.all([
      getFormatNameList(),
      bo_query_mainpart(),
    ]);
    if (formatRes?.success) {
      setFirstFormatOptions(formatRes.data || []);
    }
    if (mainPartRes?.success) {
      setMainPartOptions(mainPartRes.data || []);
    }
  };

  // 查询
  const handleSearch = () => {
    const values: any = {};
    if (archiveTime?.[0] && archiveTime?.[1]) {
      values.startTime = archiveTime[0].format(timeFormat);
      values.endTime = archiveTime[1].format(timeFormat);
    }
    if (customerNameValue) values.customName = customerNameValue;
    if (salesValue) values.salesName = salesValue;
    setFilterData(values);
    setPagination(prev => ({ ...prev, currPage: 1 }));
    getList(1);
  };

  // 重置
  const handleReset = () => {
    setArchiveTime([moment().startOf('month'), moment().endOf('month')]);
    setCustomerNameValue('');
    setSalesValue('');
    setFilterData({});
    setPagination(prev => ({ ...prev, currPage: 1 }));
    getList(1);
  };

  // 导出
  const handleExport = async () => {
    try {
      await postSalesPlanListExport(filterData);
      message.success('导出成功');
    } catch (e) {
      message.error('导出失败');
    }
  };

  // 分页切换
  const changePage = (page: number, limit: number) => {
    setPagination(prev => ({ ...prev, currPage: page, limit }));
    getList(page, limit);
  };

  return (
    <div className='sales-plan-page'>
      <PageTitle title='销售方案' />

      {/* 筛选区域 */}
      <MyCard>
        <Form layout="horizontal">
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item label="客户名称">
                <DebounceSelect
                  ref={customerNameRef}
                  value={customerNameValue}
                  onChange={(val: string) => setCustomerNameValue(val)}
                  fetchOptions={getFilterResultListSalesPlan}
                  placeholder="请输入客户名称"
                />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item label="销售">
                <DebounceSelect
                  ref={salesRef}
                  value={salesValue}
                  onChange={(val: string) => setSalesValue(val)}
                  fetchOptions={getFilterResultListSalesPlan}
                  placeholder="请输入销售"
                />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item label="创建时间">
                <RangePicker
                  value={archiveTime}
                  onChange={(dates) => setArchiveTime(dates as RangeValue)}
                  format={timeFormat}
                />
              </Form.Item>
            </Col>
          </Row>
          {moreFilter && (
            <Row gutter={16}>
              <Col span={8}>
                <Form.Item label="一级业态">
                  <Select
                    allowClear
                    placeholder="请选择一级业态"
                    options={firstFormatOptions.map(item => ({ label: item.name, value: item.id }))}
                    onChange={async (val) => {
                      if (val) {
                        const res = await getSecondFormatNameList(val);
                        if (res?.success) setSecondFormatOptions(res.data || []);
                      } else {
                        setSecondFormatOptions([]);
                      }
                    }}
                  />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item label="二级业态">
                  <Select
                    allowClear
                    placeholder="请选择二级业态"
                    options={secondFormatOptions.map(item => ({ label: item.name, value: item.id }))}
                  />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item label="销售主体">
                  <Select
                    allowClear
                    placeholder="请选择销售主体"
                    options={mainPartOptions.map(item => ({ label: item.name, value: item.code }))}
                  />
                </Form.Item>
              </Col>
            </Row>
          )}
          <Row>
            <Col span={24} style={{ textAlign: 'right' }}>
              <Button type="primary" onClick={handleSearch}>查询</Button>
              <Button style={{ marginLeft: 8 }} onClick={handleReset}>重置</Button>
              <Button
                type="link"
                onClick={() => setMoreFilter(!moreFilter)}
                icon={moreFilter ? <UpOutlined /> : <DownOutlined />}
              >
                {moreFilter ? '收起' : '展开'}
              </Button>
            </Col>
          </Row>
        </Form>
      </MyCard>

      {/* 操作按钮 */}
      <div style={{ margin: '16px 0', display: 'flex', justifyContent: 'flex-end' }}>
        <Button onClick={handleExport}>导出</Button>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => history.push('/salesPlan/newSalesPlan')}
        >
          新建销售方案
        </Button>
      </div>

      {/* 表格 */}
      <Spin spinning={isLoading}>
        <ResizableTable
          columns={columns}
          dataSource={dataSource}
          rowKey="planCode"
          scroll={{ x: 1200 }}
          pagination={false}
        />
      </Spin>

      {/* 分页 */}
      <MyPagination
        page={pagination.currPage}
        total={pagination.total}
        limit={pagination.limit}
        changePage={changePage}
      />
    </div>
  )
})

export default SalePlan;
