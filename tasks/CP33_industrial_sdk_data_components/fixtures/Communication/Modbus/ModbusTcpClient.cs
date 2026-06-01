using System;
using System.Net.Sockets;
using System.Threading;
using System.Threading.Tasks;

namespace MinqiaIndustrialComponentLibrary.Communication.Modbus
{
    /// <summary>
    /// Modbus TCP client for industrial device communication.
    /// Supports read/write of holding registers and coils.
    /// </summary>
    public class ModbusTcpClient : IDisposable
    {
        private TcpClient? _client;
        private NetworkStream? _stream;
        private readonly string _host;
        private readonly int _port;
        private readonly SemaphoreSlim _lock = new(1, 1);
        private ushort _transactionId;

        public ModbusTcpClient(string host, int port = 502)
        {
            _host = host ?? throw new ArgumentNullException(nameof(host));
            _port = port;
        }

        public bool IsConnected => _client?.Connected ?? false;

        public async Task ConnectAsync(CancellationToken ct = default)
        {
            _client = new TcpClient();
            await _client.ConnectAsync(_host, _port, ct);
            _stream = _client.GetStream();
        }

        public async Task<ushort[]> ReadHoldingRegistersAsync(
            byte unitId, ushort startAddress, ushort quantity,
            CancellationToken ct = default)
        {
            await _lock.WaitAsync(ct);
            try
            {
                var request = BuildReadRequest(unitId, 0x03, startAddress, quantity);
                await _stream!.WriteAsync(request, ct);
                var response = new byte[256];
                var bytesRead = await _stream.ReadAsync(response, ct);
                return ParseRegisters(response, bytesRead);
            }
            finally
            {
                _lock.Release();
            }
        }

        private byte[] BuildReadRequest(byte unitId, byte functionCode,
            ushort startAddress, ushort quantity)
        {
            var txId = Interlocked.Increment(ref _transactionId);
            return new byte[]
            {
                (byte)(txId >> 8), (byte)txId,
                0x00, 0x00, 0x00, 0x06,
                unitId, functionCode,
                (byte)(startAddress >> 8), (byte)startAddress,
                (byte)(quantity >> 8), (byte)quantity
            };
        }

        private static ushort[] ParseRegisters(byte[] response, int length)
        {
            var byteCount = response[8];
            var registers = new ushort[byteCount / 2];
            for (int i = 0; i < registers.Length; i++)
            {
                registers[i] = (ushort)((response[9 + i * 2] << 8) | response[10 + i * 2]);
            }
            return registers;
        }

        public void Dispose()
        {
            _stream?.Dispose();
            _client?.Dispose();
            _lock.Dispose();
        }
    }
}
