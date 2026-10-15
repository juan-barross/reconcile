"""Download dos datasets da Olist pelo kagglehub.

Os datasets são públicos e baixam sem credencial; se houver ~/.kaggle/kaggle.json
ou KAGGLE_USERNAME/KAGGLE_KEY, o kagglehub usa.
"""

import shutil
from pathlib import Path

from ingest.fontes import FONTES


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
