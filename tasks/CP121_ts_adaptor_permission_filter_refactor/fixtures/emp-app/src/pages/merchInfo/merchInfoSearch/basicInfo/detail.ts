/*
 * @Description: Basic merchant info detail page
 */
import Api from 'src/assets/js/api'
import {
  viewImagesDialog,
  downloadFile,
  imagesQueryAdaptor,
} from '../components/viewImagesDialog'

const settlementPanel = {
  type: 'panel',
  title: 'Settlement Card Attachments',
  body: {
    type: 'page',
    data: { picList1: [] },
    initApi: {
      method: 'post',
      url: Api.queryMerchSettleImages,
      requestAdaptor: function (api: any) {
        return {
          ...api,
          data: {
            merch_id: '${merch_id}',
            pic_type: 'A10',
          },
        }
      },
      adaptor: imagesQueryAdaptor,
    },
    body: {
      visibleOn: '${show === 1}',
      type: 'panel',
      body: [
        {
          visibleOn: '${!picList1 || !picList1.length}',
          className: 'w-full h-full flex items-center justify-center',
          type: 'html',
          html: '<div class="w-full h-full flex items-center justify-center"><p>No data</p></div>',
        },
        {
          visibleOn: '${picList1 && picList1.length}',
          type: 'jl-attachment',
          source: 'picList1',
        },
      ],
    },
  },
}

const generalPanel = {
  type: 'panel',
  title: 'General Attachments',
  body: {
    type: 'page',
    data: { picList1: [] },
    initApi: {
      method: 'post',
      url: Api.queryMerchGeneralImages,
      requestAdaptor: function (api: any) {
        return {
          ...api,
          data: {
            merch_id: '${merch_id}',
          },
        }
      },
      adaptor: imagesQueryAdaptor,
    },
    body: [
      {
        visibleOn: '${!picList1 || !picList1.length}',
        className: 'w-full h-full flex items-center justify-center',
        type: 'html',
        html: '<div class="w-full h-full flex items-center justify-center"><p>No data</p></div>',
      },
      {
        visibleOn: '${picList1 && picList1.length}',
        type: 'jl-attachment',
        source: 'picList1',
      },
    ],
  },
}

export default {
  schema: {
    type: 'page',
    title: 'Merchant Basic Info',
    body: [
      settlementPanel,
      generalPanel,
    ],
  },
}
