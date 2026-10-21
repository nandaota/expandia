"""Entrada única: diagnóstico, instalação isolada, teste e benchmark local."""
from pathlib import Path
import os,subprocess,sys
ROOT=Path(__file__).resolve().parent
SCRIPTS=ROOT/'plugins'/'expandia'/'skills'/'upscale-natural'/'scripts'
if __name__=='__main__':
    if '--diagnostic-only' in sys.argv:
        raise SystemExit(subprocess.call([sys.executable,str(SCRIPTS/'doctor.py')]))
    subprocess.run([sys.executable,str(SCRIPTS/'setup.py')],check=True)
    runtime=SCRIPTS.parent/'runtime'
    python=runtime/'.venv'/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
    subprocess.run([str(python),str(SCRIPTS/'expandia.py'),'benchmark'],check=True)
    print('\nExpandia preparado neste computador. Use a skill upscale-natural no Codex local.\n'
          'Padrão: 4×, 300 PPI, mistura de 20%; 30% disponível quando solicitado.\n'
          'Diagnóstico e medição em: '+str(runtime))
