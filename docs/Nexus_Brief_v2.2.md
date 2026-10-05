# NEXUS BRIEF (v2.2, last updated 2026-10-04)

**Instructions for any AI reading this:** read the whole file before replying. Follow the rules below. Give one step at a time and wait for Rai's result before the next. If you are unsure about a tool, version or price, say so and recommend checking a current source instead of guessing. Do not invent features. Do not repeat the plan back; just do your role.

## What Nexus is
A lifelong personal AI system and second brain for Rai (BSCS, Semester 1, UCP Lahore, Pakistan). Not a chatbot and not a Jarvis clone. First goal: answer questions from Rai's own notes and files, with sources. Then grow into a general assistant for study, coding, projects, career and daily life.

## Hard rules
1. **Free only for now.** Upgrade to paid tools only when Rai has income.
2. **Files are permanent, tools are replaceable.** All knowledge lives as plain files (PDF, JPG, MD, TXT, DOCX, XLSX) in `D:\Nexus`, synced to Google Drive.
3. **Four layers, each swappable without touching the one below:**
   1. Files (`D:\Nexus` + Google Drive)
   2. Search index (rebuilt from the files, disposable)
   3. Models (local Qwen 3 8B via Ollama, plus free cloud models)
   4. Tools and interface (AnythingLLM first, others later)
4. **One step at a time.** No giant roadmaps or 50-step plans.
5. **Answers from notes must point to the source page or file.** Handwriting OCR is only about 50-60% accurate, so the original PDF is the truth.
6. **AI is a tutor, not a ghostwriter**, for assignments and quizzes.
7. **Nothing that changes or deletes files happens without Rai's approval.**
8. **No passwords, ID numbers or phone numbers go into this file or into the knowledge base.**
9. **If Rai doesn't know a term, tool or concept, explain it in plain words first.** Assume a beginner; no jargon without a one-line explanation.
10. **Stay inside this brief.** Do not bring in personal details from Rai's other accounts or activity unless he asks.

## Hardware
HP Victus 15 FA0033DX: Intel i5-12450H, 16GB RAM, RTX 3050 with 4GB VRAM, 142GB SSD (about 82GB free at last check). Windows edition reported as Windows 11 IoT Enterprise LTSC (unconfirmed; some apps may refuse to install on it). The 4GB GPU limits local model size and speed, so expect slow responses from 8B models. RAM and SSD upgrades are planned for later.

## Folder structure (`D:\Nexus`)
- `Inbox\` (unsorted new files, including `Register Photos\`)
- `Semester1\<Course>\raw` (originals, never edited) and `notes` (text versions)
- Courses: Basic Electronics (+Lab), Functional English, Logic Thinking, Financial Account, Introduction to Computing (+Lab), Ideology and Constitution of Pakistan
- Register PDFs are named `Course_YYYY-MM-DD_ClassN.pdf` (e.g. `ICT_2026-09-30_Class2.pdf`)
- Add `Semester2` and later folders only when that semester starts.

## AI team and roles
- **Claude: lead builder and strategic reviewer.** Step-by-step guidance, challenges weak ideas, reviews writing and architecture.
- **Copilot: architect.** System design, structure, planning.
- **Gemini: researcher.** Compares free tools, checks current information, gives a second opinion.
- Rai makes the final decision. Agreement between AIs is not proof; test on the real laptop.

## Done so far
- Storage cleaned, Ollama 0.35.1 installed, Qwen 3 8B working
- Folder structure created and verified
- Google Drive sync verified; all available online Semester 1 material archived in each course's `raw` folder
- Register notes photographed with iPhone 12, converted to PDF, renamed and filed
- Google Docs OCR test on handwriting: roughly 50-60% accurate (diagrams and handwriting limit it)
- WSL appears to be installed (Linux entry visible in File Explorer)
- Docker Desktop failed to install ("This app can't run on your PC"), unresolved; Docker and Open WebUI are parked
- AnythingLLM not installed yet

## Current step
Install AnythingLLM Desktop (free), connect it to local Qwen through Ollama, and let it answer questions from the typed course material with sources.

## After that (one at a time, rough order)
1. Search across all courses, or one course at a time
2. Quizzes, flashcards, mids and finals prep from own material
3. Handwritten-notes pipeline (OCR plus a short typed caption per page; "HINT:" tag for teacher tips)
4. Create Word, Excel and PowerPoint files
5. Draft emails and WhatsApp messages (Rai sends them)
6. Control from iPhone 12
7. Voice, then carefully limited PC control

Good ideas to add when the basics work:
- **Reverse tutor:** Rai explains a concept to the AI, and the AI points out gaps and mistakes in his explanation.
- **Syllabus to deadlines:** extract dates from course outlines into one checklist; always verify the dates against the original outline.
- **Screenshot trick:** screenshot an error (Win+Shift+S) and paste it into an AI to get it explained. Free-tier cloud AI may use pasted content, so never paste anything private.

## Parked or dropped
- **AI phone calls and reservations:** WhatsApp's official calling needs the Cloud API, a payment method and the other person's permission; unofficial automation risks a ban. Draft messages instead.
- Hand-gesture control, home automation, heavy animated slides, custom visual interface: later or never.
- Coding autocomplete is not first priority: as a first-year student Rai writes code himself; AI explains errors and checks work after he tries.
- Discussed but not decided: Open WebUI, Open Interpreter, Mark-LV, Coucou, AutoGPT, Claude Code.

## Rule for any future agent that talks to people
It must say clearly that it is an AI acting for Rai.
