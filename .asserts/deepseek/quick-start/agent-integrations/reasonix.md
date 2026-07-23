# Integrate with Reasonix

Note

This agent is provided entirely by a third party and is listed for developers' reference only. We cannot guarantee its effectiveness or security, and we assume no responsibility for it.

Reasonix is a DeepSeek-native coding agent that runs in the terminal. It's designed around DeepSeek's API directly — cache-first loop, flash-first cost control, automatic tool-call repair — and talks to `api.deepseek.com` without a translation shim.

#### 1\. Install Node.js[​](#1-install-nodejs "Direct link to 1. Install Node.js")

-   Install [Node.js](https://nodejs.org/en/download/) 20.10+.
-   Windows users need to install [Git for Windows](https://git-scm.com/download/win).

#### 2\. Get a DeepSeek API Key[​](#2-get-a-deepseek-api-key "Direct link to 2. Get a DeepSeek API Key")

Get your API Key from the [DeepSeek Platform](https://platform.deepseek.com/api_keys). The first run of Reasonix prompts for it via a built-in wizard and persists it to `~/.reasonix/config.json` — no environment variable needed.

#### 3\. Enter the project directory and run `npx reasonix code` to get started.[​](#3-enter-the-project-directory-and-run-npx-reasonix-code-to-get-started "Direct link to 3-enter-the-project-directory-and-run-npx-reasonix-code-to-get-started")

```
cd /path/to/my-projectnpx reasonix code
```

No global install required. By default Reasonix uses **DeepSeek-V4-Flash** for cost-efficient iteration. Type `/pro` inside the TUI to arm **DeepSeek-V4-Pro** for the next turn, or `/preset max` to use Pro for the whole session. Run `/help` for the full slash-command reference.

![](https://raw.githubusercontent.com/esengine/reasonix/main/docs/logo.svg)