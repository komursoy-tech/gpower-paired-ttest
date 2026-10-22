"""Conservative grounding of model arguments in explicit user statements.

This is an input safety gate, not a statistical engine. Unknown phrasing is
clarified rather than guessed. Only percentages are converted to probabilities.
"""

import math
import re

from .errors import AgentError


NUMBER = r"[+-]?\d+(?:[.,]\d+)?(?:[eE][+-]?\d+)?"
GROUP_FIELDS = {"mean1", "mean2", "sd1", "sd2", "correlation"}
ALIASES = {
    "effect_size_dz": r"effect_size_dz|etki büyüklüğü(?: dz)?|d_z|dz",
    "mean_diff": r"mean_diff|fark ortalamasi|farklarin ortalamasi|farki",
    "sd_diff": r"sd_diff|farklarin standart sapmasi|farkin standart sapmasi|fark standart sapmasi",
    "mean1": r"mean1|öncesi ortalamasi|öncesi ortalama|önceki ortalama",
    "mean2": r"mean2|sonrasi ortalamasi|sonrasi ortalama|sonraki ortalama",
    "sd1": r"sd1|öncesi standart sapmasi|öncesi standart sapma",
    "sd2": r"sd2|sonrasi standart sapmasi|sonrasi standart sapma",
    "correlation": r"correlation|korelasyon(?:u)?|r",
    "alpha": r"alpha|alfa|α",
    "target_power": r"target_power|hedef(?:lenen)? güç|güç|power",
}
REQUIRED = {
    "calculate_sample_size": ["effect_size_dz", "alpha", "target_power", "tails"],
    "calculate_from_differences": ["mean_diff", "sd_diff", "alpha", "target_power", "tails"],
    "calculate_from_groups": ["mean1", "mean2", "sd1", "sd2", "correlation", "alpha", "target_power", "tails"],
}
LABELS = {
    "effect_size_dz": "etki büyüklüğü (dz)", "mean_diff": "fark ortalaması (mean_diff)",
    "sd_diff": "farkların standart sapması (sd_diff)", "mean1": "öncesi ortalama (mean1)",
    "mean2": "sonrası ortalama (mean2)", "sd1": "öncesi standart sapma (sd1)",
    "sd2": "sonrası standart sapma (sd2)", "correlation": "korelasyon (correlation)",
    "alpha": "alpha", "target_power": "hedef güç", "tails": "test yönü (tek yönlü / çift yönlü)",
}


def normalize(text):
    return text.casefold().replace("i\u0307", "i").replace("ı", "i")


def extract_explicit(text, context=None, *, requested_sd_diff=False):
    text = normalize(text)
    if re.search(r"\bveya\b|\bbelirsiz\b|\bbilmiyorum\b|\bdeğil\b", text):
        raise AgentError("Belirsiz veya alternatifli ifade var. Kullanılacak değeri ve test yönünü açıkça belirtin.")
    if re.search(r"bağimsiz (?:iki )?grup", text):
        raise AgentError("Bu araçlar eşleştirilmiş ölçümler içindir. Ölçümler aynı kişilere mi ait?")
    found = {}
    for field, alias in ALIASES.items():
        matches = re.finditer(
            rf"(?<!\w)(?:{alias})(?!\w)\s*(?:=|:)?\s*(%|yüzde\s+)?({NUMBER})(\s*%)?", text,
        )
        values = set()
        for match in matches:
            value = float(match[2].replace(",", "."))
            if match[1] or match[3]:
                if field not in {"alpha", "target_power"}:
                    raise AgentError(f"{LABELS[field]} yüzde olarak yorumlanamaz; açık değer belirtin.")
                value /= 100
            if not math.isfinite(value):
                raise AgentError(f"{LABELS[field]} sonlu olmalı.")
            values.add(value)
        if len(values) > 1:
            raise AgentError(f"{LABELS[field]} için çelişkili değerler var. Tek bir değer belirtin.")
        if values:
            found[field] = values.pop()

    # "Each measurement" explicitly supplies the same SD for both measurements,
    # never the SD of differences. No means or correlation can be inferred.
    shared = re.findall(
        rf"(?:her (?:bir |iki )?ölçümün|iki ölçümün de)\s+standart sapma(?:si|lari)?\s*(?:=|:)?\s*({NUMBER})", text,
    )
    shared_values = {float(value.replace(",", ".")) for value in shared}
    if any(not math.isfinite(value) for value in shared_values):
        raise AgentError("Ölçümlerin standart sapması sonlu olmalı.")
    if len(shared_values) > 1:
        raise AgentError("Ölçümlerin standart sapmaları çelişkili; sd1 ve sd2 değerlerini belirtin.")
    if shared_values:
        value = shared_values.pop()
        for field in ("sd1", "sd2"):
            if field in found and found[field] != value:
                raise AgentError("Ölçümlerin standart sapmaları çelişkili; sd1 ve sd2 değerlerini belirtin.")
            found[field] = value

    # Preserve the established possessive shorthand "difference ..., its SD ..."
    # and a direct answer to an explicit question about sd_diff. A difference
    # mean alone does not establish what an unrelated SD measures.
    known = {**(context or {}), **found}
    difference_reference = re.search(
        rf"farki\s*{NUMBER}(?:\s+\w+)?\s*[,;]\s*standart sapmasi\s", text,
    )
    measurement_reference = re.search(r"ölçüm|grup|öncesi\s+standart|sonrasi\s+standart", text)
    if "mean_diff" in known and "sd_diff" not in found and not ({"sd1", "sd2"} & known.keys()):
        matches = re.findall(rf"standart sapma(?:si)?\s*(?:=|:)?\s*({NUMBER})", text)
        values = {float(value.replace(",", ".")) for value in matches}
        if any(not math.isfinite(value) for value in values):
            raise AgentError("Standart sapma sonlu olmalı.")
        if len(values) == 1 and not measurement_reference and (difference_reference or requested_sd_diff):
            found["sd_diff"] = values.pop()
        elif len(values) > 1:
            raise AgentError("Standart sapma belirsiz. Farkların standart sapmasını sd_diff olarak belirtin.")

    tails = set()
    for pattern, value in [(r"two-tailed|çift yönlü|iki yönlü", "two-tailed"),
                           (r"one-tailed|tek yönlü", "one-tailed")]:
        if re.search(pattern, text):
            tails.add(value)
    if len(tails) > 1 or re.search(r"(?:yönlü|tailed)\s+değil", text):
        raise AgentError("Test yönü belirsiz. Tek yönlü mü, çift yönlü mü?")
    if tails:
        found["tails"] = tails.pop()
    return found


def ambiguous_sd(text, updates):
    """An untyped SD must not reuse a previously cached SD or trigger a call."""
    return bool(re.search(r"standart sapma", normalize(text))) and not (
        {"sd_diff", "sd1", "sd2"} & updates.keys()
    )


def input_mode(values):
    modes = []
    if "effect_size_dz" in values:
        modes.append("calculate_sample_size")
    groups_present = bool(GROUP_FIELDS & values.keys())
    if "sd_diff" in values or ("mean_diff" in values and not groups_present):
        modes.append("calculate_from_differences")
    if groups_present:
        modes.append("calculate_from_groups")
    if len(modes) > 1:
        raise AgentError("Birden fazla giriş yöntemi var. dz, farklar veya grup istatistiklerinden birini seçin; 'yeni' ile sıfırlayabilirsiniz.")
    return modes[0] if modes else None


def clarification(mode, values):
    if mode is None:
        return "dz değerini, fark ortalaması ve farkların standart sapmasını veya eşleştirilmiş grup istatistiklerini belirtin. Alpha, hedef güç ve test yönü de gereklidir. Alan adlarıyla da yazabilirsiniz."
    missing = [LABELS[key] for key in REQUIRED[mode] if key not in values]
    if missing:
        return "Hesaplama için eksik veya net olmayan bilgileri belirtin: " + ", ".join(missing) + ". Değerleri tahmin etmeyeceğim."
    return None
