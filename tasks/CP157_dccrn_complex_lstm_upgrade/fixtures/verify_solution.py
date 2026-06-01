"""Hidden verifier for CP157 — DCCRN Complex LSTM + Complex FiLM + 5-layer Upgrade."""
from __future__ import annotations

import json
import sys
import os
from pathlib import Path


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _try_import_and_run(ws: Path) -> dict:
    """Try to import the model and run a forward pass to verify correctness."""
    result = {"importable": False, "forward_pass": False, "complex_lstm_works": False,
              "complex_film_works": False, "state_shape_correct": False}

    # Add workspace to path
    proj_dir = ws / "dccrn_anc"
    if not proj_dir.exists():
        proj_dir = ws / "fixtures" / "dccrn_anc"
    if not proj_dir.exists():
        return result

    sys.path.insert(0, str(proj_dir))
    os.chdir(str(proj_dir))

    try:
        import torch
        # Try importing Complex LSTM module
        try:
            from core.complex_lstm import ComplexLSTM
            result["importable"] = True
        except ImportError:
            # Maybe it's defined in dccrn.py or another module
            try:
                from core.dccrn import DCCRN
                result["importable"] = True
            except Exception:
                return result

        # Try importing the upgraded DCCRN
        from core.dccrn import DCCRN

        # Test with complex lstm_type
        try:
            model = DCCRN(conditioning_enabled=True, embed_dim=64, rir_len=512, lstm_type='complex')
            model.eval()
            result["importable"] = True
        except Exception as e:
            # Fallback: maybe the model always uses complex now
            try:
                model = DCCRN(conditioning_enabled=True, embed_dim=64, rir_len=512)
                model.eval()
                result["importable"] = True
            except Exception:
                return result

        # Forward pass test
        B, F, T = 2, 161, 10
        X_r = torch.randn(B, 1, F, T)
        X_i = torch.randn(B, 1, F, T)
        p_rir = torch.randn(B, 512)
        s_rir = torch.randn(B, 512)

        with torch.no_grad():
            (Y_r, Y_i), state, z = model((X_r, X_i), p_rir=p_rir, s_rir=s_rir)

        # Check output shapes
        if Y_r.shape == (B, 1, F, T) and Y_i.shape == (B, 1, F, T):
            result["forward_pass"] = True

        # Check that LSTM state is complex (4 elements: h_r, c_r, h_i, c_i or similar)
        if state is not None:
            if isinstance(state, (list, tuple)):
                if len(state) == 4:
                    # Complex LSTM returns (h_r, c_r, h_i, c_i) or ((h_r,h_i), (c_r,c_i))
                    result["state_shape_correct"] = True
                elif len(state) == 2:
                    # Could still be complex if each element has doubled size
                    h, c = state[0], state[1]
                    # Complex LSTM might pack real+imag or use complex tensors
                    if h.is_complex() or (hasattr(h, 'shape') and len(h.shape) >= 2):
                        result["state_shape_correct"] = True

        # Verify imaginary output is non-zero (proves complex processing path)
        if Y_i.abs().sum() > 1e-6:
            result["complex_lstm_works"] = True

        # Test FiLM with identity check
        try:
            # Check if ComplexFiLM exists
            has_complex_film = False
            for name, module in model.named_modules():
                mod_class = module.__class__.__name__
                if 'ComplexFiLM' in mod_class or 'complex_film' in name.lower():
                    has_complex_film = True
                    break
                if 'FiLM' in mod_class and 'Complex' in mod_class:
                    has_complex_film = True
                    break

            if not has_complex_film:
                # Check source code for ComplexFiLM class definition
                dccrn_src = _read(proj_dir / "core" / "dccrn.py")
                if "ComplexFiLM" in dccrn_src or "complex_film" in dccrn_src.lower():
                    has_complex_film = True

            result["complex_film_works"] = has_complex_film
        except Exception:
            pass

    except Exception as e:
        result["error"] = str(e)[:200]

    return result


def grade_workspace(ws: Path) -> dict:
    proj_dir = ws / "dccrn_anc"
    if not proj_dir.exists():
        proj_dir = ws / "fixtures" / "dccrn_anc"

    components = {k: 0.0 for k in [
        "complex_lstm_module",
        "complex_film_module",
        "five_layer_encoder",
        "forward_pass_correct",
        "complex_arithmetic",
        "identity_init",
    ]}

    if not proj_dir.exists():
        return {"overall_score": 0.0, "components": components, "weights": _weights()}

    # --- Check 1: Complex LSTM module exists ---
    complex_lstm_file = None
    for candidate in [
        proj_dir / "core" / "complex_lstm.py",
        proj_dir / "core" / "complex_rnn.py",
    ]:
        if candidate.exists():
            complex_lstm_file = candidate
            break

    if complex_lstm_file:
        src = _read(complex_lstm_file)
        has_class = "class" in src and ("ComplexLSTM" in src or "Complex" in src.lower() and "lstm" in src.lower())
        has_complex_mul = ("real" in src.lower() and "imag" in src.lower()) or "complex" in src.lower()
        has_gates = "gate" in src.lower() or "sigmoid" in src.lower() or "tanh" in src.lower()
        score = 0.0
        if has_class:
            score += 0.4
        if has_complex_mul:
            score += 0.3
        if has_gates:
            score += 0.3
        components["complex_lstm_module"] = min(1.0, score)
    else:
        # Maybe integrated into dccrn.py
        dccrn_src = _read(proj_dir / "core" / "dccrn.py")
        if "ComplexLSTM" in dccrn_src or ("complex" in dccrn_src.lower() and "lstm" in dccrn_src.lower()):
            has_complex_math = "real" in dccrn_src and "imag" in dccrn_src
            components["complex_lstm_module"] = 0.7 if has_complex_math else 0.4

    # --- Check 2: Complex FiLM module ---
    dccrn_src = _read(proj_dir / "core" / "dccrn.py")
    film_sources = [dccrn_src]
    for f in (proj_dir / "core").glob("*.py"):
        film_sources.append(_read(f))
    all_src = "\n".join(film_sources)

    has_complex_film_class = "ComplexFiLM" in all_src
    has_film_complex_mul = False
    # Complex FiLM: (gamma_r + i*gamma_i) * (h_r + i*h_i) + (beta_r + i*beta_i)
    if has_complex_film_class:
        # Look for complex multiplication pattern in FiLM
        if ("gamma_r" in all_src or "gamma_real" in all_src) and ("gamma_i" in all_src or "gamma_imag" in all_src):
            has_film_complex_mul = True
        elif "complex" in all_src.lower() and ("gamma" in all_src or "scale" in all_src):
            has_film_complex_mul = True

    score = 0.0
    if has_complex_film_class:
        score += 0.5
    if has_film_complex_mul:
        score += 0.5
    components["complex_film_module"] = min(1.0, score)

    # --- Check 3: 5-layer encoder ---
    # Check that encoder has 5 layers (channels: 1->16->32->64->128->256)
    dccrn_src = _read(proj_dir / "core" / "dccrn.py")
    # Count encoder layers by looking for channel definitions or layer count
    has_5_enc = False
    if "256" in dccrn_src:
        # Look for 5-layer pattern
        if ("encoder_channels" in dccrn_src and "256" in dccrn_src) or \
           "enc5" in dccrn_src.lower() or \
           ("range(5)" in dccrn_src or "range(num_layers)" in dccrn_src):
            has_5_enc = True
        # Also check: [1, 16, 32, 64, 128, 256]
        if "128, 256" in dccrn_src or "128,256" in dccrn_src:
            has_5_enc = True
    # Alternative: count actual encoder module definitions
    enc_count = dccrn_src.lower().count("complexconv2d")
    if enc_count >= 10:  # 5 encoder + 5 decoder = 10
        has_5_enc = True

    components["five_layer_encoder"] = 1.0 if has_5_enc else 0.0

    # --- Check 4 & 5: Forward pass and complex arithmetic ---
    runtime_results = _try_import_and_run(ws)
    if runtime_results.get("forward_pass"):
        components["forward_pass_correct"] = 1.0
    elif runtime_results.get("importable"):
        components["forward_pass_correct"] = 0.3

    if runtime_results.get("complex_lstm_works"):
        components["complex_arithmetic"] = 1.0
    elif runtime_results.get("importable"):
        # Check source for complex arithmetic patterns
        all_core_src = ""
        if (proj_dir / "core").exists():
            for f in (proj_dir / "core").glob("*.py"):
                all_core_src += _read(f)
        # Look for correct complex multiplication: ac-bd, ad+bc
        patterns = [
            ("_r" in all_core_src and "_i" in all_core_src),
            ("real" in all_core_src and "imag" in all_core_src),
        ]
        if any(patterns):
            components["complex_arithmetic"] = 0.5

    # --- Check 6: Identity initialization ---
    # Complex FiLM should init gamma_r=1, gamma_i=0, beta_r=0, beta_i=0
    all_core_src = ""
    if (proj_dir / "core").exists():
        for f in (proj_dir / "core").glob("*.py"):
            all_core_src += _read(f)

    has_identity_init = False
    if "ones_" in all_core_src or "init.ones" in all_core_src:
        if "zeros_" in all_core_src or "init.zeros" in all_core_src:
            # Check for gamma_r=1 pattern
            if "gamma_r" in all_core_src or "gamma_real" in all_core_src:
                has_identity_init = True
            elif "identity" in all_core_src.lower() or "恒等" in all_core_src:
                has_identity_init = True
    # Also check: if FiLM initialized so that output equals input when z=0
    if "gamma" in all_core_src and ("1.0" in all_core_src or "ones" in all_core_src):
        if "beta" in all_core_src and ("0.0" in all_core_src or "zeros" in all_core_src):
            has_identity_init = True

    components["identity_init"] = 1.0 if has_identity_init else 0.0

    weights = _weights()
    overall = sum(weights[k] * components[k] for k in weights)
    return {
        "overall_score": round(overall, 4),
        "components": {k: round(v, 4) for k, v in components.items()},
        "weights": weights,
        "runtime": runtime_results,
    }


def _weights():
    return {
        "complex_lstm_module": 0.25,
        "complex_film_module": 0.20,
        "five_layer_encoder": 0.15,
        "forward_pass_correct": 0.20,
        "complex_arithmetic": 0.10,
        "identity_init": 0.10,
    }


def main():
    # Try multiple possible workspace locations
    for ws in [Path("/workspace"), Path("/workspace/fixtures")]:
        if (ws / "dccrn_anc").exists():
            print(json.dumps(grade_workspace(ws), ensure_ascii=False))
            return
    # Fallback
    print(json.dumps(grade_workspace(Path("/workspace")), ensure_ascii=False))


if __name__ == "__main__":
    main()
