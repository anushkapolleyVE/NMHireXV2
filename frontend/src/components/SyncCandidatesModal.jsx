import React, { useState } from 'react';
import { syncCandidates } from '../utils/api';

export default function SyncCandidatesModal({ isOpen, onClose, onSyncSuccess }) {
  const [source, setSource] = useState('local'); // 'local', 'gdrive', 'indeed'
  const [pathOrUrl, setPathOrUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);

  if (!isOpen) return null;

  const handleSync = async () => {
    if (!pathOrUrl.trim()) {
      setError('Please enter a valid path or URL.');
      return;
    }

    setLoading(true);
    setError('');
    setResult(null);

    try {
      const data = await syncCandidates(source, pathOrUrl);
      setResult(data);
    } catch (err) {
      setError(err.message || 'Failed to sync candidates.');
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    if (result && onSyncSuccess) {
      onSyncSuccess(result);
    } else {
      onClose();
    }
    
    setSource('local');
    setPathOrUrl('');
    setError('');
    setResult(null);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
      <div className="bg-slate-900 border border-slate-700/50 rounded-2xl w-full max-w-lg shadow-2xl overflow-hidden animate-slide-up">
        
        {/* Header */}
        <div className="p-6 border-b border-slate-800">
          <h2 className="text-xl font-bold text-white">Sync resume pool</h2>
          <p className="text-sm text-slate-400 mt-1">
            Choose a source to scan and ingest candidates into the database.
          </p>
        </div>

        {/* Content */}
        <div className="p-6 space-y-4">
          
          {/* Options */}
          <div className="space-y-3">
            <p className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">Source</p>
            
            {/* Local Option */}
            <label 
              className={`flex items-start p-4 rounded-xl border cursor-pointer transition-all ${
                source === 'local' 
                  ? 'border-brand bg-brand/5 ring-1 ring-brand/50' 
                  : 'border-slate-700 hover:border-slate-500 bg-slate-800/30'
              }`}
            >
              <input 
                type="radio" 
                name="source" 
                value="local" 
                checked={source === 'local'} 
                onChange={(e) => setSource(e.target.value)} 
                className="sr-only" 
              />
              <div className="flex-1 ml-2">
                <div className="flex justify-between items-center mb-1">
                  <span className="font-bold text-white text-sm flex items-center gap-2">
                    <svg className="w-4 h-4 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
                    </svg>
                    Local Drive
                  </span>
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">Available</span>
                </div>
                <p className="text-xs text-slate-400">A folder on this machine or server that NM-HireX can read directly.</p>
              </div>
            </label>

            {/* Google Drive Option */}
            <label 
              className={`flex items-start p-4 rounded-xl border cursor-pointer transition-all ${
                source === 'gdrive' 
                  ? 'border-brand bg-brand/5 ring-1 ring-brand/50' 
                  : 'border-slate-700 hover:border-slate-500 bg-slate-800/30'
              }`}
            >
              <input 
                type="radio" 
                name="source" 
                value="gdrive" 
                checked={source === 'gdrive'} 
                onChange={(e) => setSource(e.target.value)} 
                className="sr-only" 
              />
              <div className="flex-1 ml-2">
                <div className="flex justify-between items-center mb-1">
                  <span className="font-bold text-white text-sm flex items-center gap-2">
                    <svg className="w-4 h-4 text-slate-400" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M12.01 1.742h.005l9.088 15.688L16.55 25.26 7.48 9.57 12.01 1.742zM7.48 9.57l4.53 7.828H2.94L7.48 9.57zm4.53 7.828l4.54 7.862H2.922L12.01 17.4z" />
                    </svg>
                    Google Drive
                  </span>
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-brand/10 text-brand border border-brand/20">New</span>
                </div>
                <p className="text-xs text-slate-400">Sync candidates from a shared Google Drive folder or ZIP file URL.</p>
              </div>
            </label>

            {/* Indeed Option (Disabled) */}
            <label className="flex items-start p-4 rounded-xl border border-slate-800 bg-slate-800/20 opacity-60 cursor-not-allowed">
              <input type="radio" disabled className="sr-only" />
              <div className="flex-1 ml-2">
                <div className="flex justify-between items-center mb-1">
                  <span className="font-bold text-white text-sm flex items-center gap-2">
                    <span className="bg-[#003A9B] text-white text-[10px] px-1 rounded font-bold">ID</span>
                    Indeed
                  </span>
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-700/50 text-slate-400 border border-slate-600/50">Coming soon</span>
                </div>
                <p className="text-xs text-slate-400">Sync candidates sourced from Indeed. Needs a one-time Indeed employer account authorization to connect.</p>
              </div>
            </label>
          </div>

          {/* Input field */}
          <div className="mt-6">
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">
              {source === 'local' ? 'Local folder path' : 'Google Drive URL'}
            </label>
            <input 
              type="text" 
              className="w-full bg-slate-900 border border-brand rounded-lg px-4 py-3 text-sm text-white focus:outline-none focus:ring-2 focus:ring-brand/50 shadow-[0_0_15px_rgba(59,130,246,0.15)]"
              placeholder={source === 'local' ? 'C:\\Users\\...\\resumes' : 'https://drive.google.com/drive/folders/...'}
              value={pathOrUrl}
              onChange={(e) => setPathOrUrl(e.target.value)}
            />
          </div>

          {/* Result or Error */}
          {error && (
            <div className="mt-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
              {error}
            </div>
          )}

          {result && (
            <div className="mt-4 p-4 rounded-lg bg-emerald-500/10 border border-emerald-500/20">
              <p className="text-emerald-400 text-sm font-bold mb-1">Sync Complete!</p>
              <ul className="text-xs text-slate-300 space-y-1">
                <li>Total Found: <span className="text-white font-bold">{result.total || 0}</span></li>
                <li>Successfully Ingested: <span className="text-white font-bold">{result.successful || 0}</span></li>
                <li>Skipped (Already Exist): <span className="text-white font-bold">{result.skipped || 0}</span></li>
                <li>Failed: <span className="text-white font-bold">{result.failed || 0}</span></li>
              </ul>
            </div>
          )}

        </div>

        {/* Footer */}
        <div className="p-4 border-t border-slate-800 bg-slate-800/30 flex justify-end gap-3">
          <button 
            onClick={handleClose}
            className="px-4 py-2 rounded-lg text-sm font-bold text-slate-300 hover:text-white hover:bg-slate-700 transition-colors"
          >
            {result ? 'Close' : 'Cancel'}
          </button>
          {!result && (
            <button 
              onClick={handleSync}
              disabled={loading}
              className={`px-6 py-2 rounded-lg text-sm font-bold text-white transition-all flex items-center gap-2 ${
                loading 
                  ? 'bg-brand/50 cursor-not-allowed' 
                  : 'bg-brand hover:bg-brand-light shadow-[0_0_15px_rgba(59,130,246,0.5)]'
              }`}
            >
              {loading ? (
                <>
                  <svg className="animate-spin h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Syncing...
                </>
              ) : 'Go'}
            </button>
          )}
        </div>

      </div>
    </div>
  );
}
