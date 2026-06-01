/**
 * View Images Dialog - Shows attachment images with optional permission filtering.
 *
 * ISSUE: The `imagesQueryAdaptor` function currently accepts `permissField` as
 * a parameter but does NOT use it for any filtering. When a permission field
 * is provided, it should check if the user has that permission and filter out
 * images of certain `pic_type` values accordingly.
 *
 * The function is called from multiple pages with different permission requirements:
 * - merchInfoSearch: permissField = 'viewCustomerSettleInfo', filter pic_type 'A10'
 * - merchDetail: permissField = 'viewMerchBankCard', filter pic_type 'A08'
 * - no permissField: show all images (backward compatible)
 */
import { getFormatAttachmentImage, FormattedImage } from '../../utils/attachment'
import { btnPermission } from '../../utils/permission'

// Permission field to pic_type filter mapping
// When a permission is NOT granted, these pic_types should be filtered OUT
export const PERMISSION_FILTER_MAP: Record<string, string[]> = {
  viewCustomerSettleInfo: ['A10'],
  viewMerchBankCard: ['A08', 'A09'],
  viewContractImages: ['A11', 'A12'],
}

/**
 * Query adaptor for the images dialog.
 * Formats raw API response into displayable image list.
 *
 * TODO: Use permissField parameter to filter images based on user permissions.
 * Currently permissField is accepted but completely ignored.
 */
const imagesQueryAdaptor = (payload: any, response: any, permissField?: string) => {
  // Format attachment list
  const newList: FormattedImage[] = []
  const picList1 = getFormatAttachmentImage(
    payload.data.rows || payload.data.picture_list || [],
    newList
  )
  return {
    ...payload,
    data: {
      ...payload.data,
      picList1: newList,
    },
  }
}

/**
 * Build the AMIS dialog schema for viewing images.
 */
export const viewImagesDialog = (options?: { permissField?: string }) => {
  return {
    type: 'dialog',
    title: '查看附件',
    size: 'lg',
    body: {
      type: 'service',
      api: {
        url: '/api/merch/attachments/${merch_id}',
        method: 'get',
        adaptor: (payload: any, response: any) => {
          return imagesQueryAdaptor(payload, response, options?.permissField)
        },
      },
      body: {
        type: 'images',
        name: 'picList1',
        src: '${pic_url}',
        thumbMode: 'cover',
      },
    },
  }
}

export { imagesQueryAdaptor }
