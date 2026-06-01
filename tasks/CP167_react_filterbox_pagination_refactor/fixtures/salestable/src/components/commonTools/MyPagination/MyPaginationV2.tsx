import { Pagination } from 'antd';
import { FunctionComponent } from 'react';

import './index.css';

interface IMyPaginationV2Props {
  current: number;
  total: number;
  pageSize?: number;
  onChange: (page: number, pageSize: number) => void;
}

const MyPaginationV2: FunctionComponent<IMyPaginationV2Props> = (props) => {
  const {
    current,
    total,
    pageSize = 20,
    onChange,
  } = props;

  const customLocale = {
    jump_to: "跳至",
    page: "页",
  };

  return (
    <div className='yg-page-footer-v2 text-right'>
      {total !== 0 ? (
        <Pagination
          current={current}
          total={total}
          showTotal={() => `共${total}条`}
          onChange={onChange}
          showSizeChanger
          showQuickJumper
          pageSizeOptions={['10', '20', '40', '60', '80', '100']}
          pageSize={pageSize}
          locale={customLocale}
        />
      ) : null}
    </div>
  );
};

export default MyPaginationV2;
