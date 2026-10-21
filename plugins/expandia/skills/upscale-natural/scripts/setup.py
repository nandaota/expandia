"""Instala somente em ambiente isolado da skill e baixa pesos oficiais verificados."""
from pathlib import Path
import hashlib,json,os,platform,subprocess,sys,tempfile,urllib.request,venv,zipfile
from doctor import SKILL,RUNTIME,write_report

MODEL_URL='https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesrgan-ncnn-vulkan-20220424-windows.zip'
MODEL_HASHES={
    'realesrgan-x4plus.bin':'713ee713b0353afaa27976f0563a64a5043bd70b9bd8936c2e26e25ebcdbcddf',
    'realesrgan-x4plus.param':'35330ececcea33b6c397a72548e788d5d53becee4734c50b7fada36e89f10a86'}
REQUIREMENTS=['numpy==1.26.4','Pillow==10.4.0','opencv-python-headless==4.8.1.78']
NCNN='ncnn==1.0.20250503'

def models():
    folder=RUNTIME/'models';folder.mkdir(exist_ok=True)
    if all((folder/n).exists() and hashlib.sha256((folder/n).read_bytes()).hexdigest()==sha for n,sha in MODEL_HASHES.items()): return
    print('Baixando pesos oficiais Real-ESRGAN (aprox. 45 MB). As imagens não são enviadas.',flush=True)
    with tempfile.TemporaryDirectory(dir=RUNTIME) as temp:
        archive=Path(temp)/'models.zip'
        # O ZIP tem nome Windows, mas apenas .bin/.param portáveis são extraídos.
        with urllib.request.urlopen(MODEL_URL,timeout=90) as response,archive.open('wb') as stream:
            while True:
                block=response.read(1024*1024)
                if not block: break
                stream.write(block)
        with zipfile.ZipFile(archive) as bundle:
            for name,sha in MODEL_HASHES.items():
                data=bundle.read('models/'+name)
                if hashlib.sha256(data).hexdigest()!=sha: raise RuntimeError('Checksum do modelo divergente: '+name)
                (folder/name).write_bytes(data)

def main():
    report=write_report();print(json.dumps(report,ensure_ascii=False,indent=2),flush=True)
    if not (3,9)<=sys.version_info[:2]<=(3,12): raise SystemExit('Use Python 3.9 a 3.12 (recomendado: 3.12).')
    if report['architecture'] not in ('amd64','x86_64','arm64','aarch64'): raise SystemExit('Arquitetura incompatível.')
    if report['system']=='Darwin' and int(report['system_version'].split('.')[0])<11: raise SystemExit('É necessário macOS 11+.')
    env=RUNTIME/'.venv';python=env/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
    if not python.exists(): venv.EnvBuilder(with_pip=True).create(env)
    # Não compilar fontes nem instalar em Python global. Falhas são explícitas.
    subprocess.run([str(python),'-m','pip','install','--only-binary=:all:','--timeout','30','--retries','1',*REQUIREMENTS],check=True)
    # Usamos somente o binding nativo, não o model zoo do NCNN. Seus extras
    # incluem opencv-python, que conflita com opencv-python-headless.
    subprocess.run([str(python),'-m','pip','install','--only-binary=:all:','--no-deps','--timeout','30','--retries','1',NCNN],check=True)
    models()
    subprocess.run([str(python),str(Path(__file__).with_name('expandia.py')),'self-test'],check=True)
    (RUNTIME/'installation.json').write_text(json.dumps({'system':report['system'],'architecture':report['architecture'],'python':platform.python_version(),'packages':REQUIREMENTS+[NCNN],'self_test':'passed'},indent=2),encoding='utf-8')
    print('Expandia configurado. Próximo passo: benchmark e teste de uma imagem no computador de destino.',flush=True)

if __name__=='__main__': main()
