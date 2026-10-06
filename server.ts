import express from 'express';
import cors from 'cors';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawn } from 'node:child_process';
import { createServer as createHttpServer } from 'node:http';
import multer from 'multer';
import dotenv from 'dotenv';

dotenv.config();

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const PORT = 3000;
const HOST = '0.0.0.0';

app.use(cors());
app.use(express.json());

const ROOT_DIR = __dirname;
const CONFIG_FILE = path.join(ROOT_DIR, 'config', 'nexus_config.json');
const DATA_DIR = path.join(ROOT_DIR, 'data');
const INBOX_DIR = path.join(DATA_DIR, 'inbox', 'register_photos');
const ACADEMIC_DIR = path.join(DATA_DIR, 'knowledge', 'academic', 'Semester1');
const PROVENANCE_FILE = path.join(DATA_DIR, 'provenance', 'processing_records.json');
const LOGS_DIR = path.join(ROOT_DIR, 'logs');

// Ensure base directories exist
[
  INBOX_DIR,
  ACADEMIC_DIR,
  path.join(DATA_DIR, 'provenance'),
  LOGS_DIR,
  path.join(ROOT_DIR, 'backups'),
].forEach((dir) => {
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
});

// Seed default course directories if empty
const DEFAULT_COURSES = [
  'Introduction to Computing',
  'Introduction to Computing - Lab',
  'Basic Electronics',
  'Basic Electronics - Lab',
  'Functional English',
  'Logic Thinking',
  'Financial Account',
  'Ideology and Constitution of Pakistan',
];

DEFAULT_COURSES.forEach((course) => {
  const coursePath = path.join(ACADEMIC_DIR, course);
  const rawPath = path.join(coursePath, 'raw');
  const notesPath = path.join(coursePath, 'notes');
  if (!fs.existsSync(rawPath)) fs.mkdirSync(rawPath, { recursive: true });
  if (!fs.existsSync(notesPath)) fs.mkdirSync(notesPath, { recursive: true });
});

// Configure multer for file uploads to inbox
const storage = multer.diskStorage({
  destination: (_req, _file, cb) => {
    cb(null, INBOX_DIR);
  },
  filename: (_req, file, cb) => {
    cb(null, file.originalname);
  },
});
const upload = multer({ storage });

// Helper to load nexus_config.json safely
function loadNexusConfig() {
  if (!fs.existsSync(CONFIG_FILE)) {
    return {};
  }
  try {
    return JSON.parse(fs.readFileSync(CONFIG_FILE, 'utf-8'));
  } catch {
    return {};
  }
}

// Helper to save nexus_config.json
function saveNexusConfig(config: Record<string, unknown>) {
  fs.writeFileSync(CONFIG_FILE, JSON.stringify(config, null, 4), 'utf-8');
}

// ================= API ROUTES =================

// 1. System status & check
app.get('/api/system-status', (_req, res) => {
  const config = loadNexusConfig();
  const checks = {
    core: fs.existsSync(path.join(ROOT_DIR, 'app', 'core', 'nexus_core.py')),
    gui: fs.existsSync(path.join(ROOT_DIR, 'app', 'ui', 'gui.py')),
    config: fs.existsSync(CONFIG_FILE),
    process_notes: fs.existsSync(path.join(ROOT_DIR, 'app', 'capabilities', 'process_notes', 'process_notes.py')),
    inbox: fs.existsSync(INBOX_DIR),
    academic: fs.existsSync(ACADEMIC_DIR),
    provenance: fs.existsSync(PROVENANCE_FILE),
    gemini_key_configured: Boolean(process.env.GEMINI_API_KEY),
  };

  res.json({
    status: 'ready',
    version: '1.1.1',
    name: 'Nexus',
    environment: 'AI Studio Cloud',
    checks,
    config,
  });
});

// 2. Configuration GET/PUT
app.get('/api/config', (_req, res) => {
  res.json(loadNexusConfig());
});

app.put('/api/config', (req, res) => {
  try {
    const updated = req.body;
    saveNexusConfig(updated);
    res.json({ success: true, config: updated });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : String(err);
    res.status(500).json({ success: false, error: message });
  }
});

// 3. Feature Registry
app.get('/api/features', (_req, res) => {
  const config = loadNexusConfig();
  const featureConfigs = (config.features as Record<string, boolean>) || {};

  const features = [
    {
      id: 'process_notes',
      display_name: 'Process Notes',
      description: 'Automatically process register photos and documents into academic notes.',
      status: 'implemented',
      enabled: featureConfigs.process_notes ?? true,
    },
    {
      id: 'pc_control',
      display_name: 'PC Control',
      description: 'Controlled computer interaction is planned for a future release.',
      status: 'planned',
      enabled: false,
    },
    {
      id: 'screen_vision',
      display_name: 'Screen Vision',
      description: 'Understanding the computer screen is planned for a future release.',
      status: 'planned',
      enabled: false,
    },
    {
      id: 'communications',
      display_name: 'Communications',
      description: 'Controlled communication services are planned for a future release.',
      status: 'planned',
      enabled: false,
    },
  ];

  res.json(features);
});

app.post('/api/features/:id/toggle', (req, res) => {
  const { id } = req.params;
  const { enabled } = req.body;

  if (id !== 'process_notes') {
    return res.status(400).json({
      error: `Feature '${id}' is planned and cannot be enabled.`,
    });
  }

  const config = loadNexusConfig();
  if (!config.features) config.features = {};
  config.features[id] = Boolean(enabled);
  saveNexusConfig(config);

  res.json({ success: true, id, enabled: Boolean(enabled) });
});

// 4. Inbox Files
app.get('/api/inbox', (_req, res) => {
  try {
    if (!fs.existsSync(INBOX_DIR)) {
      return res.json([]);
    }
    const files = fs.readdirSync(INBOX_DIR).map((name) => {
      const filePath = path.join(INBOX_DIR, name);
      const stats = fs.statSync(filePath);
      return {
        name,
        size: stats.size,
        modified: stats.mtime,
        extension: path.extname(name).toLowerCase(),
      };
    });
    res.json(files);
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : String(err);
    res.status(500).json({ error: message });
  }
});

app.post('/api/inbox/upload', upload.array('files'), (req, res) => {
  res.json({
    success: true,
    uploaded: (req.files as Express.Multer.File[])?.map((f) => f.originalname) || [],
  });
});

app.delete('/api/inbox/:filename', (req, res) => {
  const filePath = path.join(INBOX_DIR, req.params.filename);
  if (fs.existsSync(filePath)) {
    fs.unlinkSync(filePath);
    res.json({ success: true });
  } else {
    res.status(404).json({ error: 'File not found' });
  }
});

// 5. Run Process Notes
app.post('/api/process-notes', (_req, res) => {
  const scriptPath = path.join(ROOT_DIR, 'app', 'capabilities', 'process_notes', 'process_notes.py');
  
  const pyProcess = spawn('python3', [scriptPath], {
    cwd: ROOT_DIR,
    env: { ...process.env },
  });

  let stdout = '';
  let stderr = '';

  pyProcess.stdout.on('data', (data) => {
    stdout += data.toString();
  });

  pyProcess.stderr.on('data', (data) => {
    stderr += data.toString();
  });

  pyProcess.on('close', (code) => {
    res.json({
      success: code === 0,
      exitCode: code,
      stdout,
      stderr,
    });
  });
});

// 6. Courses & Knowledge Explorer
app.get('/api/courses', (_req, res) => {
  try {
    if (!fs.existsSync(ACADEMIC_DIR)) {
      return res.json([]);
    }
    const courses = fs.readdirSync(ACADEMIC_DIR, { withFileTypes: true })
      .filter((d) => d.isDirectory())
      .map((d) => {
        const coursePath = path.join(ACADEMIC_DIR, d.name);
        const notesDir = path.join(coursePath, 'notes');
        const rawDir = path.join(coursePath, 'raw');

        const notes = fs.existsSync(notesDir)
          ? fs.readdirSync(notesDir).filter((f) => f.endsWith('.md'))
          : [];
        const raw = fs.existsSync(rawDir)
          ? fs.readdirSync(rawDir).filter((f) => !f.startsWith('.'))
          : [];

        return {
          name: d.name,
          notesCount: notes.length,
          rawCount: raw.length,
          notes,
          raw,
        };
      });
    res.json(courses);
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : String(err);
    res.status(500).json({ error: message });
  }
});

app.get('/api/notes/:course/:filename', (req, res) => {
  const { course, filename } = req.params;
  const filePath = path.join(ACADEMIC_DIR, course, 'notes', filename);

  if (!fs.existsSync(filePath)) {
    return res.status(404).json({ error: 'Note not found' });
  }

  const content = fs.readFileSync(filePath, 'utf-8');
  res.json({ course, filename, content });
});

// 7. Provenance Records
app.get('/api/provenance', (_req, res) => {
  if (!fs.existsSync(PROVENANCE_FILE)) {
    return res.json({ records: [] });
  }
  try {
    const data = JSON.parse(fs.readFileSync(PROVENANCE_FILE, 'utf-8'));
    res.json(data);
  } catch {
    res.json({ records: [] });
  }
});

// 8. Logs
app.get('/api/logs', (_req, res) => {
  const coreLog = path.join(LOGS_DIR, 'nexus_core.log');
  const processLog = path.join(LOGS_DIR, 'process_notes.log');

  const logs = {
    core: fs.existsSync(coreLog) ? fs.readFileSync(coreLog, 'utf-8').split('\n').slice(-100).join('\n') : '',
    process_notes: fs.existsSync(processLog) ? fs.readFileSync(processLog, 'utf-8').split('\n').slice(-100).join('\n') : '',
  };

  res.json(logs);
});

// ================= VITE DEV SERVER INTEGRATION =================

async function startServer() {
  const httpServer = createHttpServer(app);

  if (process.env.NODE_ENV !== 'production') {
    const { createServer: createViteServer } = await import('vite');
    const vite = await createViteServer({
      server: {
        middlewareMode: true,
        // The hosted preview proxies HTTP but does not keep Vite's HMR socket
        // open, which causes the injected client to report a closed WebSocket.
        hmr: false,
  ws: false,
      },
      appType: 'spa',
    });
    app.use(vite.middlewares);
  } else {
    app.use(express.static(path.join(ROOT_DIR, 'dist')));
    app.get('*', (_req, res) => {
      res.sendFile(path.join(ROOT_DIR, 'dist', 'index.html'));
    });
  }

  httpServer.listen(PORT, HOST, () => {
    console.log(`[NEXUS] Control Center server listening at http://${HOST}:${PORT}`);
  });
}

startServer().catch((err) => {
  console.error('[NEXUS] Failed to start server:', err);
  process.exit(1);
});
