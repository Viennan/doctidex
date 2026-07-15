# Integrate with Kilo Code

Note

This agent is provided entirely by a third party and is listed for developers' reference only. We cannot guarantee its effectiveness or security, and we assume no responsibility for it.

Kilo Code is an AI coding assistant available as a CLI and editor extension.

#### 1\. Install Kilo Code CLI[​](#1-install-kilo-code-cli "Direct link to 1. Install Kilo Code CLI")

-   Install [Node.js](https://nodejs.org/en/download/).
-   Run the following command in your terminal to install Kilo Code CLI:

```
npm install -g @kilocode/cli
```

-   After installation, run the following command. If the version number is displayed, the installation is successful:

```
kilo --version
```

#### 2\. Run Kilo Code[​](#2-run-kilo-code "Direct link to 2. Run Kilo Code")

Enter the project directory and run `kilo`:

```
cd /path/to/my-projectkilo
```

#### 3\. Connect the DeepSeek Provider[​](#3-connect-the-deepseek-provider "Direct link to 3. Connect the DeepSeek Provider")

-   Type `/connect` in the command bar to open the **Connect Provider** panel.
-   Search for `deepseek`, select **DeepSeek**, then enter your [DeepSeek API Key](https://platform.deepseek.com/api_keys).

#### 4\. Select a DeepSeek Model[​](#4-select-a-deepseek-model "Direct link to 4. Select a DeepSeek Model")

-   Type `/models` to open the model selector.
-   Select one of the available DeepSeek models:
    -   DeepSeek Chat
    -   DeepSeek Reasoner
    -   DeepSeek V4 Flash
    -   DeepSeek V4 Pro