/**
 * Stream Handler - processes Server-Sent Events (SSE) from streaming API responses.
 */
class StreamHandler {
    constructor() {
        this.buffer = '';
    }

    async processStream(response) {
        return new Promise((resolve, reject) => {
            let fullContent = '';

            response.on('data', (chunk) => {
                this.buffer += chunk.toString();
                const lines = this.buffer.split('\n');
                this.buffer = lines.pop() || '';

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const data = line.slice(6).trim();
                        if (data === '[DONE]') {
                            resolve(fullContent);
                            return;
                        }
                        try {
                            const parsed = JSON.parse(data);
                            const delta = parsed.choices?.[0]?.delta?.content;
                            if (delta) {
                                process.stdout.write(delta);
                                fullContent += delta;
                            }
                        } catch (e) {
                            // Skip malformed SSE lines
                        }
                    }
                }
            });

            response.on('end', () => resolve(fullContent));
            response.on('error', (err) => reject(err));
        });
    }
}

module.exports = { StreamHandler };
