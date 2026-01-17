<a id="top"></a>

# 🦥 AutoVisuals
### Automated Illustration & Prompt Generation Engine

<img src="docs/autovisuals_hex_icon_simple.svg" align="right" width="180" />

[![Static Badge](https://img.shields.io/badge/License-Sloths_Intel-darkgreen)]()
[![Static Badge](https://img.shields.io/badge/Build-Passing-%23a9f378)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)]()
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)]()
[![Status](https://img.shields.io/badge/Project-Active-brightgreen.svg)]()

[![Static Badge](https://img.shields.io/badge/Sloths%20Visuals-Powered-%23f378d0)]()
[![Platform](https://img.shields.io/badge/Platform-Linux%20%7C%20WSL%20%7C%20macOS-lightgrey.svg)]()

[![Static Badge](https://img.shields.io/badge/Chatbot-OpenAI%20%7C%20Anthropic%20%7C%20Gemini%20%7C%20Llama%20%7C%20DeepSeek-purple)]()


**AutoVisuals** designed by **Sloths Visuals (SlothsIntel)**, is a fully automated pipeline for generating randomised **Midjourney-ready prompts**, sending them to **Discord**, automatically **downloading and splitting MJ images**, and building a stylish **HTML gallery** with zoom navigation, for business design, internal datasets, Adobe Stock, and other illustration stocks.

---

# Contents
- [Features](#Features)
- [Installation](#Installation)
  - [From pip](#From-pip)
  - [From conda](#From-conda)
  - [From source(advanced)](#From-source-advanced)
- [Required Environment Variables](#RequiredEnvironment-Variables)
- [Optional Scaling Modules](#Optional-Scaling-Modules)
  - [Install Real-ESRGAN](#Install-Real-ESRGAN)
  - [Install SwinIR](#Install-SwinIR)
  - [Install Topaz](#Install-Topaz)
- [Usage](#Usage)
  - [Pipeline](#Pipeline)
  - [Subcommand](#Subcommand)
- [Free Providers Included](#Free-Providers-Included)
- [Theme List Format](#Theme-List-Format)
- [Future Modules](#Future-Modules)
- [Contribution](#Contribution)
- [About Sloths Visuals](#About-Sloths-Visuals)
- [License](#License)
- [Links](#Links)

---

# Features

## Prompt & Metadata Generator
- Generates output: **theme**, **title**, **description**, **45 keywords**, and **/imagine prompt**.
- Supports output formats: **txt**, **csv**, and **json**.
- Supports stock metadata formats: **Adobe Stock**, **Shutterstock**, and **Freepik**.

## Discord Automation
- Sends each prompt line to any Discord channel via **webhook**.
- Confirms each prompt in your private server with [one click]().
- Downloads MJ bot images via **Discord bot token**.
- Auto-splits 2×2 grids into 4 tiles.

## Scaling Processor (optional)

Coming soon

## HTML Gallery Builder
- Builds a techno-tidy responsive gallery:
  - Date → Category → Images  
- Zoom mode includes:
  - **Prev/Next navigation**.
  - **Back to Gallery**.

## Full Pipeline Command
Run `autovisuals pipeline` to get a pipeline of `generate` → `send` → `download` → `split` → `scale`(optional) → `gallery`.

## Status Summary
Run `autovisuals status` to show how many prompts/images exist per date/category.

<p align="right">
  <a href="#top" style="text-decoration:none;">
    ⬆️
  </a>
</p>

---

# Installation

## From pip

First,

```shell
conda create -n autovisuals python==3.11
conda activate autovisuals
cd <your_work_directory>
```

Coming soon

## From conda

Similarly,

```shell
conda create -n autovisuals python==3.11
conda activate autovisuals
cd <your_work_directory>
```

Coming soon

## From source (advanced)

```shell
conda create -n autovisuals python==3.11
conda activate autovisuals
```

Clone the repository.
```shell
git clone https://github.com/slothsintel/AutoVisuals
cd AutoVisuals
```

Install environment.

```shell
pip install -r requirements.txt
```

Add to PATH.
```shell
echo 'export PATH="$HOME/AutoVisuals/scripts:$PATH"' >> ~/.bashrc
source ~/.bashrc
```
Install scaling proccessor (optional):

[See details here](#Optional-Scaling-Module:)

<p align="right">
  <a href="#top" style="text-decoration:none;">
    ⬆️
  </a>
</p>

---

# Required Environment Variables

For prompt generation, where to get [openai api]():
```shell
export API_KEY="your LLM API key"
```

For Discord prompt sending, where to get [discord webhook]():
```shell
export WEBHOOK_URL="https://discord.com/api/webhooks/..."
```

For Discord image downloading, where to get [discord bot token]() and [mj channel id]():
```shell
export DISCORD_BOT_TOKEN="your-bot-token"
export MJ_CHANNEL_ID="123456789012345678"
```

---

<span id="Optional Scaling Module:"></span>

## Install Real-ESRGAN

Follow [this](https://github.com/slothsintel/Real-ESRGAN) or original [instruction](https://github.com/xinntao/Real-ESRGAN) to install Real-ESRGAN. Quick install:
```shell
cd AutoVisuals
git submodule add https://github.com/xinntao/Real-ESRGAN.git Real-ESRGAN
cd Real-ESRGAN
pip install basicsr
pip install facexlib
pip install gfpgan
pip install -r requirements.txt
python setup.py develop
```


## Install SwinIR

Coming soon

## Install Topaz

Coming soon



<p align="right">
  <a href="#top" style="text-decoration:none;">
    ⬆️
  </a>
</p>

---

# Usage

## Pipeline

Pipeline command `autovisuals pipeline` to `generate` → `send` → `download` → `scale`(optional) → `gallery`.

Option:

```
-h, --help        show this help message and exit.
-p, --provider    chatbot provider, choose openai by default, anthropic, gemini, llama, or deepseek.
-l, --list        list of visuals list, choose autovisuals/data/adobe_cat.csv by default or others.
-m, --mode        mode to generate prompts by themes, choose r(random) by default or m(manual).
-t, --title       title to generate prompts, choose r(weight random) by default or m(manual) input.
-d, --records     number of prompts for each run, 5 by default.
-r, --repeat      number of times to repeat each prompt for diversity, 2 by default.
-o, --out         prompt output directory, prompt/<date>/<theme> by default.
-w, --webhook     webhook URL, need to export it as environment variable.
--download-dir    images download directory, mj_downloads/<date>/<theme> by default.
--gallery-out     gallery file output directory, mj_gallery.html by default.
--idle-seconds    downloader idle timeout in seconds to proccess gallery, 120 by default.
-U, --upscale     optional upscaling step after download (y = RealESRGAN, default: n)..
--export-dir      export root for upscaled images (absolute path,
                  e.g. /mnt/c/Users/xilu/Downloads/autovisuals_export).
```

## Subcommand

Subcommand `autovisuals generate` to generate prompts + metadata.

Option:
```
-h, --help        show this help message and exit.
-p, --provider    chatbot provider, choose openai by default, anthropic, gemini, llama, or deepseek.
-l, --list        list of visuals list, choose autovisuals/data/adobe_cat.csv by default or others.
-m, --mode        mode to generate prompts by themes, choose r(random) by default or m(manual).
-t, --title       title to generate prompts, choose r(weight random) by default or m(manual) input.
-d, --records     number of prompts for each run, 5 by default.
-r, --repeat      number of times to repeat each prompt for diversity, 2 by default.
-o, --out         prompt output directory, prompt/<date>/<theme> by default.
```

Subcommand `autovisuals discord` to send prompts to Discord webhook.

Option:
```
-h, --help        show this help message and exit.
-o, --out         prompt output directory, prompt/<date>/<theme> by default.
--category        specific category slug to send, true by default.
--all-categories  send prompts for all categories for latest date, true by default.
```

Subcommand `autovisuals download` to download Midjourney images.

Option:
```
-h, --help        show this help message and exit.
-t, --token       discord bot token, need to export it as environment variable.
-c, --channel-id  discord channel id, need to export it as environment variable.
-o, --out OUT     images download directory, mj_downloads/<date>/<theme> by default.
--limit LIMIT     stop after N images, no limit by default.
--idle-seconds    downloader idle timeout in seconds to proccess gallery, 120 by default.
```

Subcommand `autovisuals gallery` to build HTML gallery.

Option:
```
-h, --help        show this help message and exit.
--download-dir    images download directory, mj_downloads/<date>/<theme> by default.
--prompt-dir      prompt output directory, prompt/<date>/<theme> by default.
--out OUT         gallery file output directory, mj_gallery.html by default.
```

Additional command `autovisuals status` to show a tidy summary of prompts + images per date/theme.

Example:
```
DATE         CATEGORY             PROMPTS   IMAGES
2025-11-21   business                  3        12
2025-11-21   nature                    3        12
---------------------------------------------------
TOTAL                                6        24
```

Additional command `autovisuals meta` to create metadata uploads to Adobe Stock/Shutterstock/Freepik.

<p align="right">
  <a href="#top" style="text-decoration:none;">
    ⬆️
  </a>
</p>

---

# Free Providers Included

AutoVisuals now includes two **completely free** API providers:

## Llama (Llama 4 Maverick)
- No API key required  
- High performance  
- Good for bulk generation  
- Endpoint: https://api.llama-api.com/chat/completions

## DeepSeek (DeepSeek V3)
- No API key required  
- Extremely fast  
- Stable JSON outputs  
- Endpoint: https://api.deepseek.com/free/chat/completions
<p align="right">
  <a href="#top" style="text-decoration:none;">
    ⬆️
  </a>
</p>

---

# Theme List Format
Each themes and its weights are in the same row, seperated by comma.
```
theme,weight
forest in fog,4
business teamwork,3
sunset over mountains,5
......
```

---

# Future Modules

- SwinIR installation  
- Topaz installation  
- pip installation
- conda installation       
- Windows installation  
- GUI (AutoVisuals Studio)  

---

# Contribution

Maintained by **Sloths Visuals** of [**Sloths Intel GitHub**](https://github.com/slothsintel), and [**Daddy Sloth Github**](https://github.com/drxilu).

---

# About Sloths Visuals

A creative visualisation brand under [**Sloths Intel**](https://slothsintel.com), specialising in data visulisation and automated illustration pipelines.

---

# License

© 2025–2026 **Sloths Intel**.

A trading name of **Sloths Intel Ltd**
Registered in England and Wales (Company No. 16907507).

MIT License.

---

# Links

* [AutoVisuals Website](https://autovisuals.slothsintel.com)
* [AutoVisuals GitHub](https://github.com/slothsintel/autovisuals)
* [Company homepage](https://slothsintel.com)

<p align="right">
  <a href="#top" style="text-decoration:none;">
    ⬆️
  </a>
</p>