/**
 * Configuration loader - reads provider config and merges with environment.
 */
const fs = require('fs');
const path = require('path');

function loadConfig() {
    const configPath = path.join(__dirname, '..', 'config', 'providers.json');
    if (!fs.existsSync(configPath)) {
        throw new Error(`Config file not found: ${configPath}`);
    }
    const raw = fs.readFileSync(configPath, 'utf-8');
    return JSON.parse(raw);
}

module.exports = { loadConfig };
