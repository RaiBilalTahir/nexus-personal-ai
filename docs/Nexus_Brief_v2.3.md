Yes. Make **v2.3 a complete replacement copy of v2.2**, with the outdated architecture/current-step sections corrected.

Create:

`D:\Nexus\Nexus_Brief v2.3.md`

and paste **exactly this**:

````markdown
# NEXUS BRIEF (v2.3, last updated 2026-10-04)

**Instructions for any AI reading this:** read the whole file before replying. Follow the rules below. Give one step at a time and wait for Rai's result before the next. If you are unsure about a tool, version or price, say so and recommend checking a current source instead of guessing. Do not invent features. Do not repeat the plan back; just do your role.

## What Nexus is

Nexus is a lifelong personal AI operating system and second brain for Rai (BSCS, Semester 1, UCP Lahore, Pakistan).

It is not intended to be merely a chatbot. Its long-term goal is to become a highly capable, expandable personal AI system that can understand Rai's files, screen, voice, tasks and context; reason about requests; use controlled tools; ask permission when needed; perform actions; verify results; and learn from outcomes.

The long-term interface may become a sophisticated JARVIS-inspired graphical and voice interface, but Nexus must remain its own system rather than trying to copy a fictional assistant.

The core operating philosophy is:

**SEE → UNDERSTAND → REMEMBER → PLAN → ASK PERMISSION WHEN NEEDED → ACT → VERIFY → LEARN**

The system must be modular and expandable. New capabilities should be added as modules without repeatedly rewriting the core.

The first practical goal remains reliable question-answering and study assistance from Rai's own course material, with answers pointing back to the original source file/page where possible.

## Hard rules

1. **Free only for now.** Upgrade to paid tools only when Rai has income.

2. **Files are permanent, tools are replaceable.** All important knowledge should live as ordinary files (PDF, JPG, MD, TXT, DOCX, XLSX, etc.) inside `D:\Nexus`, with Google Drive synchronization. Search indexes, models and applications are replaceable.

3. **Architecture must be modular.** The user interface, core orchestration, memory, permissions/privacy, feature registry, models and individual tools should have clear boundaries so one layer can eventually be replaced without rebuilding the entire system.

4. **One step at a time.** Do not give Rai giant implementation plans or 50-step instructions. Give the next concrete step, wait for the result, then continue.

5. **Answers from notes must point to the source page or file.** Handwriting OCR is only about 50-60% accurate, so the original PDF/image is the source of truth.

6. **AI is a tutor, not a ghostwriter**, for assignments and quizzes. Rai should understand and attempt work himself; AI should explain, teach, check and guide.

7. **Nothing that changes or deletes files happens without Rai's approval.** This includes automated file moves, edits, deletion or destructive cleanup.

8. **No passwords, ID numbers or phone numbers go into this file or into the knowledge base.**

9. **If Rai doesn't know a term, tool or concept, explain it in plain words first.** Assume a beginner; no jargon without a one-line explanation.

10. **Stay inside this brief.** Do not bring in personal details from Rai's other accounts or activity unless he asks.

11. **Do not expose unnecessary technical complexity to Rai.** Normal Nexus operation should eventually be controlled through the graphical interface rather than requiring command-line or code editing.

12. **Test before declaring something complete.** Architecture decisions are not considered proven until they work on the real laptop.

13. **Do not pretend an unimplemented feature works.** Features may exist in the architecture as planned capabilities, but the interface must clearly distinguish implemented, disabled and planned functionality.

14. **Security over convenience for high-impact actions.** Voice recognition or AI confidence alone must never be treated as perfect authorization for sensitive actions.

## Core architecture

Nexus should evolve toward the following architecture:

```text
                         ┌──────────────────────┐
                         │      NEXUS UI        │
                         │ Current GUI → Future  │
                         │ JARVIS-style UI      │
                         └──────────┬───────────┘
                                    │
                              Commands / State
                                    │
                         ┌──────────▼───────────┐
                         │      NEXUS CORE      │
                         │     Orchestrator     │
                         └──────────┬───────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              │                     │                     │
       ┌──────▼──────┐      ┌──────▼──────┐      ┌──────▼──────┐
       │   MEMORY    │      │ PERMISSIONS │      │   PRIVACY   │
       └─────────────┘      └─────────────┘      └─────────────┘
                                    │
                         ┌──────────▼───────────┐
                         │   FEATURE REGISTRY   │
                         └──────────┬───────────┘
                                    │
          ┌──────────────┬──────────┼──────────┬──────────────┐
          ▼              ▼          ▼          ▼              ▼
      Process Notes   Screen     PC Control  Voice       Communications
                      Vision
````

The exact implementation may evolve, but the boundaries should remain clear.

Nexus Core should eventually be a lightweight orchestrator rather than a giant file containing every capability.

Individual capabilities should live in modules.

The GUI should eventually communicate with Core through clean interfaces rather than containing business logic. The current GUI may temporarily call Core functions directly while the architecture is being built.

Do not introduce a complicated event bus prematurely. First establish clean interfaces and module boundaries. Add an event-driven system when background events, voice, vision and automation genuinely require it.

## Core execution philosophy

For actions involving tools or the computer, Nexus should eventually follow:

**Perception → Memory → Reasoning → Planning → Permission → Tool Execution → Verification → Response**

Nexus should not allow a language model to execute arbitrary shell commands directly.

Instead, capabilities should be exposed through controlled, parameterized tools with clear permissions.

High-impact actions should require explicit human approval even when Nexus is confident about the user's identity or intent.

## Feature Registry

Nexus will use a central Feature Registry to describe available capabilities.

Each feature should eventually have information such as:

* stable feature ID
* display name
* description
* implementation status
* enabled/disabled state
* required permission level
* privacy restrictions
* module/tool association

The registry should allow the GUI and Core to discover available features without hardcoding every feature separately.

The first implementation should remain simple and dependency-free.

Planned capabilities may appear in the registry before they are implemented, but they must be clearly marked as planned/unavailable.

## Permissions

Nexus will eventually have a centralized Permission Gate.

Actions should be classified roughly as:

* **Low impact:** safe informational operations
* **Medium impact:** actions that affect files, applications or workflows but are reversible
* **High impact:** communications, account actions, destructive file operations, financial actions, security-sensitive actions or other consequential operations

High-impact actions require explicit approval.

The permission system should be centralized rather than implemented independently by every module.

## Privacy modes

Nexus should eventually support four privacy modes:

### Normal

Normal Nexus operation.

### Presentation Mode

Designed for screen sharing, presentations and calls.

The Nexus interface and notifications should be minimized or hidden where practical, while approved background functions may continue.

Sensitive Nexus information should not intentionally appear in the shared screen.

### Ghost Mode

A stronger privacy mode in which the visible Nexus interface is hidden or minimized where practical.

Proactive logging and unnecessary context persistence should be reduced or disabled according to the defined policy.

### Lockdown Mode

The strongest privacy/security mode.

Sensitive capabilities such as PC control, screen vision and external communications should be disabled until Nexus is explicitly unlocked.

Lockdown should use safe, verified software controls. Do not assume that physically disconnecting networking or killing system processes is necessary or appropriate.

Privacy modes must eventually affect actual system behavior, not merely change a GUI label.

The exact enforcement must be tested against the real applications Rai uses for screen sharing and calls.

## Voice identity

Voice is a planned major capability.

Nexus should eventually be able to:

* recognize Rai's voice
* distinguish different speakers
* identify trusted versus unknown speakers
* personalize responses based on speaker identity
* use speaker identity as one input into permission decisions

Voice recognition must not be treated as perfect security because recordings, replay attacks and voice cloning are possible.

Voice identity can provide convenience and personalization, but high-impact actions still require explicit confirmation or another appropriate security factor.

## Screen vision

Screen vision is a planned capability.

Nexus should eventually be able to understand relevant content on Rai's screen when explicitly enabled.

Screen vision must respect privacy modes and permission rules.

Sensitive screen regions should eventually be capable of being excluded or masked where practical.

Screen access must never silently become an unrestricted surveillance mechanism.

## PC control

PC control is a planned capability.

It should eventually allow Nexus to perform useful computer actions through controlled tools.

It must not provide an unrestricted arbitrary-command interface to the language model.

Actions that can modify files, accounts, applications or other consequential state should pass through the permission system.

Destructive or irreversible actions require explicit approval.

## Communications

Communications are a planned capability.

Nexus may eventually draft emails, WhatsApp messages and other communications.

The default behavior should be:

**AI drafts → Rai reviews → Rai sends**

Nexus should not impersonate Rai or silently send consequential communications.

Any future external communication system must clearly identify itself as an AI acting for Rai when interacting with other people.

## Models

Models are replaceable.

Current local model:

* Ollama
* Qwen 3 8B

Free cloud models may also be used when useful.

The model layer must remain replaceable so Nexus is not permanently tied to one provider.

The current laptop's RTX 3050 has 4GB VRAM, so local 8B models may be slow and larger local models may be impractical without future hardware upgrades.

## Hardware

HP Victus 15 FA0033DX:

* Intel i5-12450H
* 16GB RAM
* RTX 3050 with 4GB VRAM
* approximately 142GB SSD
* approximately 82GB free at last check
* Windows edition reported as Windows 11 IoT Enterprise LTSC (unconfirmed)

RAM and SSD upgrades are planned for later.

## Folder structure

Current project root:

`D:\Nexus`

Current important structure:

```text
D:\Nexus
├── Backups
├── Inbox
│   └── Register Photos
├── Semester1
│   ├── Basic Electronics
│   ├── Basic Electronics - Lab
│   ├── Financial Account
│   ├── Functional English
│   ├── Ideology and Constitution of Pakistan
│   ├── Introduction to Computing
│   ├── Introduction to Computing - Lab
│   └── Logic Thinking
├── modules
│   ├── communications
│   ├── pc_control
│   └── screen_vision
├── venv
├── Nexus_Brief.md
├── Nexus_Brief v2.2.md
├── Nexus_Brief v2.3.md
├── nexus_config.json
├── nexus_core.py
├── nexus_daemon.py
└── process_notes.py
```

Important note:

`nexus_daemon.py` is intentionally not implemented yet. Do not create it unless the architecture reaches the point where a background daemon is actually required.

Course folders contain the Semester 1 material.

Original course/register material should remain preserved as raw source material.

Register PDFs are named:

`Course_YYYY-MM-DD_ClassN.pdf`

Example:

`ICT_2026-09-30_Class2.pdf`

Add `Semester2` and later semester folders only when those semesters actually start.

## Current configuration

The main configuration file is:

`D:\Nexus\nexus_config.json`

It currently controls Nexus settings and feature states.

Configuration should remain user-editable through the GUI where practical.

Rai should not have to edit Python source code just to enable or disable a normal Nexus feature.

## Current Nexus components

### Nexus Core

Current version: 1.1.1

Current role:

* load configuration
* save configuration
* provide the graphical interface
* display system state
* expose feature controls
* launch supported modules
* perform basic system checks

The current GUI is an early foundation, not the final Nexus interface.

### Process Notes

Current version: 1.1.1

Purpose:

Process register photos/PDFs through Gemini and create course notes.

Current behavior includes:

* supports PNG, JPG, JPEG and PDF input
* routes register photos based on filename
* uses the Gemini API through the configured environment variable
* creates Markdown notes
* moves original files only after successful processing
* skips existing targets
* processes files individually
* does not support `.gdoc`

The `.gdoc` shortcut previously found in the Register Photos folder was removed intentionally. Do not add `.gdoc` support.

### Launcher

Current launcher:

`D:\Nexus\start_nexus.bat`

It should use the project folder dynamically rather than relying on a hardcoded installation path.

## Current project status

Completed:

* Nexus project folder structure created and verified
* Google Drive synchronization verified
* Semester 1 material archived in course raw folders
* Register notes photographed with iPhone and converted to PDF
* Register PDFs renamed and filed
* Handwriting OCR tested; accuracy is roughly 50-60%
* Ollama installed
* Qwen 3 8B working locally
* Nexus Core configuration system created
* Nexus Core GUI created
* Feature toggles are now controlled from the GUI/configuration rather than by editing Python source
* Process Notes implemented and tested
* Dynamic project-root handling added
* Basic logging added
* Launcher tested
* Baseline backup created at:
  `D:\Nexus\Backups\Nexus_Baseline_2026-10-04`
* Gemini architecture review completed
* Feature Registry identified as the next architectural foundation

Known unresolved/parked items:

* Docker Desktop failed to install with "This app can't run on your PC"
* WSL appears to be installed
* AnythingLLM has not been installed yet
* Docker and Open WebUI remain parked
* Advanced voice, screen vision and PC control are not implemented
* Final JARVIS-style UI is not implemented
* Background daemon is not implemented

## AI team and roles

### Claude

Lead builder and strategic reviewer.

Responsibilities:

* step-by-step implementation
* architecture decisions
* challenging weak ideas
* protecting the project from unnecessary complexity
* reviewing implementation decisions
* keeping the project aligned with this brief

### Copilot

Architect.

Responsibilities:

* system design
* structure
* planning
* architectural alternatives

### Gemini

Researcher and second technical opinion.

Responsibilities:

* comparing free tools
* checking current technical information
* researching APIs/models/tools
* identifying risks
* providing independent architectural review

Rai makes the final decision.

Agreement between AIs is not proof. Test decisions on the real laptop.

## Current step

**Build the Nexus Feature Registry foundation.**

The immediate goal is to introduce a clean registry for Nexus capabilities while preserving the working GUI, configuration system and Process Notes functionality.

The first implementation should:

* remain simple
* use no unnecessary external dependencies
* keep the current GUI working
* make feature definitions centralized
* distinguish implemented features from planned/unavailable features
* keep feature enable/disable state in configuration
* avoid implementing voice, vision, PC control or communications prematurely
* avoid introducing a complicated event bus prematurely
* avoid rewriting working components unnecessarily

After the Feature Registry is stable, the next architectural foundations will be introduced one at a time, especially the centralized Permission Gate and Privacy Mode system.

## Future capability direction

Potential future capabilities include:

* search across all courses
* course-specific search
* quizzes and flashcards
* midterm/final preparation
* handwritten-notes pipeline
* OCR plus short typed captions
* teacher-tip `HINT:` tags
* Word, Excel and PowerPoint creation
* email and WhatsApp drafting
* iPhone control/interface
* voice interaction
* speaker recognition
* screen understanding
* carefully limited PC control
* memory and long-term context
* proactive assistance
* controlled browser/web tools
* coding assistance
* project assistance
* career assistance
* creative workflows
* advanced graphical interface

These are directions, not claims that the features already exist.

## Good ideas

### Reverse tutor

Rai explains a concept to Nexus, and Nexus identifies gaps, mistakes and missing reasoning.

### Syllabus to deadlines

Extract dates from course outlines into a checklist, while always verifying dates against the original outline.

### Screenshot trick

Use `Win+Shift+S` to capture an error and paste it into an AI for explanation.

Free-tier cloud AI may process pasted content, so private information must not be pasted.

## Parked or dropped

* AI phone calls and reservations
* Unofficial WhatsApp automation
* Automatic sending of consequential communications
* Hand-gesture control
* Home automation
* Heavy animated slides
* Custom JARVIS-style interface before the foundation is stable
* Coding autocomplete as a first priority
* Docker/Open WebUI until the current environment issue is resolved
* Complicated event-bus architecture before it is actually needed
* Arbitrary LLM shell/terminal access

Previously discussed but not currently decided:

* Open WebUI
* Open Interpreter
* Mark-LV
* Coucou
* AutoGPT
* Claude Code

## Important design principles

**Files first.**

Knowledge should remain portable and readable without Nexus.

**Modules over monoliths.**

Nexus Core should orchestrate capabilities rather than contain every implementation.

**GUI over CLI.**

Technical complexity should increasingly be hidden behind the Nexus interface.

**Permission before action.**

The more consequential the action, the stronger the approval requirement.

**Privacy is a system policy.**

Privacy modes must eventually affect real capabilities, not just appearance.

**Voice is identity, not perfect authentication.**

Speaker recognition is useful for personalization but insufficient by itself for high-impact authorization.

**Verify actions.**

Nexus should eventually check whether a requested action actually succeeded rather than assuming success.

**Preserve user control.**

Rai remains the final authority over consequential actions and project decisions.

## Rule for any future agent that talks to people

It must say clearly that it is an AI acting for Rai.

```

**Do not modify `v2.2`.** Keep it as the previous snapshot.

After you create `v2.3`, **don't change `nexus_core.py` yet**. Tell me when the file is saved, and we'll do exactly one next step.
```
