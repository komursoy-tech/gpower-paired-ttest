"""Convert grounded source inputs to the single MCP tool's CLI contract."""

from core_engine import calculate_dz_from_differences, calculate_dz_from_groups

from .errors import AgentError
from .inputs import analysis_mode


def prepare_arguments(source, values):
    # Only dz derivation uses the existing public Determine helpers locally.
    # Sample size and power are always calculated by the real MCP tool.
    try:
        if source == "calculate_sample_size":
            dz = values["effect_size_dz"]
        elif source == "calculate_from_differences":
            dz = calculate_dz_from_differences(values["mean_diff"], values["sd_diff"])
        elif source == "calculate_from_groups":
            dz = calculate_dz_from_groups(*(values[key] for key in ("mean1", "mean2", "sd1", "sd2", "correlation")))
        else:
            raise AgentError("Etki büyüklüğünün giriş yöntemi belirlenemedi.")
    except (ValueError, TypeError, ArithmeticError, RuntimeError) as exc:
        raise AgentError(f"Girdi hatası: {type(exc).__name__}: {exc}") from exc
    mode = analysis_mode(values)
    arguments = {
        "test": "t-paired", "mode": mode,
        "tails": 2 if values["tails"] == "two-tailed" else 1,
        "dz": dz, "alpha": values["alpha"],
    }
    if mode == "a-priori":
        arguments["power"] = values["target_power"]
    else:
        arguments["n_total"] = values["n_total"]
    return arguments
