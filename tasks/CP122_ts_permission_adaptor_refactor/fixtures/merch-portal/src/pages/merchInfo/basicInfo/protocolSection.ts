/*
 * @Author: wangxuan
 * @Date: 2022-05-26 14:22:43
 * @Description: 基本信息详情 - 协议区域
 */

import { queryStringParse, btnPermission } from 'src/assets/js/common'
import Api from 'src/assets/js/api'
import { viewImagesDialog, downloadFile, imagesQueryAdaptor } from '../components/viewImagesDialog'

// 模拟 axios
declare const axios: { post: (url: string, data: any) => Promise<any> }

/**
 * 协议操作区域
 */
const initProtocolSection = () => {
  return {
    type: 'panel',
    title: '协议信息',
    body: [
      // 收单协议
      {
        visibleOn: '${btnPermission("viewAcquireProtocolBtn")}',
        type: 'operation',
        label: '收单协议',
        buttons: [
          // 电子协议
          {
            visibleOn:
              '${ARRAYSOME(sign_info, item => item.agreement_type==="1"&&(item.sign_mode=="P"||item.sign_mode=="J"))}',
            type: 'button',
            label: '查看',
            level: 'link',
            align: 'center',
            onClick: async (e: any, props: any) => {
              const sign_info = props.data.sign_info || []
              const arr = sign_info.filter(
                (item: any) => item.agreement_type === '1' && (item.sign_mode === 'P' || item.sign_mode === 'J'),
              )
              const item = arr[0] || {}
              const agreement_id = props.data.sign_info?.sign_id || props.data?.merch_id

              try {
                const result = await axios.post(Api.recordQueryContract, { agreement_id, source: 'paymng' })
                if (result.ret_code === '00') {
                  const contract_url = result.contract_url || ''
                  if (contract_url) {
                    downloadFile(contract_url, '协议')
                  }
                } else {
                  props.env.notify('error', result.ret_msg)
                }
              } catch (error) {
                console.log(error)
              }
            },
          },
          // 其他（非电子）
          {
            visibleOn:
              '${ARRAYSOME(sign_info, item => item.agreement_type==="1"&&item.sign_mode!="P"&&item.sign_mode!="J")}',
            type: 'button',
            level: 'link',
            label: '查看',
            align: 'center',
            onClick: async (e: any, props: any) => {
              const sign_info = props.data.sign_info || []
              const arr = sign_info.filter(
                (item: any) => item.agreement_type === '1' && !(item.sign_mode === 'P' || item.sign_mode === 'J'),
              )
              const item = arr[0] || {}
              const agreement_pic = item.agreement_pic || ''

              try {
                const result = await axios.post(Api.common_image_url, { image_paths: [agreement_pic] })
                if (result.ret_code === '00') {
                  const image_urls = result.image_urls || []
                  if (image_urls.length > 0) {
                    const url = image_urls[0]
                    downloadFile(url, '协议')
                  }
                } else {
                  props.env.notify('error', result.ret_msg)
                }
              } catch (error) {
                console.log(error)
              }
            },
          },
        ],
      },
      // 结算协议
      {
        visibleOn:
          '${btnPermission("viewSettleProtocolBtn")&&ARRAYSOME(sign_info, item => item.agreement_type==="2")}',
        type: 'operation',
        label: '结算协议',
        buttons: [
          // 电子协议
          {
            visibleOn:
              '${ARRAYSOME(sign_info, item => item.agreement_type==="2"&&(item.sign_mode=="P"||item.sign_mode=="J"))}',
            type: 'button',
            label: '查看',
            level: 'link',
            align: 'center',
            onClick: async (e: any, props: any) => {
              const sign_info = props.data.sign_info || []
              const arr = sign_info.filter(
                (item: any) => item.agreement_type === '2' && (item.sign_mode === 'P' || item.sign_mode === 'J'),
              )
              const item = arr[0] || {}
              const agreement_id = props.data.sign_info?.sign_id || props.data?.merch_id

              try {
                const result = await axios.post(Api.recordQueryContract, { agreement_id, source: 'paymng' })
                if (result.ret_code === '00') {
                  const contract_url = result.contract_url || ''
                  if (contract_url) {
                    downloadFile(contract_url, '协议')
                  }
                } else {
                  props.env.notify('error', result.ret_msg)
                }
              } catch (error) {
                console.log(error)
              }
            },
          },
          // 其他（非电子）
          {
            visibleOn:
              '${ARRAYSOME(sign_info, item => item.agreement_type==="2"&&item.sign_mode!="P"&&item.sign_mode!="J")}',
            type: 'button',
            level: 'link',
            label: '查看',
            align: 'center',
            onClick: async (e: any, props: any) => {
              const sign_info = props.data.sign_info || []
              const arr = sign_info.filter(
                (item: any) => item.agreement_type === '2' && !(item.sign_mode === 'P' || item.sign_mode === 'J'),
              )
              const item = arr[0] || {}
              const agreement_pic = item.agreement_pic || ''

              try {
                const result = await axios.post(Api.common_image_url, { image_paths: [agreement_pic] })
                if (result.ret_code === '00') {
                  const image_urls = result.image_urls || []
                  if (image_urls.length > 0) {
                    const url = image_urls[0]
                    downloadFile(url, '协议')
                  }
                } else {
                  props.env.notify('error', result.ret_msg)
                }
              } catch (error) {
                console.log(error)
              }
            },
          },
        ],
      },
      // 结算卡附件查看
      {
        visibleOn: '${btnPermission("viewSettleCardBtn")}',
        type: 'operation',
        label: '结算卡附件',
        buttons: [
          {
            type: 'button',
            label: '查看',
            level: 'link',
            actionType: 'dialog',
            dialog: viewImagesDialog('结算卡附件', Api.attachmentList),
          },
        ],
      },
    ],
  }
}

export default initProtocolSection
