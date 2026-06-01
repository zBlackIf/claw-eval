"""
DCCRN-ANC: Deep Complex Convolution Recurrent Network for Active Noise Control.

Current architecture: 4-layer encoder/decoder + Real LSTM + Real FiLM conditioning.
"""
import torch
import torch.nn as nn
import torch.nn.functional as F


class ComplexConv2d(nn.Module):
    """Complex-valued 2D convolution."""
    def __init__(self, in_channels, out_channels, kernel_size=(5, 2),
                 stride=(2, 1), padding=(2, 1)):
        super().__init__()
        self.conv_r = nn.Conv2d(in_channels, out_channels, kernel_size,
                                stride=stride, padding=padding)
        self.conv_i = nn.Conv2d(in_channels, out_channels, kernel_size,
                                stride=stride, padding=padding)

    def forward(self, x_r, x_i):
        # Complex multiplication: (a+bi)(c+di) = (ac-bd) + (ad+bc)i
        out_r = self.conv_r(x_r) - self.conv_i(x_i)
        out_i = self.conv_r(x_i) + self.conv_i(x_r)
        return out_r, out_i


class ComplexConvTranspose2d(nn.Module):
    """Complex-valued 2D transposed convolution."""
    def __init__(self, in_channels, out_channels, kernel_size=(5, 2),
                 stride=(2, 1), padding=(2, 0), output_padding=(1, 0)):
        super().__init__()
        self.tconv_r = nn.ConvTranspose2d(in_channels, out_channels, kernel_size,
                                          stride=stride, padding=padding,
                                          output_padding=output_padding)
        self.tconv_i = nn.ConvTranspose2d(in_channels, out_channels, kernel_size,
                                          stride=stride, padding=padding,
                                          output_padding=output_padding)

    def forward(self, x_r, x_i):
        out_r = self.tconv_r(x_r) - self.tconv_i(x_i)
        out_i = self.tconv_r(x_i) + self.tconv_i(x_r)
        return out_r, out_i


class ComplexBatchNorm2d(nn.Module):
    """Batch normalization applied independently to real and imaginary parts."""
    def __init__(self, num_features):
        super().__init__()
        self.bn_r = nn.BatchNorm2d(num_features)
        self.bn_i = nn.BatchNorm2d(num_features)

    def forward(self, x_r, x_i):
        return self.bn_r(x_r), self.bn_i(x_i)


class RIREncoder(nn.Module):
    """Time-domain RIR encoder: produces embedding from primary + secondary RIR pair."""
    def __init__(self, rir_len=512, embed_dim=64):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(rir_len * 2, 256),
            nn.ReLU(),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Linear(128, embed_dim),
        )

    def forward(self, p_rir, s_rir):
        """
        Args:
            p_rir: (B, rir_len) primary path RIR
            s_rir: (B, rir_len) secondary path RIR
        Returns:
            z: (B, embed_dim) conditioning embedding
        """
        x = torch.cat([p_rir, s_rir], dim=-1)
        return self.net(x)


class RealFiLM(nn.Module):
    """Feature-wise Linear Modulation (Real-valued).

    Applies affine transform: gamma * h + beta
    where gamma and beta are derived from conditioning embedding z.
    Initialized to identity: gamma=1, beta=0.
    """
    def __init__(self, feature_dim, embed_dim=64):
        super().__init__()
        self.gamma_proj = nn.Linear(embed_dim, feature_dim)
        self.beta_proj = nn.Linear(embed_dim, feature_dim)
        # Initialize to identity transform
        nn.init.ones_(self.gamma_proj.weight[:, :1])
        nn.init.zeros_(self.gamma_proj.weight[:, 1:])
        nn.init.zeros_(self.gamma_proj.bias)
        nn.init.zeros_(self.beta_proj.weight)
        nn.init.zeros_(self.beta_proj.bias)

    def forward(self, h, z):
        """
        Args:
            h: (B, feature_dim, ...) hidden features
            z: (B, embed_dim) conditioning embedding
        Returns:
            modulated: gamma * h + beta
        """
        gamma = self.gamma_proj(z)  # (B, feature_dim)
        beta = self.beta_proj(z)    # (B, feature_dim)
        # Reshape for broadcasting
        while gamma.dim() < h.dim():
            gamma = gamma.unsqueeze(-1)
            beta = beta.unsqueeze(-1)
        return gamma * h + beta


class DCCRN(nn.Module):
    """DCCRN-ANC with 4-layer encoder/decoder, Real LSTM, and Real FiLM conditioning.

    Architecture:
        Encoder: 4 layers (1->16->32->64->128), ComplexConv2d + ComplexBN + PReLU
        LSTM: Real-valued (concatenates real+imag parts)
        FiLM: Real-valued affine modulation from RIR embedding
        Decoder: 4 layers with skip connections (reverse of encoder)
    """
    def __init__(self, conditioning_enabled=True, embed_dim=64,
                 rir_encoder_type='time_domain', rir_len=512,
                 lstm_type='real'):
        super().__init__()
        self.conditioning_enabled = conditioning_enabled
        self.embed_dim = embed_dim
        self.lstm_type = lstm_type

        # Encoder layers: 4 layers
        encoder_channels = [1, 16, 32, 64, 128]
        self.encoders = nn.ModuleList()
        self.encoder_bns = nn.ModuleList()
        for i in range(4):
            self.encoders.append(
                ComplexConv2d(encoder_channels[i], encoder_channels[i+1],
                              kernel_size=(5, 2), stride=(2, 1), padding=(2, 1))
            )
            self.encoder_bns.append(ComplexBatchNorm2d(encoder_channels[i+1]))

        # LSTM: Real-valued (concatenates real and imaginary parts)
        # After 4 layers of stride-2 on freq axis: 161 -> 81 -> 41 -> 21 -> 11
        # Input to LSTM: 128 channels * 11 freq_bins * 2 (real+imag)
        self.lstm_input_size = 128 * 11 * 2
        self.lstm_hidden_size = 128 * 11
        self.lstm = nn.LSTM(
            input_size=self.lstm_input_size,
            hidden_size=self.lstm_hidden_size,
            num_layers=2,
            batch_first=True,
        )

        # FiLM conditioning
        if self.conditioning_enabled:
            self.rir_encoder = RIREncoder(rir_len=rir_len, embed_dim=embed_dim)
            self.film = RealFiLM(feature_dim=self.lstm_hidden_size, embed_dim=embed_dim)

        # Decoder layers: 4 layers (with skip connections, so input channels are doubled)
        decoder_channels = [128, 64, 32, 16, 1]
        self.decoders = nn.ModuleList()
        self.decoder_bns = nn.ModuleList()
        for i in range(4):
            in_ch = decoder_channels[i] * 2 if i > 0 else decoder_channels[i]
            # First decoder gets LSTM output (no skip from encoder)
            # Actually skip connections double the channels
            if i == 0:
                in_ch = decoder_channels[i]
            else:
                in_ch = decoder_channels[i] * 2  # skip connection
            self.decoders.append(
                ComplexConvTranspose2d(in_ch, decoder_channels[i+1],
                                       kernel_size=(5, 2), stride=(2, 1),
                                       padding=(2, 0), output_padding=(1, 0))
            )
            if i < 3:
                self.decoder_bns.append(ComplexBatchNorm2d(decoder_channels[i+1]))

    def forward(self, inputs, p_rir=None, s_rir=None, lstm_state=None):
        """
        Args:
            inputs: tuple (X_r, X_i) each of shape (B, 1, F, T)
            p_rir: (B, rir_len) primary RIR (optional)
            s_rir: (B, rir_len) secondary RIR (optional)
            lstm_state: tuple of (h_n, c_n) for stateful inference
        Returns:
            outputs: tuple (Y_r, Y_i) each of shape (B, 1, F, T)
            lstm_state_out: tuple of (h_n, c_n)
            z: conditioning embedding or None
        """
        X_r, X_i = inputs
        B, C, F, T = X_r.shape

        # Conditioning embedding
        z = None
        if self.conditioning_enabled and p_rir is not None and s_rir is not None:
            z = self.rir_encoder(p_rir, s_rir)

        # Encoder
        encoder_outputs = []
        h_r, h_i = X_r, X_i
        for i, (enc, bn) in enumerate(zip(self.encoders, self.encoder_bns)):
            h_r, h_i = enc(h_r, h_i)
            h_r, h_i = bn(h_r, h_i)
            h_r = F.prelu(h_r, torch.tensor(0.3).to(h_r.device))
            h_i = F.prelu(h_i, torch.tensor(0.3).to(h_i.device))
            encoder_outputs.append((h_r, h_i))

        # Reshape for LSTM: (B, T, C*F*2)
        # h_r, h_i are (B, 128, 11, T) after 4 encoder layers
        h_r_perm = h_r.permute(0, 3, 1, 2)  # (B, T, 128, 11)
        h_i_perm = h_i.permute(0, 3, 1, 2)  # (B, T, 128, 11)
        lstm_in = torch.cat([
            h_r_perm.reshape(B, T, -1),
            h_i_perm.reshape(B, T, -1)
        ], dim=-1)  # (B, T, 128*11*2)

        # LSTM
        rnn_out, lstm_state_out = self.lstm(lstm_in, lstm_state)
        # rnn_out: (B, T, 128*11)

        # FiLM conditioning on LSTM output
        if self.conditioning_enabled and z is not None:
            # rnn_out: (B, T, hidden_size) -> apply FiLM
            rnn_out_perm = rnn_out.permute(0, 2, 1)  # (B, hidden_size, T)
            rnn_out_perm = self.film(rnn_out_perm, z)
            rnn_out = rnn_out_perm.permute(0, 2, 1)  # (B, T, hidden_size)

        # Reshape back: split into real and imaginary
        h_r = rnn_out[..., :self.lstm_hidden_size // 1].reshape(B, T, 128, 11)
        # Wait, lstm_hidden_size = 128*11, so output is (B, T, 128*11)
        # Split into real/imag for decoder
        h_r = rnn_out.reshape(B, T, 128, 11).permute(0, 2, 3, 1)  # (B, 128, 11, T)
        h_i = torch.zeros_like(h_r)  # Real LSTM loses imaginary info

        # Decoder with skip connections
        for i, dec in enumerate(self.decoders):
            if i > 0:
                # Skip connection from encoder (reverse order)
                enc_r, enc_i = encoder_outputs[-(i+1)]
                # Crop to match sizes if needed
                min_f = min(h_r.shape[2], enc_r.shape[2])
                min_t = min(h_r.shape[3], enc_r.shape[3])
                h_r = torch.cat([h_r[:, :, :min_f, :min_t],
                                 enc_r[:, :, :min_f, :min_t]], dim=1)
                h_i = torch.cat([h_i[:, :, :min_f, :min_t],
                                 enc_i[:, :, :min_f, :min_t]], dim=1)

            h_r, h_i = dec(h_r, h_i)
            if i < 3:
                h_r, h_i = self.decoder_bns[i](h_r, h_i)
                h_r = F.prelu(h_r, torch.tensor(0.3).to(h_r.device))
                h_i = F.prelu(h_i, torch.tensor(0.3).to(h_i.device))

        # Crop output to match input size
        Y_r = h_r[:, :, :F, :T]
        Y_i = h_i[:, :, :F, :T]

        return (Y_r, Y_i), lstm_state_out, z
