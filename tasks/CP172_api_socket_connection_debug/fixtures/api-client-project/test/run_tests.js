/**
 * Integration tests for LLM Gateway Client.
 * Tests validate that the client can connect and communicate with the API.
 */
const { ApiClient } = require('../src/api_client');
const { loadConfig } = require('../src/config_loader');
const http = require('http');
const https = require('https');

// Mock server to validate client behavior
function createMockServer(port, useHttps = false) {
    const handler = (req, res) => {
        // Validate headers
        const contentType = req.headers['content-type'];
        const auth = req.headers['authorization'];

        if (!auth || !auth.startsWith('Bearer ')) {
            res.writeHead(401);
            res.end(JSON.stringify({ error: 'Unauthorized' }));
            return;
        }

        let body = '';
        req.on('data', chunk => body += chunk);
        req.on('end', () => {
            const parsed = JSON.parse(body);

            if (parsed.stream) {
                // Check for Accept header for streaming
                const accept = req.headers['accept'];
                if (!accept || !accept.includes('text/event-stream')) {
                    // Server still responds but logs warning
                    console.warn('[mock-server] Missing Accept: text/event-stream header');
                }

                res.writeHead(200, {
                    'Content-Type': 'text/event-stream',
                    'Cache-Control': 'no-cache',
                    'Connection': 'keep-alive',
                });
                res.write('data: {"choices":[{"delta":{"content":"Hello"}}]}\n\n');
                res.write('data: {"choices":[{"delta":{"content":" World"}}]}\n\n');
                res.write('data: [DONE]\n\n');
                res.end();
            } else {
                res.writeHead(200, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({
                    choices: [{
                        message: { role: 'assistant', content: 'Test response' }
                    }]
                }));
            }
        });
    };

    const server = http.createServer(handler);
    return server;
}

async function runTests() {
    const results = { passed: 0, failed: 0, tests: [] };

    // Test 1: Config loading
    try {
        const config = loadConfig();
        if (config.activeProvider === 'volcengine' && config.providers.volcengine) {
            results.tests.push({ name: 'config_loading', status: 'pass' });
            results.passed++;
        } else {
            throw new Error('Config missing expected fields');
        }
    } catch (e) {
        results.tests.push({ name: 'config_loading', status: 'fail', error: e.message });
        results.failed++;
    }

    // Test 2: Client uses correct protocol module for HTTPS URLs
    try {
        const config = loadConfig();
        const client = new ApiClient(config);
        // Check if the agent is an https.Agent for https:// URLs
        const isHttpsAgent = client.agent instanceof https.Agent;
        if (isHttpsAgent) {
            results.tests.push({ name: 'https_agent_for_https_url', status: 'pass' });
            results.passed++;
        } else {
            results.tests.push({
                name: 'https_agent_for_https_url',
                status: 'fail',
                error: 'Client uses http.Agent for https:// URL - causes socket errors'
            });
            results.failed++;
        }
    } catch (e) {
        results.tests.push({ name: 'https_agent_for_https_url', status: 'fail', error: e.message });
        results.failed++;
    }

    // Test 3: Request uses https module for https:// URLs
    try {
        const config = loadConfig();
        // Override baseUrl to local mock for testing
        config.providers.volcengine.baseUrl = 'http://127.0.0.1:19876';
        config.providers.volcengine.streaming = false;
        const client = new ApiClient(config);

        const server = createMockServer(19876);
        await new Promise(resolve => server.listen(19876, resolve));

        try {
            const response = await client.chat({
                model: 'doubao-pro-32k',
                messages: [{ role: 'user', content: 'test' }],
                stream: false,
            });

            if (response && response.choices && response.choices[0].message.content === 'Test response') {
                results.tests.push({ name: 'non_streaming_request', status: 'pass' });
                results.passed++;
            } else {
                results.tests.push({ name: 'non_streaming_request', status: 'fail', error: 'Unexpected response' });
                results.failed++;
            }
        } finally {
            server.close();
        }
    } catch (e) {
        results.tests.push({ name: 'non_streaming_request', status: 'fail', error: e.message });
        results.failed++;
    }

    // Test 4: Streaming request includes Accept header
    try {
        const config = loadConfig();
        config.providers.volcengine.baseUrl = 'http://127.0.0.1:19877';
        config.providers.volcengine.streaming = true;
        const client = new ApiClient(config);

        let receivedAcceptHeader = null;
        const server = http.createServer((req, res) => {
            receivedAcceptHeader = req.headers['accept'];
            res.writeHead(200, { 'Content-Type': 'text/event-stream' });
            res.write('data: {"choices":[{"delta":{"content":"Hi"}}]}\n\n');
            res.write('data: [DONE]\n\n');
            res.end();
        });
        await new Promise(resolve => server.listen(19877, resolve));

        try {
            await client.chat({
                model: 'doubao-pro-32k',
                messages: [{ role: 'user', content: 'test' }],
                stream: true,
            });

            // Wait a moment for the request to complete
            await new Promise(r => setTimeout(r, 100));

            if (receivedAcceptHeader && receivedAcceptHeader.includes('text/event-stream')) {
                results.tests.push({ name: 'streaming_accept_header', status: 'pass' });
                results.passed++;
            } else {
                results.tests.push({
                    name: 'streaming_accept_header',
                    status: 'fail',
                    error: `Accept header: ${receivedAcceptHeader || 'missing'}`
                });
                results.failed++;
            }
        } finally {
            server.close();
        }
    } catch (e) {
        results.tests.push({ name: 'streaming_accept_header', status: 'fail', error: e.message });
        results.failed++;
    }

    // Test 5: Streaming timeout is disabled during active stream
    try {
        const config = loadConfig();
        config.providers.volcengine.baseUrl = 'http://127.0.0.1:19878';
        config.providers.volcengine.streaming = true;
        config.providers.volcengine.timeout = 500; // Very short timeout
        const client = new ApiClient(config);

        const server = http.createServer((req, res) => {
            res.writeHead(200, { 'Content-Type': 'text/event-stream' });
            // Simulate slow streaming - send data after 800ms (longer than timeout)
            setTimeout(() => {
                res.write('data: {"choices":[{"delta":{"content":"delayed"}}]}\n\n');
                res.write('data: [DONE]\n\n');
                res.end();
            }, 800);
        });
        await new Promise(resolve => server.listen(19878, resolve));

        try {
            const response = await client.chat({
                model: 'doubao-pro-32k',
                messages: [{ role: 'user', content: 'test' }],
                stream: true,
            });

            // If we get the response stream without timeout, that's good
            await new Promise((resolve, reject) => {
                let data = '';
                response.on('data', chunk => data += chunk.toString());
                response.on('end', () => resolve(data));
                response.on('error', reject);
                // Give it enough time
                setTimeout(() => reject(new Error('Test timed out')), 2000);
            });

            results.tests.push({ name: 'streaming_timeout_handling', status: 'pass' });
            results.passed++;
        } catch (e) {
            if (e.message.includes('timed out') || e.message.includes('socket') || e.message.includes('destroyed')) {
                results.tests.push({
                    name: 'streaming_timeout_handling',
                    status: 'fail',
                    error: 'Request times out during active stream - timeout should be disabled/extended for streaming'
                });
            } else {
                results.tests.push({ name: 'streaming_timeout_handling', status: 'fail', error: e.message });
            }
            results.failed++;
        } finally {
            server.close();
        }
    } catch (e) {
        results.tests.push({ name: 'streaming_timeout_handling', status: 'fail', error: e.message });
        results.failed++;
    }

    console.log(JSON.stringify(results, null, 2));
    process.exit(results.failed > 0 ? 1 : 0);
}

runTests().catch(e => {
    console.error('Test runner error:', e);
    process.exit(1);
});
