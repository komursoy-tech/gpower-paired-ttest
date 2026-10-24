def present(result, arguments):
    direction = "çift yönlü" if arguments["tails"] == 2 else "tek yönlü"
    post_hoc = arguments["mode"] == "post-hoc"
    n = arguments["n_total"] if post_hoc else result["n_total"]
    power = result["power"] if post_hoc else result["actual_power"]
    description = (
        f"{n} tamamlanmış katılımcı/eşleşmiş çift için post-hoc güç hesaplandı.\n"
        if post_hoc else f"en az {n} tamamlanmış katılımcı/eşleşmiş çift gerekir.\n"
    )
    target = "" if post_hoc else f"; hedef güç: %{arguments['power'] * 100:g}"
    return (
        f"MCP hesaplama sonucu: {direction} eşleştirilmiş t-testi için "
        f"{description}"
        f"Alpha: {arguments['alpha']:g}{target}.\n"
        f"Serbestlik derecesi (df): {result['df']}; ncp: {result['ncp']:.6f}; "
        f"kritik t: {result['critical_t']:.6f}; ulaşılan güç: %{power * 100:.4f}.\n"
        "Bu sayı tamamlanmış çiftleri belirtir; kayıp katılımcı payı eklenmemiştir."
    )
