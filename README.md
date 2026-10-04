---
title: Plant Identification Tool
colorFrom: green
colorTo: gray
sdk: gradio
app_file: plant_space_app.py
pinned: false
tags:
  - track:backyard
  - sponsor:openbmb
  - sponsor:openai
  - achievement:welltuned
  - achievement:llama
  - achievement:sharing

---

📺 **Demo video:** <a href="https://huggingface.co/spaces/build-small-hackathon/plant_identification_tool/resolve/main/screencast.webm">HF Space Recording</a> ·  

📺 **Social Demo:**
https://twitter.com/zX14_7/status/2066669462179242412 

# Plant Identification Tool

A Gradio reference app from the OpenBMB Local AI Workbench template: identify plants locally,
correct mistakes, and export field notes as training data. Deployed on Hugging Face Spaces with
zero-GPU support via `@spaces.GPU` decorators on the vision callbacks.

## What This Is

The project turns the PRD in `HF_PRD_v1.md` into a staged implementation:

1. A working Gradio app shell.
2. Config-driven OpenBMB model registry.
3. Local-first inference path through real backends: Transformers, Ollama, llama.cpp,
   LM Studio/OpenAI-compatible, SGLang, and vLLM.
4. Field notes for collecting corrections.
5. Extension points for training, GGUF export, Trackio traces, MCP tools, and agent workflows.

## Hackathon Fit

- **Track:** Backyard AI or Thousand Token Wood, depending on the final user story.
- **Canvas:** Gradio app, deployable to Hugging Face Spaces.
- **Small model rule:** target models stay at or below 32B parameters.
- **Bonus quests:** local-first, field notes/report, possible llama.cpp and trace sharing.

## Quick Start

Python is not currently available on PATH in this workspace shell. Install Python first, then:

```powershell
.\scripts\verify_structure.ps1
& "$env:LOCALAPPDATA\Microsoft\WindowsApps\python3.11.exe" -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
.\scripts\run_tests.ps1
python app.py
```

## Browser E2E Screenshots

After installing Node.js:

```powershell
npm install
npm run e2e:install
npm run e2e
```

The Playwright user-story tests run separate Workbench and Plant flows and save documentation
screenshots under `assets/e2e/workbench/` and `assets/e2e/plant/`. The Workbench screenshot now runs
local GGUF chat through `llama-cpp-python`; the Plant screenshot can run OpenBMB MiniCPM-V on
`assets/plant_sample.jpg` with `RUN_REAL_MODEL_E2E=1`.
only when `RUN_REAL_MODEL_E2E=1` is set; otherwise the browser tests verify real-backend setup
surfaces without using mock responses. To record or edit the browser flow manually, run
`npm run e2e:record`.

Generated screenshot sets:

- [Workbench home](assets/e2e/workbench/01-workbench-home.png)
- [Workbench backend status](assets/e2e/workbench/05-backend-status.png)
- [Plant tool home](assets/e2e/plant/01-plant-home.png)
- [Plant corrections export](assets/e2e/plant/03-corrections-export.png)

## Template And Reference Apps

This repo is also a template for focused local-first Gradio apps. The first reference app is
Plant Discovery under `plant/`.

```powershell
.venv\Scripts\python.exe -m plant.app --no-model --port 7861
```

Use the real OpenBMB VLM path after installing optional plant dependencies:

```powershell
.venv\Scripts\python.exe -m plant.app --model-mode openbmb --port 7861
```

The detailed build guide is [docs/TEMPLATE_HOWTO.md](docs/TEMPLATE_HOWTO.md), and the Plant
Discovery checklist is [docs/PLANT_DISCOVERY_APP_PLAN.md](docs/PLANT_DISCOVERY_APP_PLAN.md).
Model and adapter training steps are in
[docs/PLANT_MODEL_AND_TRAINING_HOWTO.md](docs/PLANT_MODEL_AND_TRAINING_HOWTO.md).

If `python` is not recognized, install Python 3.11+ from python.org or the Windows Store,
then reopen the terminal so PATH is refreshed.

Open the local URL shown by Gradio, usually `http://127.0.0.1:7860`.

## Project Structure

```text
.
|-- app.py
|-- AGENTS.md
|-- README.md
|-- requirements.txt
|-- config/
|   |-- models.yaml
|   `-- training.yaml
|-- core/
|   |-- events.py
|   `-- registry.py
|-- datasets/
|   `-- field_notes.py
|-- models/
|   |-- placeholder_service.py
|   `-- model_catalog.py
|-- ui/
|   |-- chat_tab.py
|   |-- dataset_tab.py
|   |-- export_tab.py
|   |-- notes_tab.py
|   |-- traces_tab.py
|   |-- agent_tab.py
|   |-- status_tab.py
|   |-- train_tab.py
|   `-- vision_tab.py
|-- data/
|   `-- .gitkeep
|-- exports/
|   `-- .gitkeep
|-- HF_PRD_v1.md
`-- HF_PRD_ext.md
```

## Project Docs

The working docs live in [docs/README.md](docs/README.md).

- [Task checklist](docs/TASKS.md)
- [Implementation status](docs/IMPLEMENTATION_STATUS.md)
- [PRD implementation matrix](docs/PRD_IMPLEMENTATION_MATRIX.md)
- [Acceptance criteria](docs/ACCEPTANCE_CRITERIA.md)
- [Roadmap](docs/ROADMAP.md)
- [Template how-to](docs/TEMPLATE_HOWTO.md)
- [Plant Discovery plan](docs/PLANT_DISCOVERY_APP_PLAN.md)
- [Usage guide](docs/USAGE.md)
- [Architecture guide](docs/ARCHITECTURE.md)
- [Extension guide](docs/EXTENDING.md)
- [Hackathon submission package](docs/HACKATHON_SUBMISSION.md)
- [Test and quality policy](docs/ACCEPTANCE_CRITERIA.md)

## Current Truth

The full PRD is not implemented yet. The current app is a tested, quality-gated scaffold moving
from placeholder-first local verification to real-backend Workbench deployment. GitHub push is
complete at `https://github.com/Ckal/codex`. LM Studio/OpenAI-compatible text inference has been
verified previously; OpenBMB Transformers, Ollama OpenBMB, llama.cpp, MiniCPM-V, Space builds,
training execution, served MCP, and most extension PRD items still need proof before being claimed
done.

## Model Plan

Initial candidates from the PRD:

| Config ID | Model | Purpose |
| --- | --- | --- |
| `minicpm5_1b` | `openbmb/MiniCPM5-1B` | text chat, LoRA, local-first baseline |
| `minicpm_v46` | `openbmb/MiniCPM-V-4.6` | image/video understanding |
| `minicpm_o45` | `openbmb/MiniCPM-o-4.5` | omnimodal stretch goal |

The app does not download large model files automatically. In deployed Space mode, placeholder
backend choices are hidden and model calls require real backend configuration. llama.cpp,
llama-cpp-python, Ollama, LM Studio/OpenAI-compatible, SGLang, Nemotron Nano 9B v2, and Transformers text can be selected as
backends, but the backend tool/package/server must be installed and populated with the selected
model explicitly by the user.

## Deployment Target

For Hugging Face Spaces, keep these files at repo root:

- `app.py`
- `requirements.txt`
- `README.md`
- `config/`
- `core/`
- `models/`
- `ui/`

Workbench Space target:

```text
https://huggingface.co/spaces/build-small-hackathon/workbench
```

## Spaces

- Workbench Space: https://huggingface.co/spaces/build-small-hackathon/workbench
- Plant Identification Tool Space: https://huggingface.co/spaces/build-small-hackathon/plant_identification_tool

Both Spaces have been pushed. At the latest local poll they were still in Hugging Face `BUILDING`
state on `zero-a10g`, so final build/run smoke verification is still open.

Plant Identification Tool Space target:

```text
https://huggingface.co/spaces/build-small-hackathon/plant_identification_tool
```

Use a freshly generated token through `hf auth login`; do not paste tokens into files or commit
them.

Later deployment commands:

```powershell
hf auth login
git remote add space-workbench https://huggingface.co/spaces/build-small-hackathon/workbench
git push space-workbench main
git remote add space-plant https://huggingface.co/spaces/build-small-hackathon/plant_identification_tool
git push space-plant main
```

## Next Implementation Steps

1. Decide the exact hackathon story and user.
2. Add screenshot/demo media and Space submission URLs.
3. Push and verify the two Hugging Face Spaces, then finish llama.cpp MiniCPM-V mmproj vision verification.
4. Add field-note export to JSONL/HF Dataset.
5. Polish README with screenshots, demo video script, and submission links.
