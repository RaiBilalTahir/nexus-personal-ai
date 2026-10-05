import React, { useState, useEffect } from 'react';
import {
  Terminal,
  Cpu,
  Layers,
  FileText,
  Settings,
  FolderOpen,
  CheckCircle2,
  AlertCircle,
  Play,
  RotateCw,
  Upload,
  BookOpen,
  Shield,
  FileCode,
  HardDrive,
  Clock,
  Sparkles,
  ChevronRight,
  ExternalLink,
  Trash2,
  Eye,
  Server
} from 'lucide-react';

interface SystemStatus {
  status: string;
  version: string;
  name: string;
  environment: string;
  checks: Record<string, boolean>;
  config: {
    ai?: { provider: string; model: string };
    paths?: Record<string, string>;
    features?: Record<string, boolean>;
    runtime?: Record<string, string | number>;
  };
}

interface Feature {
  id: string;
  display_name: string;
  description: string;
  status: 'implemented' | 'planned';
  enabled: boolean;
}

interface InboxFile {
  name: string;
  size: number;
  modified: string;
  extension: string;
}

interface Course {
  name: string;
  notesCount: number;
  rawCount: number;
  notes: string[];
  raw: string[];
}

interface ProvenanceRecord {
  source: {
    filename: string;
    content_hash: string;
    size_bytes: number;
    mime_type: string;
  };
  processing_config_id: string;
  status: string;
  output_path?: string;
  updated_at: string;
}

export default function App() {
  const [activeTab, setActiveTab] = useState<'control' | 'inbox' | 'knowledge' | 'provenance' | 'config' | 'logs'>('control');
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [features, setFeatures] = useState<Feature[]>([]);
  const [inboxFiles, setInboxFiles] = useState<InboxFile[]>([]);
  const [courses, setCourses] = useState<Course[]>([]);
  const [selectedCourse, setSelectedCourse] = useState<string>('Introduction to Computing');
  const [selectedNote, setSelectedNote] = useState<{ filename: string; content: string } | null>(null);
  const [provenance, setProvenance] = useState<ProvenanceRecord[]>([]);
  const [logs, setLogs] = useState<{ core: string; process_notes: string }>({ core: '', process_notes: '' });
  
  const [processing, setProcessing] = useState(false);
  const [processOutput, setProcessOutput] = useState<string>('');
  const [systemCheckOpen, setSystemCheckOpen] = useState(false);
  const [notification, setNotification] = useState<string | null>(null);

  const showNotification = (msg: string) => {
    setNotification(msg);
    setTimeout(() => setNotification(null), 4000);
  };

  const fetchStatus = async () => {
    try {
      const res = await fetch('/api/system-status');
      const data = await res.json();
      setStatus(data);
    } catch {
      // fallback
    }
  };

  const fetchFeatures = async () => {
    try {
      const res = await fetch('/api/features');
      const data = await res.json();
      setFeatures(data);
    } catch {
      // fallback
    }
  };

  const fetchInbox = async () => {
    try {
      const res = await fetch('/api/inbox');
      const data = await res.json();
      setInboxFiles(data);
    } catch {
      // fallback
    }
  };

  const fetchCourses = async () => {
    try {
      const res = await fetch('/api/courses');
      const data = await res.json();
      setCourses(data);
      if (data.length > 0 && !selectedCourse) {
        setSelectedCourse(data[0].name);
      }
    } catch {
      // fallback
    }
  };

  const fetchProvenance = async () => {
    try {
      const res = await fetch('/api/provenance');
      const data = await res.json();
      setProvenance(data.records || []);
    } catch {
      // fallback
    }
  };

  const fetchLogs = async () => {
    try {
      const res = await fetch('/api/logs');
      const data = await res.json();
      setLogs(data);
    } catch {
      // fallback
    }
  };

  useEffect(() => {
    fetchStatus();
    fetchFeatures();
    fetchInbox();
    fetchCourses();
    fetchProvenance();
    fetchLogs();
  }, []);

  const toggleFeature = async (featureId: string, currentEnabled: boolean) => {
    try {
      const res = await fetch(`/api/features/${featureId}/toggle`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled: !currentEnabled }),
      });
      if (res.ok) {
        fetchFeatures();
        fetchStatus();
        showNotification(`${featureId} toggled ${!currentEnabled ? 'ON' : 'OFF'}`);
      } else {
        const err = await res.json();
        showNotification(err.error || 'Failed to toggle feature');
      }
    } catch {
      showNotification('Error connecting to server');
    }
  };

  const runProcessNotes = async () => {
    setProcessing(true);
    setProcessOutput('Starting Process Notes pipeline...\n');
    try {
      const res = await fetch('/api/process-notes', { method: 'POST' });
      const data = await res.json();
      setProcessOutput(data.stdout + (data.stderr ? `\nSTDERR:\n${data.stderr}` : ''));
      fetchInbox();
      fetchCourses();
      fetchProvenance();
      fetchLogs();
      if (data.success) {
        showNotification('Process Notes completed successfully!');
      } else {
        showNotification('Process Notes finished with warnings or errors.');
      }
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err);
      setProcessOutput(`Execution failed: ${message}`);
    } finally {
      setProcessing(false);
    }
  };

  const loadNoteContent = async (courseName: string, fileName: string) => {
    try {
      const res = await fetch(`/api/notes/${encodeURIComponent(courseName)}/${encodeURIComponent(fileName)}`);
      const data = await res.json();
      setSelectedNote({ filename: fileName, content: data.content });
    } catch {
      showNotification('Failed to read note content');
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0) return;
    const formData = new FormData();
    for (let i = 0; i < e.target.files.length; i++) {
      formData.append('files', e.target.files[i]);
    }
    try {
      const res = await fetch('/api/inbox/upload', {
        method: 'POST',
        body: formData,
      });
      if (res.ok) {
        showNotification('Files uploaded to Inbox successfully');
        fetchInbox();
      }
    } catch {
      showNotification('Upload failed');
    }
  };

  const deleteInboxFile = async (filename: string) => {
    try {
      const res = await fetch(`/api/inbox/${encodeURIComponent(filename)}`, { method: 'DELETE' });
      if (res.ok) {
        fetchInbox();
        showNotification(`Removed ${filename} from Inbox`);
      }
    } catch {
      showNotification('Delete failed');
    }
  };

  return (
    <div className="min-h-screen bg-[#101318] text-[#E8EAED] flex flex-col">
      {/* Toast Notification */}
      {notification && (
        <div className="fixed top-5 right-5 z-50 bg-[#1e232d] border border-cyan-500/40 text-cyan-200 px-4 py-3 rounded-lg shadow-xl shadow-cyan-950/50 flex items-center space-x-3 text-sm animate-fade-in">
          <CheckCircle2 className="w-4 h-4 text-cyan-400" />
          <span>{notification}</span>
        </div>
      )}

      {/* Top Header */}
      <header className="bg-[#171A21] border-b border-[#252A34] px-6 py-4 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center space-x-4">
          <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-cyan-500/20 to-blue-600/30 border border-cyan-500/30 flex items-center justify-center text-cyan-400">
            <Cpu className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-xl font-bold tracking-wider text-white">NEXUS</h1>
              <span className="text-xs px-2 py-0.5 rounded bg-cyan-950/80 text-cyan-400 border border-cyan-800/40 font-mono">
                v1.1.1
              </span>
            </div>
            <p className="text-xs text-[#9AA0AA]">
              Personal AI Operating Layer • Control Center
            </p>
          </div>
        </div>

        {/* Global Action Bar */}
        <div className="flex items-center space-x-3">
          <button
            onClick={runProcessNotes}
            disabled={processing}
            className="flex items-center space-x-2 px-4 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white font-medium text-sm transition shadow-lg shadow-cyan-950/40 disabled:opacity-50 cursor-pointer"
          >
            <Play className={`w-4 h-4 fill-current ${processing ? 'animate-spin' : ''}`} />
            <span>{processing ? 'Processing...' : 'Run Process Notes'}</span>
          </button>

          <button
            onClick={() => setSystemCheckOpen(true)}
            className="flex items-center space-x-2 px-3 py-2 rounded-lg bg-[#252A34] hover:bg-[#343B48] text-[#E8EAED] text-sm transition cursor-pointer"
          >
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            <span>System Check</span>
          </button>

          <button
            onClick={() => {
              fetchStatus();
              fetchFeatures();
              fetchInbox();
              fetchCourses();
              fetchProvenance();
              fetchLogs();
              showNotification('Configuration & Status Reloaded');
            }}
            className="p-2 rounded-lg bg-[#252A34] hover:bg-[#343B48] text-[#9AA0AA] hover:text-white transition cursor-pointer"
            title="Reload State"
          >
            <RotateCw className="w-4 h-4" />
          </button>
        </div>
      </header>

      {/* Navigation Tabs */}
      <nav className="bg-[#14171E] border-b border-[#252A34] px-6 flex space-x-1 overflow-x-auto">
        {[
          { id: 'control', label: 'Control Center', icon: Layers },
          { id: 'inbox', label: 'Inbox & Processing', icon: FolderOpen, badge: inboxFiles.length },
          { id: 'knowledge', label: 'Academic Knowledge', icon: BookOpen, badge: courses.reduce((acc, c) => acc + c.notesCount, 0) },
          { id: 'provenance', label: 'Provenance Ledger', icon: Shield, badge: provenance.length },
          { id: 'config', label: 'Configuration', icon: Settings },
          { id: 'logs', label: 'System Logs', icon: Terminal },
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center space-x-2 px-4 py-3 text-sm font-medium border-b-2 transition whitespace-nowrap cursor-pointer ${
                isActive
                  ? 'border-cyan-400 text-cyan-300 bg-cyan-950/20'
                  : 'border-transparent text-[#9AA0AA] hover:text-white hover:border-[#343B48]'
              }`}
            >
              <Icon className="w-4 h-4" />
              <span>{tab.label}</span>
              {tab.badge !== undefined && tab.badge > 0 && (
                <span className="ml-1.5 px-1.5 py-0.2 rounded-full text-xs bg-[#252A34] text-cyan-300 font-mono">
                  {tab.badge}
                </span>
              )}
            </button>
          );
        })}
      </nav>

      {/* Main Content Area */}
      <main className="flex-1 p-6 max-w-7xl w-full mx-auto">
        {/* 1. CONTROL CENTER TAB */}
        {activeTab === 'control' && (
          <div className="space-y-6">
            {/* Quick Stats Grid */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="bg-[#171A21] border border-[#252A34] p-4 rounded-xl">
                <div className="flex items-center justify-between text-xs text-[#9AA0AA] mb-2">
                  <span>ORCHESTRATION</span>
                  <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
                </div>
                <div className="text-xl font-bold text-white">Nexus Ready</div>
                <p className="text-xs text-emerald-400/90 mt-1 font-mono">Headless Core Active</p>
              </div>

              <div className="bg-[#171A21] border border-[#252A34] p-4 rounded-xl">
                <div className="flex items-center justify-between text-xs text-[#9AA0AA] mb-2">
                  <span>AI GATEWAY</span>
                  <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
                </div>
                <div className="text-xl font-bold text-white">
                  {status?.config?.ai?.model || 'gemini-3.8-flash'}
                </div>
                <p className="text-xs text-cyan-400/90 mt-1">Provider: {status?.config?.ai?.provider || 'gemini'}</p>
              </div>

              <div className="bg-[#171A21] border border-[#252A34] p-4 rounded-xl">
                <div className="flex items-center justify-between text-xs text-[#9AA0AA] mb-2">
                  <span>REGISTER INBOX</span>
                  <FolderOpen className="w-3.5 h-3.5 text-amber-400" />
                </div>
                <div className="text-xl font-bold text-white">{inboxFiles.length} files</div>
                <p className="text-xs text-amber-400/90 mt-1">Pending Processing</p>
              </div>

              <div className="bg-[#171A21] border border-[#252A34] p-4 rounded-xl">
                <div className="flex items-center justify-between text-xs text-[#9AA0AA] mb-2">
                  <span>ACADEMIC NOTES</span>
                  <BookOpen className="w-3.5 h-3.5 text-purple-400" />
                </div>
                <div className="text-xl font-bold text-white">
                  {courses.reduce((acc, c) => acc + c.notesCount, 0)} Notes
                </div>
                <p className="text-xs text-purple-400/90 mt-1">Across {courses.length} Courses</p>
              </div>
            </div>

            {/* Feature Registry Cards */}
            <div className="bg-[#171A21] border border-[#252A34] rounded-xl p-6">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h2 className="text-base font-semibold text-white">FEATURE REGISTRY</h2>
                  <p className="text-xs text-[#9AA0AA]">
                    Declared capabilities, status, and activation boundaries
                  </p>
                </div>
                <span className="text-xs font-mono text-[#707782]">Unified Config: config/nexus_config.json</span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {features.map((feature) => (
                  <div
                    key={feature.id}
                    className="p-4 rounded-lg bg-[#12151B] border border-[#252A34] flex items-start justify-between space-x-4"
                  >
                    <div className="space-y-1">
                      <div className="flex items-center space-x-2">
                        <span className="font-semibold text-white text-sm">{feature.display_name}</span>
                        {feature.status === 'implemented' ? (
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-950/80 text-emerald-400 border border-emerald-800/40">
                            IMPLEMENTED
                          </span>
                        ) : (
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-[#252A34] text-[#9AA0AA]">
                            PLANNED
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-[#8F96A1] leading-relaxed">{feature.description}</p>
                    </div>

                    <div>
                      {feature.status === 'implemented' ? (
                        <button
                          onClick={() => toggleFeature(feature.id, feature.enabled)}
                          className={`px-3 py-1.5 rounded text-xs font-bold font-mono transition cursor-pointer ${
                            feature.enabled
                              ? 'bg-emerald-600 text-white hover:bg-emerald-500'
                              : 'bg-[#252A34] text-[#9AA0AA] hover:text-white'
                          }`}
                        >
                          {feature.enabled ? 'ON' : 'OFF'}
                        </button>
                      ) : (
                        <span className="px-3 py-1.5 rounded text-xs font-mono font-medium text-[#707782] bg-[#1a1e26]">
                          DISABLED
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Quick Actions & Live Processing Bar */}
            <div className="bg-[#171A21] border border-[#252A34] rounded-xl p-6">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                  <h3 className="text-sm font-semibold text-white">Process Notes Capability</h3>
                  <p className="text-xs text-[#9AA0AA]">
                    Scans Inbox, classifies source SHA-256, generates Markdown notes via Gemini Gateway, and archives original PDF/photos.
                  </p>
                </div>
                <div className="flex items-center space-x-3">
                  <button
                    onClick={runProcessNotes}
                    disabled={processing}
                    className="flex items-center space-x-2 px-5 py-2.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white font-medium text-sm transition shadow-lg shadow-cyan-950/50 disabled:opacity-50 cursor-pointer"
                  >
                    <Play className="w-4 h-4 fill-current" />
                    <span>{processing ? 'Processing Notes...' : 'Run Pipeline Now'}</span>
                  </button>
                </div>
              </div>

              {processOutput && (
                <div className="mt-4 p-4 rounded-lg bg-[#0d0f14] border border-[#252A34] font-mono text-xs text-[#A0AAB8] max-h-60 overflow-y-auto whitespace-pre-wrap">
                  {processOutput}
                </div>
              )}
            </div>
          </div>
        )}

        {/* 2. INBOX & PROCESSING TAB */}
        {activeTab === 'inbox' && (
          <div className="space-y-6">
            {/* Header + File Uploader */}
            <div className="flex flex-wrap items-center justify-between gap-4 bg-[#171A21] border border-[#252A34] p-6 rounded-xl">
              <div>
                <h2 className="text-base font-semibold text-white">Register Photos & Scans Inbox</h2>
                <p className="text-xs text-[#9AA0AA]">
                  Directory: <code className="text-cyan-400 font-mono">data/inbox/register_photos</code>
                </p>
              </div>

              <div className="flex items-center space-x-3">
                <label className="flex items-center space-x-2 px-4 py-2 rounded-lg bg-[#252A34] hover:bg-[#343B48] text-white text-sm cursor-pointer transition">
                  <Upload className="w-4 h-4 text-cyan-400" />
                  <span>Upload Files</span>
                  <input
                    type="file"
                    multiple
                    accept=".pdf,.png,.jpg,.jpeg"
                    className="hidden"
                    onChange={handleFileUpload}
                  />
                </label>

                <button
                  onClick={runProcessNotes}
                  disabled={processing || inboxFiles.length === 0}
                  className="flex items-center space-x-2 px-4 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-sm font-medium transition disabled:opacity-50 cursor-pointer"
                >
                  <Play className="w-4 h-4 fill-current" />
                  <span>Process All ({inboxFiles.length})</span>
                </button>
              </div>
            </div>

            {/* Inbox Files Table */}
            <div className="bg-[#171A21] border border-[#252A34] rounded-xl overflow-hidden">
              <table className="w-full text-left text-sm">
                <thead className="bg-[#14171E] border-b border-[#252A34] text-xs font-mono text-[#8E96A3]">
                  <tr>
                    <th className="px-6 py-3">FILE NAME</th>
                    <th className="px-6 py-3">COURSE ROUTING</th>
                    <th className="px-6 py-3">SIZE</th>
                    <th className="px-6 py-3">LAST MODIFIED</th>
                    <th className="px-6 py-3 text-right">ACTION</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#252A34]">
                  {inboxFiles.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="px-6 py-8 text-center text-sm text-[#707782]">
                        No register files in inbox. Upload a PDF or photo with format <code className="text-cyan-400">ICT_2026-09-30_Class2.pdf</code> to process.
                      </td>
                    </tr>
                  ) : (
                    inboxFiles.map((f) => {
                      const prefix = f.name.split('_')[0];
                      return (
                        <tr key={f.name} className="hover:bg-[#1C202A] transition">
                          <td className="px-6 py-3 font-mono font-medium text-white flex items-center space-x-2">
                            <FileText className="w-4 h-4 text-cyan-400" />
                            <span>{f.name}</span>
                          </td>
                          <td className="px-6 py-3 text-xs">
                            <span className="px-2 py-0.5 rounded bg-cyan-950/80 text-cyan-300 border border-cyan-800/40">
                              Prefix: {prefix}
                            </span>
                          </td>
                          <td className="px-6 py-3 font-mono text-xs text-[#9AA0AA]">
                            {(f.size / 1024).toFixed(1)} KB
                          </td>
                          <td className="px-6 py-3 text-xs text-[#9AA0AA]">
                            {new Date(f.modified).toLocaleString()}
                          </td>
                          <td className="px-6 py-3 text-right">
                            <button
                              onClick={() => deleteInboxFile(f.name)}
                              className="p-1.5 rounded hover:bg-rose-950/50 text-rose-400 transition cursor-pointer"
                              title="Delete from Inbox"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>

            {/* Pipeline Live Terminal Output */}
            {processOutput && (
              <div className="bg-[#171A21] border border-[#252A34] rounded-xl p-5">
                <div className="flex items-center space-x-2 mb-3 text-xs font-mono text-cyan-400">
                  <Terminal className="w-4 h-4" />
                  <span>PROCESS NOTES CONSOLE OUTPUT</span>
                </div>
                <pre className="p-4 rounded-lg bg-[#0c0e12] border border-[#252A34] text-xs font-mono text-emerald-400/90 whitespace-pre-wrap max-h-72 overflow-y-auto">
                  {processOutput}
                </pre>
              </div>
            )}
          </div>
        )}

        {/* 3. ACADEMIC KNOWLEDGE TAB */}
        {activeTab === 'knowledge' && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Courses Column */}
            <div className="space-y-4">
              <h2 className="text-sm font-bold tracking-wider text-[#9AA0AA] uppercase">
                Semester 1 Courses
              </h2>
              <div className="space-y-2">
                {courses.map((c) => (
                  <button
                    key={c.name}
                    onClick={() => {
                      setSelectedCourse(c.name);
                      setSelectedNote(null);
                    }}
                    className={`w-full text-left p-3.5 rounded-xl border transition flex items-center justify-between cursor-pointer ${
                      selectedCourse === c.name
                        ? 'bg-cyan-950/30 border-cyan-500/50 text-white'
                        : 'bg-[#171A21] border-[#252A34] text-[#A0AAB8] hover:bg-[#1E232D]'
                    }`}
                  >
                    <div>
                      <div className="font-semibold text-sm">{c.name}</div>
                      <div className="text-xs text-[#707782] mt-0.5">
                        {c.notesCount} notes • {c.rawCount} archived
                      </div>
                    </div>
                    <ChevronRight className="w-4 h-4 text-[#707782]" />
                  </button>
                ))}
              </div>
            </div>

            {/* Notes List & Document Preview */}
            <div className="md:col-span-2 space-y-4">
              <div className="bg-[#171A21] border border-[#252A34] rounded-xl p-5">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h3 className="text-base font-bold text-white">{selectedCourse}</h3>
                    <p className="text-xs text-[#9AA0AA]">
                      Generated academic notes and archived source documents
                    </p>
                  </div>
                </div>

                {/* Course Notes List */}
                <div className="space-y-2 mb-6">
                  <h4 className="text-xs font-bold text-[#8E96A3] uppercase">Markdown Notes:</h4>
                  {courses.find((c) => c.name === selectedCourse)?.notes.length === 0 ? (
                    <p className="text-xs text-[#707782] py-2">No Markdown notes generated yet.</p>
                  ) : (
                    courses.find((c) => c.name === selectedCourse)?.notes.map((note) => (
                      <div
                        key={note}
                        onClick={() => loadNoteContent(selectedCourse, note)}
                        className={`p-3 rounded-lg border flex items-center justify-between cursor-pointer transition ${
                          selectedNote?.filename === note
                            ? 'bg-cyan-900/30 border-cyan-500/50 text-white'
                            : 'bg-[#12151B] border-[#252A34] hover:bg-[#1A1E26] text-[#C0C8D2]'
                        }`}
                      >
                        <div className="flex items-center space-x-2 text-sm font-mono">
                          <FileText className="w-4 h-4 text-cyan-400" />
                          <span>{note}</span>
                        </div>
                        <button className="text-xs text-cyan-400 flex items-center space-x-1">
                          <Eye className="w-3.5 h-3.5" />
                          <span>View Note</span>
                        </button>
                      </div>
                    ))
                  )}
                </div>

                {/* Note Viewer Window */}
                {selectedNote && (
                  <div className="border border-cyan-500/30 rounded-lg bg-[#0e1116] p-5 animate-fade-in">
                    <div className="flex items-center justify-between pb-3 mb-3 border-b border-[#252A34]">
                      <div className="flex items-center space-x-2">
                        <FileText className="w-4 h-4 text-cyan-400" />
                        <span className="font-mono text-sm font-bold text-white">{selectedNote.filename}</span>
                      </div>
                      <span className="text-xs px-2 py-0.5 rounded bg-emerald-950/80 text-emerald-400 border border-emerald-800/40">
                        Markdown Note
                      </span>
                    </div>
                    <div className="prose prose-invert max-w-none text-xs text-[#D0D7DE] font-mono leading-relaxed whitespace-pre-wrap max-h-96 overflow-y-auto">
                      {selectedNote.content}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* 4. PROVENANCE LEDGER TAB */}
        {activeTab === 'provenance' && (
          <div className="space-y-6">
            <div className="bg-[#171A21] border border-[#252A34] p-6 rounded-xl flex items-center justify-between">
              <div>
                <h2 className="text-base font-semibold text-white">Cryptographic Processing Ledger</h2>
                <p className="text-xs text-[#9AA0AA]">
                  Immutable SHA-256 source identity records, deduplication audit trail, and processing metadata
                </p>
              </div>
              <span className="px-3 py-1 rounded bg-[#252A34] text-xs font-mono text-cyan-400 border border-cyan-500/20">
                {provenance.length} Total Records
              </span>
            </div>

            <div className="bg-[#171A21] border border-[#252A34] rounded-xl overflow-hidden">
              <table className="w-full text-left text-sm">
                <thead className="bg-[#14171E] border-b border-[#252A34] text-xs font-mono text-[#8E96A3]">
                  <tr>
                    <th className="px-6 py-3">SOURCE FILE</th>
                    <th className="px-6 py-3">SHA-256 HASH</th>
                    <th className="px-6 py-3">SIZE / MIME</th>
                    <th className="px-6 py-3">STATUS</th>
                    <th className="px-6 py-3">PROCESSED AT</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#252A34]">
                  {provenance.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="px-6 py-8 text-center text-sm text-[#707782]">
                        No processing records yet. Files processed via Process Notes will record their SHA-256 hash here.
                      </td>
                    </tr>
                  ) : (
                    provenance.map((rec, i) => (
                      <tr key={i} className="hover:bg-[#1C202A] transition">
                        <td className="px-6 py-3 font-mono font-medium text-white">
                          {rec.source.filename}
                        </td>
                        <td className="px-6 py-3 font-mono text-xs text-cyan-300/80">
                          {rec.source.content_hash.slice(0, 16)}...
                        </td>
                        <td className="px-6 py-3 text-xs text-[#9AA0AA] font-mono">
                          {(rec.source.size_bytes / 1024).toFixed(1)} KB ({rec.source.mime_type})
                        </td>
                        <td className="px-6 py-3">
                          <span
                            className={`px-2 py-0.5 rounded text-xs font-bold font-mono ${
                              rec.status === 'completed'
                                ? 'bg-emerald-950/80 text-emerald-400 border border-emerald-800/40'
                                : 'bg-rose-950/80 text-rose-400 border border-rose-800/40'
                            }`}
                          >
                            {rec.status.toUpperCase()}
                          </span>
                        </td>
                        <td className="px-6 py-3 text-xs text-[#9AA0AA]">
                          {new Date(rec.updated_at).toLocaleString()}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* 5. CONFIGURATION TAB */}
        {activeTab === 'config' && (
          <div className="space-y-6">
            <div className="bg-[#171A21] border border-[#252A34] p-6 rounded-xl">
              <h2 className="text-base font-semibold text-white mb-1">Nexus System Configuration</h2>
              <p className="text-xs text-[#9AA0AA]">
                Validated configuration managed by headless Core in <code className="text-cyan-400">config/nexus_config.json</code>
              </p>

              <div className="mt-6 space-y-4 max-w-2xl">
                <div>
                  <label className="block text-xs font-mono text-[#8E96A3] mb-1">AI MODEL</label>
                  <input
                    type="text"
                    disabled
                    value={status?.config?.ai?.model || 'gemini-3.8-flash'}
                    className="w-full p-2.5 rounded-lg bg-[#101318] border border-[#252A34] text-white font-mono text-sm"
                  />
                </div>

                <div>
                  <label className="block text-xs font-mono text-[#8E96A3] mb-1">AI PROVIDER</label>
                  <input
                    type="text"
                    disabled
                    value={status?.config?.ai?.provider || 'gemini'}
                    className="w-full p-2.5 rounded-lg bg-[#101318] border border-[#252A34] text-white font-mono text-sm"
                  />
                </div>

                <div>
                  <label className="block text-xs font-mono text-[#8E96A3] mb-1">INBOX PATH</label>
                  <input
                    type="text"
                    disabled
                    value={status?.config?.paths?.inbox || 'data/inbox'}
                    className="w-full p-2.5 rounded-lg bg-[#101318] border border-[#252A34] text-white font-mono text-sm"
                  />
                </div>

                <div>
                  <label className="block text-xs font-mono text-[#8E96A3] mb-1">ACADEMIC KNOWLEDGE PATH</label>
                  <input
                    type="text"
                    disabled
                    value={status?.config?.paths?.academic || 'data/knowledge/academic/Semester1'}
                    className="w-full p-2.5 rounded-lg bg-[#101318] border border-[#252A34] text-white font-mono text-sm"
                  />
                </div>

                <div>
                  <label className="block text-xs font-mono text-[#8E96A3] mb-1">LOG LEVEL</label>
                  <input
                    type="text"
                    disabled
                    value={status?.config?.runtime?.log_level || 'INFO'}
                    className="w-full p-2.5 rounded-lg bg-[#101318] border border-[#252A34] text-white font-mono text-sm"
                  />
                </div>
              </div>
            </div>
          </div>
        )}

        {/* 6. SYSTEM LOGS TAB */}
        {activeTab === 'logs' && (
          <div className="space-y-6">
            <div className="bg-[#171A21] border border-[#252A34] p-6 rounded-xl">
              <h2 className="text-base font-semibold text-white mb-2">Nexus Diagnostic Logs</h2>
              <p className="text-xs text-[#9AA0AA]">
                Direct logs from <code className="text-cyan-400">logs/nexus_core.log</code> and <code className="text-cyan-400">logs/process_notes.log</code>
              </p>

              <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <h3 className="text-xs font-mono text-[#8E96A3] mb-2 uppercase">Nexus Core Log:</h3>
                  <pre className="p-4 rounded-lg bg-[#0c0e12] border border-[#252A34] text-xs font-mono text-[#A0AAB8] h-96 overflow-y-auto whitespace-pre-wrap">
                    {logs.core || 'No core logs recorded yet.'}
                  </pre>
                </div>

                <div>
                  <h3 className="text-xs font-mono text-[#8E96A3] mb-2 uppercase">Process Notes Log:</h3>
                  <pre className="p-4 rounded-lg bg-[#0c0e12] border border-[#252A34] text-xs font-mono text-cyan-300/80 h-96 overflow-y-auto whitespace-pre-wrap">
                    {logs.process_notes || 'No process notes logs recorded yet.'}
                  </pre>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* System Check Modal */}
      {systemCheckOpen && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-xs flex items-center justify-center z-50 p-4">
          <div className="bg-[#171A21] border border-[#252A34] rounded-xl max-w-md w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between pb-3 border-b border-[#252A34]">
              <div className="flex items-center space-x-2">
                <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                <h3 className="text-base font-bold text-white">Nexus System Check</h3>
              </div>
              <button
                onClick={() => setSystemCheckOpen(false)}
                className="text-[#707782] hover:text-white cursor-pointer"
              >
                ✕
              </button>
            </div>

            <div className="space-y-2 py-2">
              {status?.checks ? (
                Object.entries(status.checks).map(([key, val]) => (
                  <div key={key} className="flex items-center justify-between text-xs py-1.5 border-b border-[#252A34]/50">
                    <span className="font-mono text-[#A0AAB8] uppercase">{key.replace('_', ' ')}:</span>
                    <span
                      className={`font-mono font-bold px-2 py-0.5 rounded ${
                        val
                          ? 'bg-emerald-950/80 text-emerald-400 border border-emerald-800/40'
                          : 'bg-rose-950/80 text-rose-400 border border-rose-800/40'
                      }`}
                    >
                      {val ? 'OK' : 'MISSING'}
                    </span>
                  </div>
                ))
              ) : (
                <p className="text-xs text-[#707782]">Checking system components...</p>
              )}
            </div>

            <button
              onClick={() => setSystemCheckOpen(false)}
              className="w-full py-2 rounded-lg bg-[#252A34] hover:bg-[#343B48] text-white text-sm font-medium transition cursor-pointer"
            >
              Close
            </button>
          </div>
        </div>
      )}

      {/* Footer */}
      <footer className="border-t border-[#252A34] bg-[#14171E] px-6 py-3 text-xs text-[#707782] flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center space-x-4">
          <span>Nexus v1.1.1</span>
          <span>•</span>
          <span>Config: config/nexus_config.json</span>
        </div>
        <div>
          <span>Local-First & Provider-Agnostic Architecture</span>
        </div>
      </footer>
    </div>
  );
}
