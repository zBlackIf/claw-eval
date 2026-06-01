/**
 * API Client - handles HTTP requests to LLM providers.
 *
 * Known issue: Users report "The socket connection was closed unexpectedly"
 * when using streaming mode with the Volcengine provider.
 */
const http = require('http');
const { URL } = require('url');

class ApiClient {
    constructor(config) {
        this.config = config;
        this.provider = config.providers[config.activeProvider];
        this.baseUrl = this.provider.baseUrl;
        this.apiKey = this.provider.apiKey;
        this.timeout = this.provider.timeout || 30000;

        this.agent = new http.Agent({
            keepAlive: config.connection?.keepAlive ?? true,
            keepAliveMsecs: config.connection?.keepAliveTimeout ?? 60000,
            maxSockets: 5,
        });
    }

    async chat(params) {
        const url = new URL('/chat/completions', this.baseUrl);
        const payload = JSON.stringify({
            model: params.model,
            messages: params.messages,
            stream: params.stream || false,
        });

        const options = this._buildRequestOptions(url, payload);

        return new Promise((resolve, reject) => {
            const req = http.request(options, (res) => {
                if (params.stream) {
                    resolve(res);
                } else {
                    let data = '';
                    res.on('data', chunk => data += chunk);
                    res.on('end', () => {
                        try {
                            resolve(JSON.parse(data));
                        } catch (e) {
                            reject(new Error(`Failed to parse response: ${e.message}`));
                        }
                    });
                }
            });

            req.on('error', (err) => {
                reject(new Error(
                    `The socket connection was closed unexpectedly. ` +
                    `For more information, pass \`verbose: true\` in the second argument to fetch()`
                ));
            });

            req.setTimeout(this.timeout, () => {
                req.destroy();
                reject(new Error('Request timed out'));
            });

            req.write(payload);
            req.end();
        });
    }

    _buildRequestOptions(url, payload) {
        return {
            hostname: url.hostname,
            port: url.port || (url.protocol === 'https:' ? 443 : 80),
            path: url.pathname,
            method: 'POST',
            agent: this.agent,
            headers: {
                'Content-Type': 'application/json',
                'Content-Length': Buffer.byteLength(payload),
                'Authorization': `Bearer ${this.apiKey}`,
            },
        };
    }

    async chatWithRetry(params) {
        const { maxRetries, initialDelay, backoffMultiplier } = this.config.retryConfig || {};
        let lastError;
        let delay = initialDelay || 1000;

        for (let attempt = 0; attempt <= (maxRetries || 3); attempt++) {
            try {
                return await this.chat(params);
            } catch (error) {
                lastError = error;
                if (attempt < (maxRetries || 3)) {
                    await new Promise(r => setTimeout(r, delay));
                    delay *= (backoffMultiplier || 2);
                }
            }
        }
        throw lastError;
    }
}

module.exports = { ApiClient };
