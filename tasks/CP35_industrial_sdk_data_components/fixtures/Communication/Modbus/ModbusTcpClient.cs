using System;
using System.Net.Sockets;
using System.Threading;
using System.Threading.Tasks;

namespace MinqiaIndustrialComponentLibrary.Communication.Modbus
{
    /// <summary>
    /// Modbus TCP 客户端，提供寄存器读写功能。
    /// </summary>
    public class ModbusTcpClient : IDisposable
    {
        private TcpClient _client;
        private NetworkStream _stream;
        private readonly SemaphoreSlim _semaphore = new SemaphoreSlim(1, 1);
        private bool _disposed;

        public string Host { get; }
        public int Port { get; }
        public int Timeout { get; set; } = 3000;
        public bool IsConnected => _client?.Connected ?? false;

        public ModbusTcpClient(string host, int port = 502)
        {
            Host = host ?? throw new ArgumentNullException(nameof(host));
            Port = port;
        }

        public async Task ConnectAsync(CancellationToken cancellationToken = default)
        {
            await _semaphore.WaitAsync(cancellationToken);
            try
            {
                _client = new TcpClient();
                await _client.ConnectAsync(Host, Port);
                _stream = _client.GetStream();
                _stream.ReadTimeout = Timeout;
                _stream.WriteTimeout = Timeout;
            }
            finally
            {
                _semaphore.Release();
            }
        }

        public async Task<ushort[]> ReadHoldingRegistersAsync(
            byte unitId, ushort startAddress, ushort quantity,
            CancellationToken cancellationToken = default)
        {
            await _semaphore.WaitAsync(cancellationToken);
            try
            {
                var request = BuildReadRequest(unitId, 0x03, startAddress, quantity);
                await _stream.WriteAsync(request, 0, request.Length, cancellationToken);

                var response = new byte[256];
                var bytesRead = await _stream.ReadAsync(response, 0, response.Length, cancellationToken);

                return ParseRegisters(response, bytesRead, quantity);
            }
            finally
            {
                _semaphore.Release();
            }
        }

        private byte[] BuildReadRequest(byte unitId, byte functionCode, ushort startAddress, ushort quantity)
        {
            // MBAP Header (7 bytes) + PDU (5 bytes)
            var request = new byte[12];
            // Transaction ID (2 bytes) - auto increment
            request[0] = 0; request[1] = 1;
            // Protocol ID (2 bytes) - always 0
            request[2] = 0; request[3] = 0;
            // Length (2 bytes)
            request[4] = 0; request[5] = 6;
            // Unit ID
            request[6] = unitId;
            // Function code
            request[7] = functionCode;
            // Start address
            request[8] = (byte)(startAddress >> 8);
            request[9] = (byte)(startAddress & 0xFF);
            // Quantity
            request[10] = (byte)(quantity >> 8);
            request[11] = (byte)(quantity & 0xFF);
            return request;
        }

        private ushort[] ParseRegisters(byte[] response, int bytesRead, ushort quantity)
        {
            var registers = new ushort[quantity];
            int dataStart = 9; // MBAP(7) + FC(1) + ByteCount(1)
            for (int i = 0; i < quantity && (dataStart + i * 2 + 1) < bytesRead; i++)
            {
                registers[i] = (ushort)((response[dataStart + i * 2] << 8) | response[dataStart + i * 2 + 1]);
            }
            return registers;
        }

        public void Dispose()
        {
            if (!_disposed)
            {
                _stream?.Dispose();
                _client?.Dispose();
                _semaphore?.Dispose();
                _disposed = true;
            }
        }
    }
}
