"""Diagnóstico conservador, sem dependências externas nem identificadores pessoais."""
import ctypes
import json
import os
import platform
from pathlib import Path
import subprocess
import sys

SKILL=Path(__file__).resolve().parents[1]
RUNTIME=SKILL/'runtime'

def command(args):
    try: return subprocess.check_output(args,stderr=subprocess.DEVNULL,timeout=8,text=True).strip()
    except (OSError,subprocess.SubprocessError): return ''

def ram_bytes(system):
    if system=='Darwin':
        value=command(['sysctl','-n','hw.memsize'])
        return int(value) if value.isdigit() else None
    if system=='Windows':
        class Memory(ctypes.Structure):
            _fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong)]+[(s,ctypes.c_ulonglong) for s in ('total','available','page','page_available','virtual','virtual_available','extended')]
        info=Memory();info.length=ctypes.sizeof(info)
        return info.total if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(info)) else None
    try: return os.sysconf('SC_PAGE_SIZE')*os.sysconf('SC_PHYS_PAGES')
    except (ValueError,OSError,AttributeError): return None

def recommend(memory,logical,physical=None):
    # Limites operacionais, não alterações na proporção ou no motor.
    gb=memory/(1024**3) if memory else 4
    if gb<4: tile,cap=64,8_000_000
    elif gb<8: tile,cap=96,16_000_000
    elif gb<16: tile,cap=160,32_000_000
    else: tile,cap=256,32_000_000
    cores=physical or max(1,logical//2)
    threads=min(4,max(1,cores-1 if cores>2 else cores))
    return {'backend':'ncnn-cpu','threads':threads,'tile':tile,'context':32,
            'max_output_pixels':cap,'timeout_per_image_seconds':3600,
            'default_scale':4,'default_ppi':300,'default_strength':20}

def detect():
    system=platform.system();logical=os.cpu_count() or 1;physical=None
    cpu=platform.processor() or platform.machine()
    if system=='Darwin':
        cpu=command(['sysctl','-n','machdep.cpu.brand_string']) or cpu
        count=command(['sysctl','-n','hw.physicalcpu']);physical=int(count) if count.isdigit() else None
    elif system=='Windows':
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,r'HARDWARE\DESCRIPTION\System\CentralProcessor\0') as key:
                cpu=winreg.QueryValueEx(key,'ProcessorNameString')[0].strip()
        except OSError: pass
    memory=ram_bytes(system);warnings=[]
    arch=platform.machine().lower()
    if system not in ('Darwin','Windows'): warnings.append('Sistema fora dos alvos validados; uso experimental.')
    if arch not in ('amd64','x86_64','arm64','aarch64'): warnings.append('Arquitetura não suportada pelos pacotes previstos.')
    if not (3,9)<=sys.version_info[:2]<=(3,12): warnings.append('Instalador exige Python 3.9 a 3.12.')
    if system=='Darwin' and int((platform.mac_ver()[0] or '0').split('.')[0])<11:
        warnings.append('O pacote NCNN utilizado exige macOS 11 ou superior.')
    if system=='Darwin' and command(['sysctl','-n','sysctl.proc_translated'])=='1':
        warnings.append('Python em Rosetta: preferir Python arm64 nativo para aproveitar Apple Silicon.')
    if memory is None: warnings.append('Não foi possível medir RAM; perfil conservador aplicado.')
    return {'system':system,'system_version':platform.mac_ver()[0] if system=='Darwin' else platform.release(),
            'architecture':arch,'cpu':cpu,'logical_cpus':logical,'physical_cpus':physical,
            'ram_bytes':memory,'ram_gib':round(memory/1024**3,2) if memory else None,
            'python':platform.python_version(),'warnings':warnings,'profile':recommend(memory,logical,physical)}

def write_report():
    RUNTIME.mkdir(exist_ok=True)
    report=detect()
    (RUNTIME/'hardware.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return report

if __name__=='__main__': print(json.dumps(write_report(),ensure_ascii=False,indent=2))
