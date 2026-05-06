import api from './client';
import type { Attachment } from '@/types';

export interface PresignedUploadRequest {
  filename: string;
  content_type: string;
  owner_type: string;
  owner_id: string;
}

export interface PresignedUploadResponse {
  upload_url: string;
  storage_key: string;
  expires_in: number;
}

export interface ConfirmUploadRequest {
  storage_key: string;
  original_filename: string;
  content_type: string;
  owner_type: string;
  owner_id: string;
}

export interface PresignedDownloadResponse {
  download_url: string;
  storage_key: string;
  expires_in: number;
}

export interface Attachment extends Record<string, unknown> {
  id: string;
  original_filename: string;
  mime_type: string;
  size_bytes: number;
  storage_key: string;
  owner_type: string;
  owner_id: string;
  uploaded_by: string;
  uploaded_at: string;
}

export const attachmentsApi = {
  // Получить presigned URL для загрузки
  async getPresignedUploadUrl(data: PresignedUploadRequest): Promise<PresignedUploadResponse> {
    const response = await api.post('/api/v1/attachments/presigned-upload', data);
    return response.data;
  },

  // Загрузить файл напрямую в MinIO
  async uploadFileToStorage(uploadUrl: string, file: File): Promise<void> {
    const publicUrl = uploadUrl.replace('minio:9000', 'localhost:9900');
    
    const response = await fetch(publicUrl, {
      method: 'PUT',
      body: file,
      headers: {
        'Content-Type': file.type,
      },
    });
    
    if (!response.ok) {
      throw new Error(`Upload failed: ${response.status}`);
    }
  },

  // Подтвердить загрузку
  async confirmUpload(data: ConfirmUploadRequest): Promise<Attachment> {
    const response = await api.post('/api/v1/attachments/confirm-upload', data);
    return response.data;
  },


  // Получить информацию о вложении по ID
  async getAttachment(attachmentId: string): Promise<Attachment> {
    const response = await api.get(`/api/v1/attachments/${attachmentId}`);
    return response.data;
  },

  // Получить presigned URL для скачивания
  async getPresignedDownloadUrl(attachmentId: string): Promise<PresignedDownloadResponse> {
    const response = await api.get(`/api/v1/attachments/${attachmentId}/presigned-download`);
    return response.data;
  },

  // Полный процесс скачивания
  async downloadAttachment(attachmentId: string): Promise<void> {
  try {
    // Шаг 1: Получить presigned URL для скачивания
    const { download_url, storage_key } = await this.getPresignedDownloadUrl(attachmentId);
    
    // Шаг 2: ЗАМЕНЯЕМ URL (так же как и при загрузке)
    let fixedDownloadUrl = download_url;
    if (fixedDownloadUrl.includes('http://minio:9000')) {
      fixedDownloadUrl = fixedDownloadUrl.replace('http://minio:9000', 'http://localhost:9900');
    }
    if (fixedDownloadUrl.includes('http://maildev:9000')) {
      fixedDownloadUrl = fixedDownloadUrl.replace('http://maildev:9000', 'http://localhost:9900');
    }
    
    
    // Шаг 3: Скачать файл по исправленному URL
    const response = await fetch(fixedDownloadUrl);
    
    if (!response.ok) {
      throw new Error(`Download failed: ${response.status}`);
    }
    
    // Шаг 4: Сохранить файл на диск
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    
    // Извлекаем оригинальное имя файла из storage_key или запрашиваем информацию о вложении
    const attachment = await this.getAttachment(attachmentId);
    a.download = attachment.original_filename;
    
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  } catch (error) {
    console.error('Download failed:', error);
    throw error;
  }
},
  // Полный процесс загрузки
  async uploadAttachment(
    file: File,
    ownerType: string,
    ownerId: string
  ): Promise<Attachment> {
    
    const presignedData = await this.getPresignedUploadUrl({
      filename: file.name,
      content_type: file.type,
      owner_type: ownerType,
      owner_id: ownerId,
    });

    await this.uploadFileToStorage(presignedData.upload_url, file);

    const attachment = await this.confirmUpload({
      storage_key: presignedData.storage_key,
      original_filename: file.name,
      content_type: file.type,
      owner_type: ownerType,
      owner_id: ownerId,
    });

    return attachment;
  },
};