# Integrate with Hermes Agent

Note

This agent is provided entirely by a third party and is listed for developers' reference only. We cannot guarantee its effectiveness or security, and we assume no responsibility for it.

Hermes is a self-improving AI agent built by Nous Research. It includes a built-in learning loop: it creates skills from experience, improves them during use, persists knowledge, and builds an evolving model of your preferences across sessions.

#### 1\. Install Hermes[​](#1-install-hermes "Direct link to 1. Install Hermes")

##### Quick Install[​](#quick-install "Direct link to Quick Install")

Get Hermes Agent up and running in under two minutes with the one-line installer.

###### Linux / macOS / WSL2[​](#linux--macos--wsl2 "Direct link to Linux / macOS / WSL2")

```
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
```

The only prerequisite is Git. The installer automatically handles everything else.

For more installation instructions, please refer to the [Hermes installation page](https://hermes-agent.nousresearch.com/docs/getting-started/installation).

#### 2\. Run and Configure[​](#2-run-and-configure "Direct link to 2. Run and Configure")

Reload your shell and start Hermes configuration:

-   Execute the `hermes setup` command
-   Choose the Quick Setup option
-   When prompted for the model provider, select **DeepSeek**
-   Enter your [DeepSeek API Key](https://platform.deepseek.com/api_keys)
-   Enter the Base URL as `https://api.deepseek.com`
-   Select the `deepseek-v4-pro` model
-   Continue with the remaining options