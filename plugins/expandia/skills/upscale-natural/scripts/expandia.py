"""Motor portátil Expandia. Sem API, com execução sequencial e limites adaptativos."""
from pathlib import Path
import argparse,contextlib,gc,hashlib,json,os,shutil,sys,time,warnings
from doctor import RUNTIME,detect,write_report

EXTENSIONS={'.png','.jpg','.jpeg','.tif','.tiff','.webp'}

def libraries():
    global Image,ImageOps,np,cv2
    import numpy as np
    import cv2
    from PIL import Image,ImageOps
    Image.MAX_IMAGE_PIXELS=64_000_000
    warnings.simplefilter('error',Image.DecompressionBombWarning)
    cv2.setNumThreads(1)

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def atomic_json(path,value):
    path=Path(path);temporary=path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
    os.replace(temporary,path)

@contextlib.contextmanager
def exclusive():
    RUNTIME.mkdir(exist_ok=True)
    stream=(RUNTIME/'execution.lock').open('a+b')
    if os.fstat(stream.fileno()).st_size==0: stream.write(b'0');stream.flush()
    stream.seek(0)
    try:
        if os.name=='nt':
            import msvcrt
            msvcrt.locking(stream.fileno(),msvcrt.LK_NBLCK,1)
        else:
            import fcntl
            fcntl.flock(stream.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
    except OSError:
        stream.close();raise RuntimeError('Já há uma execução Expandia neste pacote. Aguarde sua conclusão.')
    try: yield
    finally: stream.close()

@contextlib.contextmanager
def awake():
    helper=None
    if sys.platform=='darwin' and shutil.which('caffeinate'):
        import subprocess
        helper=subprocess.Popen(['caffeinate','-i','-w',str(os.getpid())],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    elif os.name=='nt':
        import ctypes
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)
    try: yield
    finally:
        if helper and helper.poll() is None: helper.terminate()
        if os.name=='nt':
            import ctypes
            ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)

def read_image(path):
    with Image.open(path) as original:
        if original.format not in ('JPEG','PNG','TIFF','WEBP') or getattr(original,'n_frames',1)!=1:
            raise ValueError('Use PNG, JPG, TIFF ou WebP estático de uma página.')
        if original.mode not in ('RGB','L') or 'transparency' in original.info:
            raise ValueError('Esta versão aceita RGB/cinza de 8 bits, sem transparência ou CMYK.')
        profile=original.info.get('icc_profile')
        image=ImageOps.exif_transpose(original).convert('RGB');image.load()
        return image,profile

def plan(path,scale,ppi,profile):
    if scale not in (2,4) or ppi not in (150,300): raise ValueError('Use 2×/4× e 150/300 PPI.')
    image,_=read_image(path);width,height=image.size
    out=(width*scale,height*scale)
    if out[0]*out[1]>profile['max_output_pixels']:
        raise ValueError(f"Saída de {out[0]*out[1]/1e6:.1f} MP excede o limite deste computador ({profile['max_output_pixels']/1e6:.0f} MP). Escolha 2× ou uma imagem menor.")
    return {'input_pixels':[width,height],'output_pixels':list(out),'scale':scale,'ppi':ppi,
            'print_cm':[round(v/ppi*2.54,2) for v in out]}

def fidelity(image,scale,cancel=lambda:False):
    out=image.resize((image.width*scale,image.height*scale),Image.Resampling.LANCZOS)
    reference=out.copy()
    for top in range(0,out.height,192):
        if cancel(): raise InterruptedError('Interrupção solicitada.')
        bottom=min(out.height,top+192);low=max(0,top-8);high=min(out.height,bottom+8)
        rgb=np.asarray(reference.crop((0,low,out.width,high)))
        ycc=cv2.cvtColor(rgb,cv2.COLOR_RGB2YCrCb);y=ycc[:,:,0].astype(np.float32)
        detail=y-cv2.GaussianBlur(y,(0,0),1.2)
        correction=np.clip(np.sign(detail)*np.maximum(np.abs(detail)-1.5,0)*.8,-8,8)
        ycc[:,:,0]=np.clip(y+correction,0,255).astype(np.uint8)
        part=Image.fromarray(cv2.cvtColor(ycc,cv2.COLOR_YCrCb2RGB))
        out.paste(part.crop((0,top-low,out.width,bottom-low)),(0,top))
    return out

def network(profile):
    import ncnn
    folder=RUNTIME/'models'
    from setup import MODEL_HASHES
    for name,value in MODEL_HASHES.items():
        if not (folder/name).exists() or sha(folder/name)!=value:
            raise RuntimeError('Modelo ausente ou checksum divergente. Execute iniciar.py.')
    net=ncnn.Net();net.opt.use_vulkan_compute=False;net.opt.num_threads=profile['threads']
    net.opt.use_fp16_packed=False;net.opt.use_fp16_storage=False;net.opt.use_fp16_arithmetic=False
    if net.load_param(str(folder/'realesrgan-x4plus.param')) or net.load_model(str(folder/'realesrgan-x4plus.bin')):
        raise RuntimeError('Falha ao carregar modelo NCNN.')
    return net

def infer_patch(net,image):
    import ncnn
    data=np.ascontiguousarray(np.asarray(image).transpose(2,0,1),dtype=np.float32)/255
    mat=ncnn.Mat(data).clone()
    with net.create_extractor() as ex:
        ex.set_light_mode(True)
        if ex.input('data',mat): raise RuntimeError('Falha no bloco de entrada.')
        ret,output=ex.extract('output')
        if ret: raise RuntimeError('Inferência NCNN falhou; pode haver insuficiência de memória.')
        data=np.asarray(output).copy()
    if data.shape!=(3,image.height*4,image.width*4): raise RuntimeError('Dimensões neurais inesperadas.')
    return Image.fromarray(np.clip(data.transpose(1,2,0)*255,0,255).round().astype(np.uint8))

def neural(image,scale,profile,progress=lambda value:None,cancel=lambda:False):
    net=network(profile);width,height=image.size;tile=profile['tile'];pad=profile['context']
    total=((width+tile-1)//tile)*((height+tile-1)//tile);done=0;t=time.monotonic()
    out=Image.new('RGB',(width*scale,height*scale))
    for y in range(0,height,tile):
        for x in range(0,width,tile):
            if cancel(): raise InterruptedError('Interrupção solicitada; arquivo original preservado.')
            if time.monotonic()-t>profile['timeout_per_image_seconds']: raise TimeoutError('Limite de tempo por imagem atingido. Retome com uma imagem menor ou uma amostra.')
            right,bottom=min(width,x+tile),min(height,y+tile);left,top=max(0,x-pad),max(0,y-pad)
            result=infer_patch(net,image.crop((left,top,min(width,right+pad),min(height,bottom+pad))))
            core=result.crop(((x-left)*4,(y-top)*4,(right-left)*4,(bottom-top)*4))
            if scale==2: core=core.resize(((right-x)*2,(bottom-y)*2),Image.Resampling.LANCZOS)
            out.paste(core,(x*scale,y*scale));done+=1;progress(round(done/total*100))
    return out

def verify_output(path,info):
    with Image.open(path) as image:
        image.load()
        if list(image.size)!=info['output_pixels'] or image.mode!='RGB' or abs(image.info.get('dpi',(0,0))[0]-info['ppi'])>.1:
            raise RuntimeError('Falha na verificação do PNG final.')

def upscale(source,destination,scale,ppi,strength,profile,progress=lambda value:None,cancel=lambda:False):
    if strength not in (20,30): raise ValueError('Escolha proporção de 20% ou 30%.')
    info=plan(source,scale,ppi,profile);fingerprint=sha(source)
    target=destination/(source.stem+f'_expandia{scale}x_{ppi}ppi_RE{strength}.png');meta=target.with_suffix('.json')
    if target.exists():
        if not meta.exists(): raise FileExistsError('Saída já existe sem metadados; não foi sobrescrita.')
        existing=json.loads(meta.read_text(encoding='utf-8'))
        if existing.get('source_sha256')!=fingerprint or existing.get('strength')!=strength: raise FileExistsError('Saída já existe com outra origem ou configuração.')
        verify_output(target,info);return {'file':str(target),'reused':True,**info}
    if shutil.disk_usage(destination).free<max(300_000_000,info['output_pixels'][0]*info['output_pixels'][1]*10): raise RuntimeError('Espaço livre insuficiente para saída e cache.')
    cache=RUNTIME/'cache';cache.mkdir(exist_ok=True)
    # Configuração do contexto entra na chave: não reutilizar resultados de outro perfil.
    cachekey=f'{fingerprint}_{scale}x_t{profile["tile"]}_p{profile["context"]}'
    cached=cache/(cachekey+'.png');image,icc=read_image(source);t=time.monotonic()
    if cached.exists():
        with Image.open(cached) as saved: generated=saved.convert('RGB')
        if list(generated.size)!=info['output_pixels']: raise RuntimeError('Cache com dimensões incompatíveis.')
    else:
        try: generated=neural(image,scale,profile,progress,cancel)
        except MemoryError:
            if profile['tile']<=64: raise
            gc.collect();profile=dict(profile,tile=max(64,profile['tile']//2))
            generated=neural(image,scale,profile,progress,cancel)
            cached=cache/(cachekey+'_memory-retry.png')
        tmp=cached.with_suffix('.tmp');generated.save(tmp,format='PNG');os.replace(tmp,cached)
    base=fidelity(image,scale,cancel);mixed=Image.blend(base,generated,strength/100)
    if cancel(): raise InterruptedError('Interrupção solicitada antes de salvar.')
    tmp=target.with_suffix('.tmp');mixed.save(tmp,format='PNG',dpi=(ppi,ppi),icc_profile=icc)
    verify_output(tmp,info);os.replace(tmp,target)
    metadata={**info,'source_sha256':fingerprint,'source_name':source.name,'strength':strength,
              'model':'Real-ESRGAN x4plus','base':'Lanczos + nitidez moderada','profile':profile,
              'face_restoration':False,'seconds':round(time.monotonic()-t,2)}
    atomic_json(meta,metadata)
    return {'file':str(target),'reused':False,**metadata}

def benchmark(profile):
    from PIL import ImageDraw
    sample=Image.new('RGB',(96,96),'#888888');draw=ImageDraw.Draw(sample)
    draw.ellipse((12,12,84,84),fill='#d8ae85');draw.line((0,0,95,95),fill='black',width=2)
    start=time.monotonic();out=neural(sample,4,profile);elapsed=time.monotonic()-start
    assert out.size==(384,384)
    result={'sample_input_pixels':[96,96],'sample_seconds':round(elapsed,3),
            'estimated_seconds_per_1_5mp_including_tile_context':round(elapsed*1_500_000/(96*96)*(1+64/profile['tile'])**2),
            'note':'Estimativa grosseira: conteúdo, memória, temperatura e tamanho dos blocos afetam o tempo.',
            'profile':profile}
    atomic_json(RUNTIME/'benchmark.json',result)
    return result

def self_test(profile):
    sample=Image.new('RGB',(19,13),(120,100,80));output=neural(sample,4,profile)
    assert output.size==(76,52)
    base=fidelity(sample,4);mixed=Image.blend(base,output,.2)
    path=RUNTIME/'self-test.png';mixed.save(path,dpi=(300,300))
    verify_output(path,{'output_pixels':[76,52],'ppi':300})
    return {'ok':True,'model':'Real-ESRGAN x4plus','test':'inferência 4x + mistura20 + PNG/300PPI','system':detect()['system']}

def main():
    parser=argparse.ArgumentParser(description='Expandia: upscale local natural, padrão de 20%.')
    parser.add_argument('command',choices=('doctor','self-test','benchmark','plan','upscale','batch'))
    parser.add_argument('path',nargs='?');parser.add_argument('--scale',type=int,choices=(2,4),default=4)
    parser.add_argument('--ppi',type=int,choices=(150,300),default=300)
    parser.add_argument('--strength',type=int,choices=(20,30),default=20)
    parser.add_argument('--output-dir');args=parser.parse_args()
    report=write_report();profile=report['profile']
    if args.command=='doctor': print(json.dumps(report,ensure_ascii=False,indent=2));return
    libraries()
    if args.command=='plan':
        if not args.path: parser.error('Informe a imagem.')
        print(json.dumps(plan(Path(args.path),args.scale,args.ppi,profile),ensure_ascii=False,indent=2));return
    with exclusive(),awake():
        if args.command in ('self-test','benchmark'):
            result=self_test(profile) if args.command=='self-test' else benchmark(profile)
            print(json.dumps(result,ensure_ascii=False,indent=2));return
        if not args.path: parser.error('Informe a imagem ou pasta.')
        source=Path(args.path).expanduser().resolve()
        files=[source] if args.command=='upscale' else sorted(p for p in source.iterdir() if p.is_file() and p.suffix.lower() in EXTENSIONS and '_expandia' not in p.stem and '_upscale4x_' not in p.stem)
        if not files: raise ValueError('Nenhuma imagem raster original encontrada.')
        destination=Path(args.output_dir).expanduser().resolve() if args.output_dir else (source if source.is_dir() else source.parent)
        destination.mkdir(parents=True,exist_ok=True);stop=destination/'PARAR-EXPANDIA.txt'
        if stop.exists(): raise InterruptedError('Existe PARAR-EXPANDIA.txt; remova o marcador para retomar.')
        state={'status':'processando','strength':args.strength,'scale':args.scale,'ppi':args.ppi,
               'images':[{'name':p.name,'status':'pendente','progress':0} for p in files]}
        status=destination/'expandia-lote.json';atomic_json(status,state)
        try:
            for path,entry in zip(files,state['images']):
                if stop.exists(): raise InterruptedError('Interrupção solicitada.')
                try:
                    entry['status']='processando';atomic_json(status,state)
                    def progress(value):
                        entry['progress']=value;atomic_json(status,state)
                        print(json.dumps({'image':path.name,'progress':value}),flush=True)
                    result=upscale(path,destination,args.scale,args.ppi,args.strength,profile,progress,stop.exists)
                    entry.update(status='concluida',progress=100,result=result);atomic_json(status,state)
                except (InterruptedError,KeyboardInterrupt): raise
                except Exception as exc:
                    entry.update(status='erro',error=str(exc));atomic_json(status,state)
                    if args.command=='upscale': raise
            state['status']='concluido' if all(e['status']=='concluida' for e in state['images']) else 'concluido_com_erros'
        except (InterruptedError,KeyboardInterrupt):
            state['status']='interrompido';atomic_json(status,state);raise
        finally: atomic_json(status,state)
        print(json.dumps(state,ensure_ascii=False,indent=2))
        if state['status']!='concluido': raise SystemExit(1)

if __name__=='__main__': main()
