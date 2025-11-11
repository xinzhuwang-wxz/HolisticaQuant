import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { X, Key, CheckCircle2, AlertCircle } from 'lucide-react';
import { getApiKeysStatus, setApiKeys, clearApiKeys } from '../lib/apiClient';

interface ApiKeySettingsProps {
  isOpen: boolean;
  onClose: () => void;
}

const PROVIDERS = [
  { id: 'doubao', name: '豆包', placeholder: '输入豆包API密钥' },
  { id: 'chatgpt', name: 'ChatGPT', placeholder: '输入OpenAI API密钥' },
  { id: 'claude', name: 'Claude', placeholder: '输入Anthropic API密钥' },
  { id: 'deepseek', name: 'DeepSeek', placeholder: '输入DeepSeek API密钥' },
];

const ApiKeySettings: React.FC<ApiKeySettingsProps> = ({ isOpen, onClose }) => {
  const [keys, setKeys] = useState<Record<string, string>>({});
  const [status, setStatus] = useState<{ configured_providers: string[]; using_builtin: boolean } | null>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  useEffect(() => {
    if (isOpen) {
      loadStatus();
      // 从localStorage加载已保存的密钥（不显示完整内容）
      const savedKeys: Record<string, string> = {};
      PROVIDERS.forEach(provider => {
        const saved = localStorage.getItem(`api_key_${provider.id}`);
        if (saved) {
          // 只显示前4位和后4位，中间用*代替
          const masked = saved.length > 8 
            ? `${saved.substring(0, 4)}${'*'.repeat(Math.min(saved.length - 8, 20))}${saved.substring(saved.length - 4)}`
            : '****';
          savedKeys[provider.id] = masked;
        }
      });
      setKeys(savedKeys);
    }
  }, [isOpen]);

  const loadStatus = async () => {
    try {
      const statusData = await getApiKeysStatus();
      setStatus(statusData);
    } catch (error) {
      console.error('获取密钥状态失败:', error);
    }
  };

  const handleKeyChange = (providerId: string, value: string) => {
    setKeys(prev => ({ ...prev, [providerId]: value }));
    setMessage(null);
  };

  const handleSave = async () => {
    setLoading(true);
    setMessage(null);

    try {
      // 获取实际密钥（从localStorage或用户输入）
      const actualKeys: Record<string, string> = {};
      PROVIDERS.forEach(provider => {
        const inputValue = keys[provider.id];
        if (inputValue && !inputValue.includes('*')) {
          // 新输入的密钥
          actualKeys[provider.id] = inputValue;
        } else {
          // 尝试从localStorage获取
          const saved = localStorage.getItem(`api_key_${provider.id}`);
          if (saved) {
            actualKeys[provider.id] = saved;
          }
        }
      });

      // 如果有新密钥，保存到localStorage
      Object.entries(keys).forEach(([providerId, value]) => {
        if (value && !value.includes('*')) {
          localStorage.setItem(`api_key_${providerId}`, value);
        }
      });

      // 发送到后端
      if (Object.keys(actualKeys).length > 0) {
        await setApiKeys(actualKeys);
        setMessage({ type: 'success', text: 'API密钥已保存' });
        await loadStatus();
      } else {
        setMessage({ type: 'error', text: '请至少输入一个API密钥' });
      }
    } catch (error) {
      setMessage({ type: 'error', text: `保存失败: ${error instanceof Error ? error.message : '未知错误'}` });
    } finally {
      setLoading(false);
    }
  };

  const handleClear = async () => {
    setLoading(true);
    try {
      await clearApiKeys();
      // 清除localStorage
      PROVIDERS.forEach(provider => {
        localStorage.removeItem(`api_key_${provider.id}`);
      });
      setKeys({});
      setMessage({ type: 'success', text: 'API密钥已清除' });
      await loadStatus();
    } catch (error) {
      setMessage({ type: 'error', text: `清除失败: ${error instanceof Error ? error.message : '未知错误'}` });
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-hidden flex flex-col"
      >
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-slate-200">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-gradient-to-br from-teal-500 to-cyan-600 rounded-lg flex items-center justify-center">
              <Key className="w-5 h-5 text-white" />
            </div>
            <div>
              <h2 className="text-xl font-semibold text-slate-900">API密钥配置</h2>
              <p className="text-sm text-slate-500">配置LLM提供商的API密钥，或使用内置密钥</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-slate-100 transition-colors"
          >
            <X className="w-5 h-5 text-slate-500" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {/* Status Info */}
          {status && (
            <div className={`p-4 rounded-lg border ${
              status.using_builtin 
                ? 'bg-teal-50 border-teal-200' 
                : 'bg-blue-50 border-blue-200'
            }`}>
              <div className="flex items-start space-x-3">
                {status.using_builtin ? (
                  <AlertCircle className="w-5 h-5 text-teal-600 mt-0.5" />
                ) : (
                  <CheckCircle2 className="w-5 h-5 text-blue-600 mt-0.5" />
                )}
                <div className="flex-1">
                  <p className="text-sm font-medium text-slate-900">
                    {status.using_builtin ? '当前使用内置密钥' : '当前使用自定义密钥'}
                  </p>
                  {status.configured_providers.length > 0 && (
                    <p className="text-xs text-slate-600 mt-1">
                      已配置: {status.configured_providers.join(', ')}
                    </p>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* API Key Inputs */}
          {PROVIDERS.map((provider) => (
            <div key={provider.id} className="space-y-2">
              <label className="block text-sm font-medium text-slate-700">
                {provider.name}
              </label>
              <input
                type="password"
                value={keys[provider.id] || ''}
                onChange={(e) => handleKeyChange(provider.id, e.target.value)}
                placeholder={provider.placeholder}
                className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-transparent outline-none transition-all"
              />
            </div>
          ))}

          {/* Message */}
          {message && (
            <div className={`p-3 rounded-lg flex items-center space-x-2 ${
              message.type === 'success' 
                ? 'bg-green-50 text-green-800' 
                : 'bg-red-50 text-red-800'
            }`}>
              {message.type === 'success' ? (
                <CheckCircle2 className="w-4 h-4" />
              ) : (
                <AlertCircle className="w-4 h-4" />
              )}
              <span className="text-sm">{message.text}</span>
            </div>
          )}

          {/* Info */}
          <div className="p-4 bg-slate-50 rounded-lg">
            <p className="text-xs text-slate-600">
              <strong>提示：</strong>API密钥仅存储在浏览器本地，不会上传到服务器（除非您主动配置）。
              如果未配置自定义密钥，系统将使用内置密钥。
            </p>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between p-6 border-t border-slate-200 bg-slate-50">
          <button
            onClick={handleClear}
            disabled={loading}
            className="px-4 py-2 text-sm font-medium text-slate-600 hover:text-slate-900 transition-colors disabled:opacity-50"
          >
            清除所有
          </button>
          <div className="flex space-x-3">
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-200 rounded-lg transition-colors"
            >
              取消
            </button>
            <button
              onClick={handleSave}
              disabled={loading}
              className="px-4 py-2 text-sm font-medium text-white bg-gradient-to-r from-teal-600 to-cyan-600 rounded-lg hover:shadow-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? '保存中...' : '保存'}
            </button>
          </div>
        </div>
      </motion.div>
    </div>
  );
};

export default ApiKeySettings;

