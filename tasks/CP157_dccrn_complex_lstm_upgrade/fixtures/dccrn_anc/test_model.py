"""
Test script for DCCRN-ANC model (basic sanity check).
Run: python test_model.py
"""
import torch
from core.dccrn import DCCRN


def test_forward_pass():
    """Test that the model runs a forward pass without errors."""
    model = DCCRN(conditioning_enabled=True, embed_dim=64, rir_len=512, lstm_type='real')
    model.eval()

    B, F, T = 2, 161, 10
    X_r = torch.randn(B, 1, F, T)
    X_i = torch.randn(B, 1, F, T)
    p_rir = torch.randn(B, 512)
    s_rir = torch.randn(B, 512)

    with torch.no_grad():
        (Y_r, Y_i), state, z = model((X_r, X_i), p_rir=p_rir, s_rir=s_rir)

    print(f"Input shape:  ({B}, 1, {F}, {T})")
    print(f"Output shape: {Y_r.shape}")
    print(f"Embedding:    {z.shape}")
    print(f"LSTM state:   h={state[0].shape}, c={state[1].shape}")
    print(f"Parameters:   {sum(p.numel() for p in model.parameters()):,}")
    print("PASS: Forward pass succeeded")


if __name__ == "__main__":
    test_forward_pass()
