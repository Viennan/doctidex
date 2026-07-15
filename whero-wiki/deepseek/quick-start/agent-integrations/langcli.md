# Integrate with Langcli

Note

This agent is provided entirely by a third party and is listed for developers' reference only. We cannot guarantee its effectiveness or security, and we assume no responsibility for it.

[Langcli](https://langcli.com) is an AI coding assistant that supports CLI and Zed ACP Agent.

#### 1\. Installation[​](#1-installation "Direct link to 1. Installation")

##### Quick Install (Recommended)[​](#quick-install-recommended "Direct link to Quick Install (Recommended)")

For macOS, Linux and WSL users, run the following command to install Langcli:

```
bash -c "$(curl -fsSL https://assets.langcli.com/installation/install-langcli.sh)"
```

For Windows users, run the following command instead (Run as Administrator CMD):

```
cmd /c "curl -fsSL -o %TEMP%\install-langcli.bat https://assets.langcli.com/installation/install-langcli.bat && %TEMP%\install-langcli.bat"
```

> **Note**: It's recommended to restart your terminal after installation to ensure environment variables take effect.

##### Manual Installation[​](#manual-installation "Direct link to Manual Installation")

Make sure you have Node.js 20 or later installed. Otherwise download it from [nodejs.org](https://nodejs.org/en/download) and install first.

```
npm i -g langcli-com
```

#### 2\. Quick Start[​](#2-quick-start "Direct link to 2. Quick Start")

##### API Key Preparation[​](#api-key-preparation "Direct link to API Key Preparation")

Go to [LangRouter](https://langrouter.ai/), register an account, save your API key. Note: Free trial available.

#### Running[​](#running "Direct link to Running")

```
# Start Langcli (interactive)langcli# Then, in the session:hi
```