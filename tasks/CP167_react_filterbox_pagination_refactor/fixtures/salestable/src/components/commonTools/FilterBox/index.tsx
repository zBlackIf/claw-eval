import React, {
  useEffect,
  useState,
  useCallback,
  useImperativeHandle,
  forwardRef,
  ReactNode,
} from 'react';
import { Form, Row, Col, Select, Input, Button, FormInstance } from 'antd';
import { DownOutlined, UpOutlined } from '@ant-design/icons';

const { Option } = Select;

// 筛选项类型
export type FilterItemType = 'select' | 'input' | 'custom';

// 选择项配置
export interface SelectOption {
  label: string;
  value: string | number;
}

// 筛选项配置
export interface FilterItemConfig {
  // 唯一标识
  name: string;
  // 标签名称
  label: string;
  // 筛选项类型
  type: FilterItemType;
  // 占位宽度 (1-24)
  span?: number;
  // 是否显示
  visible?: boolean | (() => boolean);
  // 默认值
  defaultValue?: any;
  // 选择项列表（type为select时使用）
  options?: SelectOption[];
  // 自定义渲染（type为custom时使用）
  render?: (form: FormInstance) => ReactNode;
  // Select组件的onSelect回调
  onSelect?: (value: any, form: FormInstance) => void;
  // Input组件的onChange回调
  onChange?: (e: any, form: FormInstance) => void;
  // 额外的组件属性
  componentProps?: Record<string, any>;
}

// 筛选盒子属性
interface FilterBoxProps {
  compId?: string; // 组件的id
  // 筛选项配置
  filterItems: FilterItemConfig[];
  // 查询回调
  onSearch: (values: any) => void;
  // 重置回调
  onReset?: () => void;
  // 加载状态
  loading?: boolean;
  // 是否显示重置按钮
  showReset?: boolean;
  // 额外的操作按钮
  extraActions?: ReactNode;
  // 表单初始值
  initialValues?: Record<string, any>;
  // 表单值变化回调
  onValuesChange?: (changedValues: any, allValues: any) => void;
  // 每行默认列数（用于计算默认span）
  defaultColsPerRow?: number;
  // 查询按钮文字
  searchText?: string;
  // 重置按钮文字
  resetText?: string;
  // 获取表单操作方法
  getFormActions?: (actions: FormActions) => void;
  // 是否启用展开/收起功能
  collapsible?: boolean;
  // 默认是否展开（true=展开，false=收起）
  defaultExpanded?: boolean;
  // 收起时显示的行数
  collapsedRows?: number;
  // 展开/收起按钮文字
  expandText?: string;
  collapseText?: string;
}

// 表单操作方法
export interface FormActions {
  getFieldsValue: () => any;
  setFieldsValue: (values: any) => void;
  resetFields: () => void;
  validateFields: () => Promise<any>;
  getFormInstance: () => FormInstance;
}

const FilterBox: React.FC<FilterBoxProps> = ({
  compId,
  filterItems,
  onSearch,
  onReset,
  loading = false,
  showReset = true,
  extraActions,
  initialValues = {},
  onValuesChange,
  defaultColsPerRow = 3,
  searchText = '查询',
  resetText = '重置',
  getFormActions,
  collapsible = false,
  defaultExpanded = true,
  collapsedRows = 1,
  expandText = '展开',
  collapseText = '收起',
}) => {
  const [form] = Form.useForm();
  const [expanded, setExpanded] = useState(defaultExpanded);

  useEffect(() => {
    if (getFormActions) {
      getFormActions({
        getFieldsValue: () => form.getFieldsValue(),
        setFieldsValue: (values: any) => form.setFieldsValue(values),
        resetFields: () => form.resetFields(),
        validateFields: () => form.validateFields(),
        getFormInstance: () => form,
      });
    }
  }, [form, getFormActions]);

  const defaultSpan = Math.floor(24 / defaultColsPerRow);

  const visibleItems = filterItems.filter(item => {
    if (typeof item.visible === 'function') return item.visible();
    return item.visible !== false;
  });

  const itemsPerRow = defaultColsPerRow;
  const maxVisibleItems = collapsible && !expanded
    ? collapsedRows * itemsPerRow
    : visibleItems.length;

  const displayItems = visibleItems.slice(0, maxVisibleItems);

  const handleSearch = () => {
    const values = form.getFieldsValue();
    onSearch(values);
  };

  const handleReset = () => {
    form.resetFields();
    onReset?.();
  };

  const renderItem = (item: FilterItemConfig) => {
    switch (item.type) {
      case 'select':
        return (
          <Select
            allowClear
            placeholder={`请选择${item.label}`}
            options={item.options}
            onSelect={(val) => item.onSelect?.(val, form)}
            {...(item.componentProps || {})}
          />
        );
      case 'input':
        return (
          <Input
            placeholder={`请输入${item.label}`}
            onChange={(e) => item.onChange?.(e, form)}
            {...(item.componentProps || {})}
          />
        );
      case 'custom':
        return item.render?.(form) || null;
      default:
        return null;
    }
  };

  return (
    <div id={compId} className="filter-box">
      <Form
        form={form}
        layout="horizontal"
        initialValues={initialValues}
        onValuesChange={onValuesChange}
      >
        <Row gutter={16}>
          {displayItems.map((item) => (
            <Col key={item.name} span={item.span || defaultSpan}>
              <Form.Item name={item.name} label={item.label}>
                {renderItem(item)}
              </Form.Item>
            </Col>
          ))}
          <Col span={item => defaultSpan} style={{ textAlign: 'right', marginLeft: 'auto' }}>
            <Form.Item>
              <Button type="primary" onClick={handleSearch} loading={loading}>
                {searchText}
              </Button>
              {showReset && (
                <Button style={{ marginLeft: 8 }} onClick={handleReset}>
                  {resetText}
                </Button>
              )}
              {collapsible && visibleItems.length > collapsedRows * itemsPerRow && (
                <Button
                  type="link"
                  onClick={() => setExpanded(!expanded)}
                  icon={expanded ? <UpOutlined /> : <DownOutlined />}
                >
                  {expanded ? collapseText : expandText}
                </Button>
              )}
            </Form.Item>
          </Col>
        </Row>
      </Form>
      {extraActions && (
        <div className="filter-box-extra-actions" style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end', marginTop: 8 }}>
          {extraActions}
        </div>
      )}
    </div>
  );
};

export default FilterBox;
