// components/helpers/ConfirmModal.tsx
import { X, AlertTriangle } from 'lucide-react';

interface ConfirmModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  type?: 'danger' | 'warning' | 'info';
}

export const ConfirmModal = ({ 
  isOpen, 
  onClose, 
  onConfirm, 
  title, 
  message, 
  confirmText = 'Удалить', 
  cancelText = 'Отмена',
  type = 'danger' 
}: ConfirmModalProps) => {
  if (!isOpen) return null;

  const getTypeStyles = () => {
    switch (type) {
      case 'danger':
        return {
          icon: <AlertTriangle className="w-6 h-6 text-red-400" />,
          confirmButton: 'bg-red-800 hover:bg-red-700 text-white',
          titleColor: 'text-white'
        };
      case 'warning':
        return {
          icon: <AlertTriangle className="w-6 h-6 text-yellow-400" />,
          confirmButton: 'bg-yellow-800 hover:bg-yellow-700 text-white',
          titleColor: 'text-white'
        };
      default:
        return {
          icon: <AlertTriangle className="w-6 h-6 text-blue-400" />,
          confirmButton: 'bg-blue-800 hover:bg-blue-700 text-white',
          titleColor: 'text-white'
        };
    }
  };

  const styles = getTypeStyles();

  return (
    <div className="fixed inset-0 z-[200] flex items-center justify-center bg-black/80 p-4" onClick={onClose}>
      <div className="bg-[#1a1a1a] rounded-2xl w-full max-w-md overflow-hidden border border-white/20" onClick={e => e.stopPropagation()}>
        {/* Заголовок */}
        <div className="flex justify-between items-center px-6 py-4 border-b border-white/10">
          <div className="flex items-center gap-3">
            {styles.icon}
            <h2 className="text-[16px] font-bold text-white">{title}</h2>
          </div>
          <button onClick={onClose} className="text-white/50 hover:text-white transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>
        
        {/* Содержание */}
        <div className="p-6">
          <p className="text-white/70 text-base">{message}</p>
        </div>
        
        {/* Кнопки */}
        <div className="flex justify-end gap-3 px-6 py-4 border-t border-white/10">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-xl bg-white/5 hover:bg-white/10 text-white transition-colors text-sm"
          >
            {cancelText}
          </button>
          <button
            onClick={() => {
              onConfirm();
              onClose();
            }}
            className={`px-4 py-2 rounded-xl font-medium transition-colors text-sm ${styles.confirmButton}`}
          >
            {confirmText}
          </button>
        </div>
      </div>
    </div>
  );
};