/*
 * @Author: wujiamian
 * @Date: 2022-10-11 17:26:42
 * @Description: 图片预览的格式化
 */
const getFormatAttachmentImage = (picList1: any[], newList?: any[]) => {
  return picList1.map(item => {
    item.title = item.pic_name
    item.src = item.pic_url
    if (newList) {
      newList.push({
        ...item,
        title: item.pic_name,
        src: item.pic_url,
      })
    }
    return item
  })
}

/**
 * 图片查询适配器 - 格式化附件列表
 * @param payload API 响应载荷
 */
const imagesQueryAdaptor = (payload: any) => {
  // 格式化附件列表
  const newList: Array<any> = []
  const picList1 = getFormatAttachmentImage(
    payload.data.rows || payload.data.picture_list || [],
    newList,
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
 * 下载文件
 */
const downloadFile = (url: string, filename: string) => {
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
}

/**
 * 查看图片弹窗配置
 */
const viewImagesDialog = (title: string, apiUrl: string) => {
  return {
    type: 'dialog',
    title,
    body: {
      type: 'service',
      api: {
        url: apiUrl,
        adaptor: imagesQueryAdaptor,
      },
      body: {
        type: 'images',
        source: '${picList1}',
      },
    },
  }
}

export { viewImagesDialog, downloadFile, imagesQueryAdaptor, getFormatAttachmentImage }
