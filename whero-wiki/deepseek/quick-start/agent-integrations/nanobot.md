# Integrating nanobot

Note

This agent is provided entirely by a third party and is listed for developers' reference only. We cannot guarantee its effectiveness or security, and we assume no responsibility for it.

nanobot is a lightweight AI agent that supports integration with popular chat tools.

#### 1\. Install nanobot[​](#1-install-nanobot "Direct link to 1. Install nanobot")

-   Install [uv](https://github.com/astral-sh/uv)
-   Run the following command to install nanobot:

```
uv tool install nanobot-ai
```

-   Note: On Windows, add the `.local/bin` directory under your user home directory to the environment variables:

```
$env:PATH = "$env:USERPROFILE\.local\bin;$env:PATH"
```

-   Or update the terminal via `uv`:

```
uv tool update-shell
```

-   After installation, run the following command. If a version number is displayed, the installation was successful:

```
nanobot --version
```

#### 2\. Configure nanobot[​](#2-configure-nanobot "Direct link to 2. Configure nanobot")

Run the following command to initialize the nanobot configuration file:

```
nanobot onboard
```

The configuration file path varies by operating system:

-   **Windows**: `$env:USERPROFILE\.nanobot\config.json`
-   **Linux / macOS**: `~/.nanobot/config.json`

Edit the `config.json` file and modify the following configuration items:

```
{    "agents": {        "defaults": {            "model": "deepseek-v4-pro",            "provider": "deepseek",        }    },    "providers": {        "deepseek": {            "apiKey": "<your DeepSeek API Key>",            "apiBase": "https://api.deepseek.com/v1",        },    },}
```

#### 3\. Get Started[​](#3-get-started "Direct link to 3. Get Started")

Run in the terminal:

```
nanobot agent
```