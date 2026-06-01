/**
 * Merchant Basic Info Detail Page - AMIS Schema definition.
 *
 * This file defines the merchant detail page with sub-merchant table.
 * Each sub-merchant row has protocol buttons (收单协议 / 结算协议).
 *
 * KNOWN BUGS:
 * 1. The "结算协议" (settlement protocol) button does NOT display even when
 *    sign_info contains agreement_type === "2" data. The "收单协议" (acquiring
 *    protocol) button with agreement_type === "1" works fine.
 *    Root cause: In an AMIS input-table column, the data scope for each row
 *    is the row object itself. The visibleOn expression needs to reference
 *    the row-level sign_info directly, but there may be a scoping issue.
 *
 * 2. The onClick handlers for both protocol buttons contain duplicated logic
 *    for opening protocol dialogs. They should be refactored into reusable
 *    functions.
 */
import { btnPermission } from '../../utils/permission'

// Type for sign info entries
interface SignInfo {
  agreement_type: string  // "1" = acquiring, "2" = settlement
  sign_id?: string
  sign_mode?: string  // "P" = paper, "J" = electronic (image), "E" = e-sign
  agreement_pic?: string
}

/**
 * Open a protocol dialog based on sign mode.
 * For electronic protocols (sign_mode P or J), shows images.
 * For e-sign protocols (sign_mode E), opens the e-sign viewer.
 */
function openProtocolViewer(signInfo: SignInfo[], agreementType: string, merchId: string) {
  const items = signInfo.filter(item => item.agreement_type === agreementType)
  if (items.length === 0) return

  const item = items[0]
  if (item.sign_mode === 'P' || item.sign_mode === 'J') {
    // Show paper/image protocol
    window.open(`/protocol/images?merch_id=${merchId}&sign_id=${item.sign_id}`)
  } else if (item.sign_mode === 'E') {
    // Show e-sign protocol
    window.open(`/protocol/esign?merch_id=${merchId}&sign_id=${item.sign_id}`)
  }
}

/**
 * Initialize the basic info detail page schema.
 */
const initBasicInfo = () => {
  return {
    type: 'page',
    body: [
      {
        type: 'panel',
        title: '基本信息',
        body: {
          type: 'form',
          mode: 'horizontal',
          body: [
            { type: 'static', name: 'cust_name', label: '客户名称' },
            { type: 'static', name: 'cust_no', label: '客户编号' },
            { type: 'static', name: 'register_time', label: '注册时间' },
          ],
        },
      },
      {
        type: 'panel',
        title: '子商户信息',
        collapsed: true,
        body: {
          type: 'input-table',
          name: 'merch_info_list',
          placeholder: '暂无数据',
          columnsTogglable: false,
          perPage: 5,
          columns: [
            { name: 'merch_no', label: '商户编号' },
            { name: 'merch_name', label: '商户名称' },
            { name: 'account_name', label: '账户名' },
            { name: 'account_no', label: '账户号' },
            { name: 'register_time', label: '注册时间' },
            {
              type: 'operation',
              label: '操作',
              buttons: [
                // Acquiring protocol button - WORKS correctly
                {
                  visibleOn: '${btnPermission("viewAcquireProtocolBtn")}',
                  type: 'operation',
                  label: '收单协议',
                  buttons: [
                    // Electronic protocol (sign_mode P or J)
                    {
                      visibleOn:
                        '${ARRAYSOME(sign_info, item => item.agreement_type==="1"&&(item.sign_mode=="P"||item.sign_mode=="J"))}',
                      type: 'button',
                      label: '查看协议(图片)',
                      onEvent: {
                        click: {
                          actions: [
                            {
                              actionType: 'custom',
                              script: `
                                const signInfo = event.data.sign_info || [];
                                const items = signInfo.filter(item => item.agreement_type === "1");
                                if (items.length > 0) {
                                  const item = items[0];
                                  if (item.sign_mode === "P" || item.sign_mode === "J") {
                                    window.open("/protocol/images?merch_id=" + event.data.merch_id + "&sign_id=" + item.sign_id);
                                  }
                                }
                              `,
                            },
                          ],
                        },
                      },
                    },
                    // E-sign protocol
                    {
                      visibleOn:
                        '${ARRAYSOME(sign_info, item => item.agreement_type==="1"&&item.sign_mode=="E")}',
                      type: 'button',
                      label: '查看协议(电子签)',
                      onEvent: {
                        click: {
                          actions: [
                            {
                              actionType: 'custom',
                              script: `
                                const signInfo = event.data.sign_info || [];
                                const items = signInfo.filter(item => item.agreement_type === "1");
                                if (items.length > 0) {
                                  const item = items[0];
                                  if (item.sign_mode === "E") {
                                    window.open("/protocol/esign?merch_id=" + event.data.merch_id + "&sign_id=" + item.sign_id);
                                  }
                                }
                              `,
                            },
                          ],
                        },
                      },
                    },
                  ],
                },
                // Settlement protocol button - BUG: does NOT display
                // even when sign_info has agreement_type "2" data.
                // The visibleOn expression uses data.sign_info instead of sign_info
                // (incorrect scope reference in input-table row context).
                {
                  visibleOn:
                    '${btnPermission("viewSettleProtocolBtn")&&ARRAYSOME(data.sign_info, item => item.agreement_type==="2")}',
                  type: 'operation',
                  label: '结算协议',
                  buttons: [
                    // Electronic protocol (sign_mode P or J)
                    {
                      visibleOn:
                        '${ARRAYSOME(data.sign_info, item => item.agreement_type==="2"&&(item.sign_mode=="P"||item.sign_mode=="J"))}',
                      type: 'button',
                      label: '查看协议(图片)',
                      onEvent: {
                        click: {
                          actions: [
                            {
                              actionType: 'custom',
                              script: `
                                const signInfo = event.data.sign_info || [];
                                const items = signInfo.filter(item => item.agreement_type === "2");
                                if (items.length > 0) {
                                  const item = items[0];
                                  if (item.sign_mode === "P" || item.sign_mode === "J") {
                                    window.open("/protocol/images?merch_id=" + event.data.merch_id + "&sign_id=" + item.sign_id);
                                  }
                                }
                              `,
                            },
                          ],
                        },
                      },
                    },
                    // E-sign protocol
                    {
                      visibleOn:
                        '${ARRAYSOME(data.sign_info, item => item.agreement_type==="2"&&item.sign_mode=="E")}',
                      type: 'button',
                      label: '查看协议(电子签)',
                      onEvent: {
                        click: {
                          actions: [
                            {
                              actionType: 'custom',
                              script: `
                                const signInfo = event.data.sign_info || [];
                                const items = signInfo.filter(item => item.agreement_type === "2");
                                if (items.length > 0) {
                                  const item = items[0];
                                  if (item.sign_mode === "E") {
                                    window.open("/protocol/esign?merch_id=" + event.data.merch_id + "&sign_id=" + item.sign_id);
                                  }
                                }
                              `,
                            },
                          ],
                        },
                      },
                    },
                  ],
                },
              ],
            },
          ],
        },
      },
    ],
  }
}

export default initBasicInfo
export { openProtocolViewer }
