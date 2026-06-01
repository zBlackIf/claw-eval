/*
 * @Author: wujiamian
 * @Date: 2022-10-11 17:26:42
 * @Description: Image preview formatting utilities
 */
const getFormatAttachmentImage = (picList1, newList?: any[]) => {
  return picList1.map(item => {
    item.title = item.pic_name
    item.fileType = item.file_type
    // cover
    if (item.file_type !== '2') {
      item.src = item.pic_ftp_address
    }
    // content
    if (item.file_type === '3') {
      // video
      item.path = item.video_ftp_address
    } else if (item.file_type === '4') {
      // audio
      item.path = item.audio_ftp_address
    } else {
      item.path = item.pic_ftp_address
    }
    if (item.path && newList) {
      newList.push(item)
    }
    return item
  })
}

/*
 * @Author: wangxuan
 * @Date: 2022-10-11 17:26:42
 * @Description: View images dialog adaptor
 */

const imagesQueryAdaptor = (payload, response, permissFeild) => {
  // Format attachment list
  const newList: Array<any> = []
  const picList1 = getFormatAttachmentImage(payload.data.rows || payload.data.picture_list || [], newList)
  return {
    ...payload,
    data: {
      ...payload.data,
      picList1: newList,
    },
  }
}

const viewImagesDialog = (url, params, title = '') => {
  return {
    title: title || 'View Attachments',
    size: 'md',
    bodyClassName: 'jl-p-0',
    body: {
      type: 'page',
      data: { picList1: [] },
      initApi: {
        method: 'post',
        url: url,
        requestAdaptor: function (api: any) {
          return {
            ...api,
            data: {
              ...params,
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
    actions: [
      {
        type: 'button',
        actionType: 'close',
        label: 'Close',
      },
    ],
  }
}

function downloadFile(url, fileName) {
  const a = document.createElement('a')
  a.style.display = 'none'
  a.setAttribute('target', '_blank')
  fileName && a.setAttribute('download', fileName)
  a.href = url
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
}

export { viewImagesDialog, imagesQueryAdaptor, getFormatAttachmentImage, downloadFile }
