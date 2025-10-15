import importlib
try:
    torch = importlib.import_module('torch')
    print('torch_installed', getattr(torch, '__version__', 'unknown'))
    try:
        ca = torch.cuda.is_available()
        print('cuda_available', ca)
        print('device_count', torch.cuda.device_count() if ca else 0)
        print('torch_cuda_build', getattr(torch.version, 'cuda', None))
        if ca:
            try:
                print('device0', torch.cuda.get_device_name(0))
            except Exception as e:
                print('get_device_name error', e)
    except Exception as e:
        print('cuda check error', e)
except Exception as e:
    print('torch import error', e)
