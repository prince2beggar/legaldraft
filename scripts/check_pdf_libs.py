"""Check available PDF and image processing packages in environment."""

for mod in ["pypdf", "pypdfium2", "fitz", "pdf2image", "PIL", "cryptography"]:
    try:
        __import__(mod)
        print(f"AVAILABLE: {mod}")
    except ImportError:
        print(f"NOT AVAILABLE: {mod}")
