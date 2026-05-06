// components/helpers/CommentForm.tsx
import { useState, useRef, useCallback, useEffect } from 'react';
import { User, Send, Loader2, Paperclip, X, File, CheckCircle2, WandSparkles } from 'lucide-react';
import { attachmentsApi } from '../../api/attachments';
import { proofreadingApi } from '../../api/client';
import { SpellCheckDiff } from './SpellCheckDiff';
import { useToast } from '../ui/use-toast';
import React from 'react';

interface LocalFile {
  id: string;
  file: File;
  preview?: string;
  status: 'pending' | 'uploading' | 'success' | 'error';
  error?: string;
  attachmentId?: string;
}

interface CommentFormProps {
  message: string;
  setMessage: (value: string) => void;
  onSend: (files: LocalFile[]) => Promise<string | null>;
  sending: boolean;
  messageType: 'public' | 'internal';
  setMessageType: (type: 'public' | 'internal') => void;
  canWriteInternal: boolean;
  onSuccess?: () => void;
}

export const CommentForm = React.memo(({ 
  message, 
  setMessage, 
  onSend, 
  sending,
  messageType,
  setMessageType,
  canWriteInternal,
  onSuccess
}: CommentFormProps) => {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [localFiles, setLocalFiles] = useState<LocalFile[]>([]);
  const [uploadingFiles, setUploadingFiles] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { toast } = useToast();

  // ─── Spell Check State ──────────────────────────────────────────────
  const [spellCheckLoading, setSpellCheckLoading] = useState(false);
  const [spellCheckResult, setSpellCheckResult] = useState<any>(null);

  const handleInput = useCallback(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`;
    }
  }, []);

  useEffect(() => {
    handleInput();
  }, [message, handleInput]);

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = Array.from(e.target.files || []);
    const newFiles: LocalFile[] = selectedFiles.map(file => ({
      id: `${file.name}_${Date.now()}_${Math.random()}`,
      file,
      preview: file.type.startsWith('image/') ? URL.createObjectURL(file) : undefined,
      status: 'pending',
    }));
    setLocalFiles(prev => [...prev, ...newFiles].slice(0, 5));
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const droppedFiles = Array.from(e.dataTransfer.files);
    const newFiles: LocalFile[] = droppedFiles.map(file => ({
      id: `${file.name}_${Date.now()}_${Math.random()}`,
      file,
      preview: file.type.startsWith('image/') ? URL.createObjectURL(file) : undefined,
      status: 'pending',
    }));
    setLocalFiles(prev => [...prev, ...newFiles].slice(0, 5));
  };

  const removeFile = (id: string) => {
    setLocalFiles(prev => prev.filter(f => f.id !== id));
  };

  const uploadFiles = async (commentId: string): Promise<boolean> => {
    const filesToUpload = localFiles.filter(f => f.status === 'pending');
    
    if (filesToUpload.length === 0) return true;
    
    setUploadingFiles(true);
    setLocalFiles(prev => prev.map(f => 
      filesToUpload.some(uf => uf.id === f.id) 
        ? { ...f, status: 'uploading' }
        : f
    ));
    
    let allSuccess = true;
    
    for (const fileItem of filesToUpload) {
      try {
        const attachment = await attachmentsApi.uploadAttachment(
          fileItem.file,
          'comment',
          commentId
        );
        
        setLocalFiles(prev => prev.map(f =>
          f.id === fileItem.id
            ? { ...f, status: 'success', attachmentId: attachment.id }
            : f
        ));
      } catch (error) {
        console.error(`Failed to upload ${fileItem.file.name}:`, error);
        setLocalFiles(prev => prev.map(f =>
          f.id === fileItem.id
            ? { ...f, status: 'error', error: 'Ошибка загрузки' }
            : f
        ));
        allSuccess = false;
      }
    }
    
    setUploadingFiles(false);
    return allSuccess;
  };

  // ─── Spell Check ───────────────────────────────────────────────────
  const handleSpellCheck = useCallback(async () => {
    if (!message.trim() || spellCheckLoading) return;

    setSpellCheckLoading(true);
    setSpellCheckResult(null);

    try {
      const result = await proofreadingApi.spellCheck(message);
      setSpellCheckResult(result);
    } catch (error) {
      console.error('Spell check failed:', error);
      toast({
        title: 'Ошибка',
        description: 'Не удалось проверить текст',
        variant: 'destructive',
      });
    } finally {
      setSpellCheckLoading(false);
    }
  }, [message, spellCheckLoading, toast]);

  const handleSend = async () => {
    const trimmedMessage = message.trim();
    const hasFiles = localFiles.filter(f => f.status === 'pending').length > 0;
    
    if ((!trimmedMessage && !hasFiles) || sending || uploadingFiles) {
      return;
    }
    
    try {
      const commentId = await onSend(localFiles);
      
      if (!commentId) {
        throw new Error('Не удалось создать комментарий - ID не получен');
      }
      
      if (hasFiles) {
        await uploadFiles(commentId);
      }
      
      setMessage('');
      setLocalFiles([]);
      setSpellCheckResult(null);
      
      if (onSuccess) {
        await onSuccess();
      }
      
    } catch (error) {
      console.error('Failed to send comment:', error);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && e.ctrlKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setMessage(e.target.value);
    // Сбрасываем результат проверки при изменении текста
    if (spellCheckResult) {
      setSpellCheckResult(null);
    }
  };

  const getStatusIcon = (status: LocalFile['status']) => {
    switch (status) {
      case 'uploading':
        return <Loader2 className="w-4 h-4 text-blue-400 animate-spin" />;
      case 'success':
        return <CheckCircle2 className="w-4 h-4 text-green-400" />;
      case 'error':
        return <X className="w-4 h-4 text-red-400" />;
      default:
        return null;
    }
  };

  const pendingFilesCount = localFiles.filter(f => f.status === 'pending').length;
  const isSendDisabled = (!message.trim() && pendingFilesCount === 0) || sending || uploadingFiles;

  return (
    <div className="flex gap-3">
      <div className="flex-shrink-0">
        <div className="w-10 h-10 rounded-full bg-gradient-to-br from-white/50 to-white/30 flex items-center justify-center">
          <User className="w-5 h-5 text-white" />
        </div>
      </div>
      
      <div className="flex-1">
        {/* ─── Textarea с кнопкой spell check ─── */}
        <div className="relative">
          <textarea
            ref={textareaRef}
            value={message}
            onChange={handleChange}
            onKeyDown={handleKeyDown}
            onDrop={handleDrop}
            onDragOver={(e) => e.preventDefault()}
            placeholder="Написать комментарий..."
            className="w-full px-4 py-3 pr-12 bg-white/5 border border-white/10 rounded-xl text-white placeholder-white/40 focus:outline-none focus:border-red-500/50 focus:bg-white/10 transition-all text-l resize-none overflow-y-auto"
            rows={1}
            style={{ minHeight: '56px', maxHeight: '200px' }}
          />

          {/* Кнопка волшебной палочки внутри textarea */}
          <div className="absolute right-2 top-3">
            <button
              onClick={handleSpellCheck}
              disabled={!message.trim() || spellCheckLoading}
              className={`
                relative p-2 rounded-lg transition-all duration-200 group/spell
                ${spellCheckLoading
                  ? 'text-amber-400 bg-amber-500/10'
                  : 'text-white/90 hover:text-amber-400 hover:bg-amber-500/10 active:scale-95'
                }
                disabled:opacity-30 disabled:cursor-not-allowed
              `}
            >
              {spellCheckLoading ? (
                <Loader2 size={18} className="animate-spin" />
              ) : (
                <WandSparkles size={18} />
              )}

              {/* Тултип */}
              <span className="absolute bottom-full right-0 mb-2 px-2.5 py-1.5 rounded-lg bg-[#1a1a1a] border border-white/10 shadow-xl text-l text-white/80 whitespace-nowrap opacity-0 pointer-events-none group-hover/spell:opacity-100 transition-opacity duration-150 z-10">
                Проверить текст ✨
              </span>
            </button>
          </div>
        </div>

        {/* ─── Результат проверки орфографии ─── */}
        {spellCheckResult && (
          <div className="mt-2">
            <SpellCheckDiff
              result={spellCheckResult}
              onApply={(corrected) => {
                setMessage(corrected);
                setSpellCheckResult(null);
              }}
              onDismiss={() => setSpellCheckResult(null)}
            />
          </div>
        )}
        
        {/* ─── Список файлов ─── */}
        {localFiles.length > 0 && (
          <div className="mt-3 space-y-2">
            {localFiles.map((f) => (
              <div key={f.id} className="flex items-center gap-3 p-2 rounded-lg bg-white/5">
                {f.preview ? (
                  <img src={f.preview} alt="" className="w-8 h-8 rounded object-cover" />
                ) : (
                  <div className="w-8 h-8 rounded bg-white/10 flex items-center justify-center">
                    <File className="w-4 h-4 text-white/50" />
                  </div>
                )}
                <div className="flex-1 min-w-0">
                  <p className="text-l text-white truncate">{f.file.name}</p>
                  <p className="text-l text-white/40">{formatFileSize(f.file.size)}</p>
                  {f.error && <p className="text-l text-red-400">{f.error}</p>}
                </div>
                <div className="flex items-center gap-2">
                  {getStatusIcon(f.status)}
                  <button
                    onClick={() => removeFile(f.id)}
                    disabled={f.status === 'uploading'}
                    className="p-1 rounded hover:bg-white/10 text-white/50 hover:text-red-400 transition-colors disabled:opacity-50"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
        
        {/* ─── Нижняя панель ─── */}
        <div className="flex justify-between items-center mt-2">
          <div className="flex gap-2">
            {canWriteInternal && (
              <button
                type="button"
                onClick={() => setMessageType(messageType === 'public' ? 'internal' : 'public')}
                className={`px-3 py-1.5 rounded-lg text-l font-medium transition-colors ${
                  messageType === 'internal'
                    ? 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30'
                    : 'bg-white/5 text-white/60 border border-white/10 hover:bg-white/10'
                }`}
              >
                {messageType === 'internal' ? 'Внутренний' : 'Публичный'}
              </button>
            )}
            
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="px-3 py-1.5 rounded-lg text-l font-medium bg-white/5 text-white/60 border border-white/10 hover:bg-white/10 transition-colors"
              disabled={uploadingFiles}
            >
              <Paperclip className="w-6 h-6 inline mr-1" />
              Файлы {localFiles.length > 0 && `(${localFiles.length})`}
            </button>
            <input
              ref={fileInputRef}
              type="file"
              multiple
              onChange={handleFileSelect}
              className="hidden"
              accept="image/*,.pdf,.doc,.docx,.xls,.xlsx,.txt"
            />
            
            <span className="text-l text-white/30 self-center">
              Ctrl+Enter для отправки
            </span>
          </div>
          
          <button
            onClick={handleSend}
            disabled={isSendDisabled}
            className="px-5 py-1.5 rounded-lg bg-red-800 hover:bg-red-700 text-white font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 text-l"
          >
            {(sending || uploadingFiles) ? <Loader2 className="w-6 h-6 animate-spin" /> : <Send className="w-5 h-5" />}
            Отправить
          </button>
        </div>
      </div>
    </div>
  );
});

CommentForm.displayName = 'CommentForm';