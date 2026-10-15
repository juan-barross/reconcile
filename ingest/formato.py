"""Formatação de números no padrão brasileiro para os relatórios."""

TRACO = "—"
_MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
_BR = str.maketrans(",.", ".,")


def numero(valor: float | None, casas: int = 0) -> str:
    if valor is None:
        return TRACO
    return f"{valor:,.{casas}f}".translate(_BR)


def reais(valor: float | None, casas: int = 2, sinal: bool = False) -> str:
    if valor is None:
        return TRACO
    texto = f"R$ {numero(abs(valor), casas)}"
    if sinal:
        return f"{'+' if valor >= 0 else '−'} {texto}"
    return f"−{texto}" if valor < 0 else texto


def pct(fracao: float, casas: int = 1) -> str:
    return f"{100 * fracao:.{casas}f}%".replace(".", ",")


def mes_extenso(mes: str) -> str:
    ano, m = mes.split("-")
    return f"{_MESES[int(m) - 1]}/{ano}"
