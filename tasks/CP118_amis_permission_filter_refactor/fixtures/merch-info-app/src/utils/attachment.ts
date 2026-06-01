/**
 * Attachment image formatting utility.
 * Transforms raw attachment data into display-friendly image list.
 */

export interface AttachmentItem {
  pic_type: string
  pic_url: string
  pic_name?: string
  [key: string]: any
}

export interface FormattedImage {
  pic_type: string
  pic_url: string
  pic_name: string
  thumbnail: string
}

/**
 * Format raw attachment rows into a standardized image list.
 * @param rows - Raw attachment data from API
 * @param outList - Output array to populate (mutated in place)
 * @returns The same outList reference
 */
export function getFormatAttachmentImage(
  rows: AttachmentItem[],
  outList: FormattedImage[]
): FormattedImage[] {
  for (const row of rows) {
    outList.push({
      pic_type: row.pic_type || 'unknown',
      pic_url: row.pic_url || '',
      pic_name: row.pic_name || `image_${outList.length + 1}`,
      thumbnail: row.pic_url ? `${row.pic_url}?thumb=200x200` : '',
    })
  }
  return outList
}
