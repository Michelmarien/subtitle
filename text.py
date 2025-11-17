import torch

def check_gpu_availability():
    """Vérifie si CUDA est disponible"""
    if torch.cuda.is_available():
        gpu_name = torch.cuda.get_device_name(0)
        gpu_memory = torch.cuda.get_device_properties(0).total_memory / (1024**3)
        print(f"✅ GPU détecté : {gpu_name}")
        print(f"💾 Mémoire GPU : {gpu_memory:.2f} GB")
        return True
    else:
        print("❌ Pas de GPU CUDA détecté")
        print("   → Installez PyTorch avec CUDA : https://pytorch.org/get-started/locally/")
        return False

# Test
if check_gpu_availability():
    device = 'cuda'
else:
    device = 'cpu'
