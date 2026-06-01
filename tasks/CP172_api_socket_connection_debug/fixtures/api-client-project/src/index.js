/**
 * LLM Gateway Client - Main entry point
 * Connects to configured LLM provider and handles streaming responses.
 */
const { ApiClient } = require('./api_client');
const { loadConfig } = require('./config_loader');
const { StreamHandler } = require('./stream_handler');

async function main() {
    const config = loadConfig();
    const client = new ApiClient(config);
    const streamHandler = new StreamHandler();

    try {
        const response = await client.chat({
            model: config.providers[config.activeProvider].defaultModel,
            messages: [{ role: 'user', content: 'Hello, world!' }],
            stream: config.providers[config.activeProvider].streaming,
        });

        if (config.providers[config.activeProvider].streaming) {
            await streamHandler.processStream(response);
        } else {
            console.log(response.choices[0].message.content);
        }
    } catch (error) {
        console.error(`API Error: ${error.message}`);
        process.exit(1);
    }
}

main();
