import { getBlob } from '../api'
import { apiPaths } from '../api/endpoints'
import { downloadBlob, openBlobInNewTab } from '../utils/blob'
import type { DocumentResponse, PhotoResponse } from '../types'

async function fetchBinary(url: string, inline = false): Promise<Blob> {
  return getBlob(url, inline ? { params: { inline: 1 } } : undefined)
}

export async function previewDocumentFile(document: Pick<DocumentResponse, 'id'>): Promise<Blob> {
  const blob = await fetchBinary(apiPaths.docs.download(document.id), true)
  openBlobInNewTab(blob)
  return blob
}

export async function downloadDocumentFile(document: Pick<DocumentResponse, 'id' | 'filename'>): Promise<Blob> {
  const blob = await fetchBinary(apiPaths.docs.download(document.id))
  downloadBlob(blob, document.filename || `document-${document.id}`)
  return blob
}

export async function previewPhotoFile(photo: Pick<PhotoResponse, 'id'>): Promise<Blob> {
  const blob = await fetchBinary(apiPaths.photos.download(photo.id), true)
  openBlobInNewTab(blob)
  return blob
}

export async function downloadPhotoFile(photo: Pick<PhotoResponse, 'id' | 'filename'>): Promise<Blob> {
  const blob = await fetchBinary(apiPaths.photos.download(photo.id))
  downloadBlob(blob, photo.filename || `photo-${photo.id}`)
  return blob
}

export async function previewRelatedItem(itemId: string): Promise<Blob | null> {
  const [prefix, rawId] = itemId.split(':', 2)
  if (prefix === 'document') {
    return previewDocumentFile({ id: rawId })
  }
  if (prefix === 'photo') {
    return previewPhotoFile({ id: rawId })
  }
  return null
}

export async function downloadRelatedItem(itemId: string): Promise<Blob | null> {
  const [prefix, rawId] = itemId.split(':', 2)
  if (prefix === 'document') {
    return downloadDocumentFile({ id: rawId, filename: `document-${rawId}` })
  }
  if (prefix === 'photo') {
    return downloadPhotoFile({ id: rawId, filename: `photo-${rawId}` })
  }
  return null
}
