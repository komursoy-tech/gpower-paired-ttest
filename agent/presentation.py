def present(result, arguments):
    direction = "çift yönlü" if arguments["tails"] == "two-tailed" else "tek yönlü"
    return (
        f"MCP hesaplama sonucu: {direction} eşleştirilmiş t-testi için "
        f"en az {result['sample_size']} tamamlanmış katılımcı/eşleşmiş çift gerekir.\n"
        f"Alpha: {arguments['alpha']:g}; hedef güç: %{arguments['target_power'] * 100:g}.\n"
        f"Serbestlik derecesi (df): {result['df']}; delta: {result['delta']:.6f}; "
        f"kritik t: {result['critical_t']:.6f}; ulaşılan güç: %{result['actual_power'] * 100:.4f}.\n"
        "Bu sayı tamamlanmış çiftleri belirtir; kayıp katılımcı payı eklenmemiştir."
    )
