import shutil
from pathlib import Path

from reconcile.caminhos import FONTES


def baixar(destino: Path) -> list[Path]:
    import kagglehub

    destino.mkdir(parents=True, exist_ok=True)
    pastas = {ds: Path(kagglehub.dataset_download(ds)) for ds in {f.dataset for f in FONTES}}

    copiados = []
    for fonte in FONTES:
        origem = pastas[fonte.dataset] / fonte.arquivo
        if not origem.exists():
            raise FileNotFoundError(f"{fonte.arquivo} não veio em {fonte.dataset}")
        copiados.append(Path(shutil.copyfile(origem, destino / fonte.arquivo)))
    return copiados
