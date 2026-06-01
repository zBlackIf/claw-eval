import { Pagination } from 'antd';
import { FunctionComponent } from 'react';

import './index.css';

interface IMyPaginationProps {
  page: number;
  total: number;
  changePage: (page: number, limit: number) => void;
  limit?: number;
}

const MyPagination: FunctionComponent<IMyPaginationProps> = (props) => {
  const {
    page,
    total,
    changePage,
    limit,
  } = props;

  const customLocale = {
    jump_to: "跳至",
    page: "页",
  };

  return (
    <div className='yg-page-footer text-right'>
      {total !== 0 ? (
        <Pagination
          current={page}
          total={total}
          showTotal={() => `共${total}条`}
          onChange={changePage}
          showSizeChanger
          showQuickJumper
          pageSizeOptions={['10', '20', '40', '60', '80', '100']}
          pageSize={limit ?? 20}
          locale={customLocale}
        />
      ) : null}
    </div>
  );
};

export default MyPagination;
